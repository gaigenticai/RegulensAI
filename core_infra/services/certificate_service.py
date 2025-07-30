"""
Certificate Service
Handles certificate generation, validation, and management for training portal.
"""

import os
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from io import BytesIO
import tempfile

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import Color, black, blue, gold
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF
from PIL import Image as PILImage, ImageDraw, ImageFont
import qrcode

from core_infra.database.models import (
    db, TrainingCertificate, TrainingEnrollment, TrainingModule, User
)
from core_infra.utils.email import EmailService
from core_infra.utils.storage import FileStorage
import structlog

logger = structlog.get_logger(__name__)


class CertificateService:
    """Service for managing training certificates."""
    
    def __init__(self):
        self.email_service = EmailService()
        self.file_storage = FileStorage()
        self.certificate_template_path = "assets/certificate_template.png"
        self.logo_path = "assets/regulensai_logo.png"
    
    def generate_certificate(self, enrollment_id: str) -> TrainingCertificate:
        """
        Generate a certificate for a completed training enrollment.
        """
        try:
            # Get enrollment with related data
            enrollment = TrainingEnrollment.query.filter(
                TrainingEnrollment.id == enrollment_id,
                TrainingEnrollment.status == 'completed'
            ).first()
            
            if not enrollment:
                raise ValueError("Enrollment not found or not completed")
            
            # Check if certificate already exists
            existing_cert = TrainingCertificate.query.filter(
                TrainingCertificate.enrollment_id == enrollment_id
            ).first()
            
            if existing_cert:
                raise ValueError("Certificate already exists for this enrollment")
            
            # Calculate final score from assessment attempts
            final_score = self._calculate_final_score(enrollment_id)
            
            # Determine certificate type based on score
            certificate_type = self._determine_certificate_type(final_score, enrollment)
            
            # Generate unique certificate number and verification code
            certificate_number = self._generate_certificate_number()
            verification_code = self._generate_verification_code(enrollment_id, certificate_number)
            
            # Create certificate record
            certificate = TrainingCertificate(
                user_id=enrollment.user_id,
                module_id=enrollment.module_id,
                enrollment_id=enrollment_id,
                certificate_number=certificate_number,
                certificate_type=certificate_type,
                final_score=final_score,
                verification_code=verification_code,
                is_valid=True
            )
            
            # Set expiration date if applicable
            if enrollment.module.category in ['compliance', 'security']:
                certificate.expires_at = datetime.utcnow() + timedelta(days=365)  # 1 year
            
            db.session.add(certificate)
            db.session.commit()
            
            # Generate certificate files
            self._generate_certificate_files(certificate)
            
            # Send notification email
            self._send_certificate_notification(certificate)
            
            logger.info(
                "Certificate generated successfully",
                certificate_id=str(certificate.id),
                enrollment_id=enrollment_id,
                certificate_number=certificate_number
            )
            
            return certificate
            
        except Exception as e:
            logger.error("Failed to generate certificate", enrollment_id=enrollment_id, error=str(e))
            db.session.rollback()
            raise
    
    def generate_certificate_file(self, certificate: TrainingCertificate, format_type: str = 'pdf') -> str:
        """
        Generate certificate file in specified format.
        """
        try:
            if format_type.lower() == 'pdf':
                return self._generate_pdf_certificate(certificate)
            elif format_type.lower() == 'png':
                return self._generate_image_certificate(certificate)
            else:
                raise ValueError(f"Unsupported format: {format_type}")
                
        except Exception as e:
            logger.error("Failed to generate certificate file", certificate_id=str(certificate.id), error=str(e))
            raise
    
    def _calculate_final_score(self, enrollment_id: str) -> Optional[float]:
        """
        Calculate final score from assessment attempts.
        """
        try:
            from core_infra.database.models import TrainingAssessmentAttempt
            
            # Get best scores for each assessment
            attempts = TrainingAssessmentAttempt.query.filter(
                TrainingAssessmentAttempt.enrollment_id == enrollment_id,
                TrainingAssessmentAttempt.status == 'completed',
                TrainingAssessmentAttempt.passed == True
            ).all()
            
            if not attempts:
                return None
            
            # Calculate average of best scores
            total_score = sum(attempt.score for attempt in attempts if attempt.score)
            return total_score / len(attempts) if attempts else None
            
        except Exception as e:
            logger.error("Failed to calculate final score", enrollment_id=enrollment_id, error=str(e))
            return None
    
    def _determine_certificate_type(self, final_score: Optional[float], enrollment: TrainingEnrollment) -> str:
        """
        Determine certificate type based on performance and module characteristics.
        """
        if not final_score:
            return 'completion'
        
        if final_score >= 95:
            return 'mastery'
        elif final_score >= 85:
            return 'proficiency'
        else:
            return 'completion'
    
    def _generate_certificate_number(self) -> str:
        """
        Generate unique certificate number.
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        random_part = str(uuid.uuid4()).replace('-', '')[:8].upper()
        return f"REG-{timestamp}-{random_part}"
    
    def _generate_verification_code(self, enrollment_id: str, certificate_number: str) -> str:
        """
        Generate verification code for certificate.
        """
        data = f"{enrollment_id}{certificate_number}{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16].upper()
    
    def _generate_pdf_certificate(self, certificate: TrainingCertificate) -> str:
        """
        Generate PDF certificate using ReportLab.
        """
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_path = temp_file.name
            temp_file.close()
            
            # Create PDF document
            doc = SimpleDocTemplate(
                temp_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Get styles
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=28,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=blue
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=18,
                spaceAfter=20,
                alignment=TA_CENTER,
                textColor=black
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=14,
                spaceAfter=12,
                alignment=TA_CENTER
            )
            
            # Build certificate content
            story = []
            
            # Add logo if available
            if os.path.exists(self.logo_path):
                logo = Image(self.logo_path, width=2*inch, height=1*inch)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 20))
            
            # Certificate title
            story.append(Paragraph("CERTIFICATE OF COMPLETION", title_style))
            story.append(Spacer(1, 20))
            
            # Organization name
            story.append(Paragraph("RegulensAI Training Program", subtitle_style))
            story.append(Spacer(1, 30))
            
            # Certificate text
            story.append(Paragraph("This certifies that", body_style))
            story.append(Spacer(1, 10))
            
            # User name
            user_name_style = ParagraphStyle(
                'UserName',
                parent=styles['Normal'],
                fontSize=24,
                spaceAfter=20,
                alignment=TA_CENTER,
                textColor=blue,
                fontName='Helvetica-Bold'
            )
            story.append(Paragraph(certificate.user.full_name, user_name_style))
            
            # Achievement text
            story.append(Paragraph("has successfully completed the training module", body_style))
            story.append(Spacer(1, 10))
            
            # Module name
            module_style = ParagraphStyle(
                'ModuleName',
                parent=styles['Normal'],
                fontSize=20,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=black,
                fontName='Helvetica-Bold'
            )
            story.append(Paragraph(certificate.module.title, module_style))
            
            # Certificate details table
            details_data = [
                ['Certificate Number:', certificate.certificate_number],
                ['Date Issued:', certificate.issued_at.strftime('%B %d, %Y')],
                ['Certificate Type:', certificate.certificate_type.title()],
            ]
            
            if certificate.final_score:
                details_data.append(['Final Score:', f"{certificate.final_score:.1f}%"])
            
            if certificate.expires_at:
                details_data.append(['Expires:', certificate.expires_at.strftime('%B %d, %Y')])
            
            details_table = Table(details_data, colWidths=[2*inch, 2*inch])
            details_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(details_table)
            story.append(Spacer(1, 30))
            
            # QR Code for verification
            qr_code_path = self._generate_qr_code(certificate.verification_code)
            if qr_code_path:
                qr_image = Image(qr_code_path, width=1*inch, height=1*inch)
                qr_image.hAlign = 'CENTER'
                story.append(qr_image)
                story.append(Paragraph("Scan to verify certificate authenticity", 
                                     ParagraphStyle('QRText', parent=styles['Normal'], 
                                                  fontSize=10, alignment=TA_CENTER)))
                # Clean up QR code file
                os.unlink(qr_code_path)
            
            # Build PDF
            doc.build(story)
            
            return temp_path
            
        except Exception as e:
            logger.error("Failed to generate PDF certificate", certificate_id=str(certificate.id), error=str(e))
            raise
    
    def _generate_image_certificate(self, certificate: TrainingCertificate) -> str:
        """
        Generate image certificate using PIL.
        """
        try:
            # Create certificate image
            width, height = 1200, 800
            img = PILImage.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Try to load fonts
            try:
                title_font = ImageFont.truetype("arial.ttf", 48)
                subtitle_font = ImageFont.truetype("arial.ttf", 32)
                body_font = ImageFont.truetype("arial.ttf", 24)
                small_font = ImageFont.truetype("arial.ttf", 16)
            except:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                body_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            # Draw border
            border_color = (0, 100, 200)
            draw.rectangle([20, 20, width-20, height-20], outline=border_color, width=5)
            draw.rectangle([40, 40, width-40, height-40], outline=border_color, width=2)
            
            # Title
            title_text = "CERTIFICATE OF COMPLETION"
            title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            draw.text(((width - title_width) // 2, 80), title_text, 
                     fill=border_color, font=title_font)
            
            # Organization
            org_text = "RegulensAI Training Program"
            org_bbox = draw.textbbox((0, 0), org_text, font=subtitle_font)
            org_width = org_bbox[2] - org_bbox[0]
            draw.text(((width - org_width) // 2, 150), org_text, 
                     fill='black', font=subtitle_font)
            
            # Certificate text
            cert_text = "This certifies that"
            cert_bbox = draw.textbbox((0, 0), cert_text, font=body_font)
            cert_width = cert_bbox[2] - cert_bbox[0]
            draw.text(((width - cert_width) // 2, 220), cert_text, 
                     fill='black', font=body_font)
            
            # User name
            user_text = certificate.user.full_name
            user_bbox = draw.textbbox((0, 0), user_text, font=title_font)
            user_width = user_bbox[2] - user_bbox[0]
            draw.text(((width - user_width) // 2, 280), user_text, 
                     fill=border_color, font=title_font)
            
            # Achievement text
            achievement_text = "has successfully completed the training module"
            achievement_bbox = draw.textbbox((0, 0), achievement_text, font=body_font)
            achievement_width = achievement_bbox[2] - achievement_bbox[0]
            draw.text(((width - achievement_width) // 2, 360), achievement_text, 
                     fill='black', font=body_font)
            
            # Module name
            module_text = certificate.module.title
            module_bbox = draw.textbbox((0, 0), module_text, font=subtitle_font)
            module_width = module_bbox[2] - module_bbox[0]
            draw.text(((width - module_width) // 2, 420), module_text, 
                     fill='black', font=subtitle_font)
            
            # Certificate details
            details_y = 520
            details = [
                f"Certificate Number: {certificate.certificate_number}",
                f"Date Issued: {certificate.issued_at.strftime('%B %d, %Y')}",
                f"Certificate Type: {certificate.certificate_type.title()}"
            ]
            
            if certificate.final_score:
                details.append(f"Final Score: {certificate.final_score:.1f}%")
            
            for detail in details:
                detail_bbox = draw.textbbox((0, 0), detail, font=small_font)
                detail_width = detail_bbox[2] - detail_bbox[0]
                draw.text(((width - detail_width) // 2, details_y), detail, 
                         fill='black', font=small_font)
                details_y += 25
            
            # QR Code
            qr_code_path = self._generate_qr_code(certificate.verification_code)
            if qr_code_path:
                qr_img = PILImage.open(qr_code_path)
                qr_img = qr_img.resize((100, 100))
                img.paste(qr_img, (width - 150, height - 150))
                
                # QR text
                qr_text = "Scan to verify"
                draw.text((width - 150, height - 40), qr_text, 
                         fill='black', font=small_font)
                
                # Clean up QR code file
                os.unlink(qr_code_path)
            
            # Save image
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_path = temp_file.name
            temp_file.close()
            
            img.save(temp_path, 'PNG')
            
            return temp_path
            
        except Exception as e:
            logger.error("Failed to generate image certificate", certificate_id=str(certificate.id), error=str(e))
            raise
    
    def _generate_qr_code(self, verification_code: str) -> str:
        """
        Generate QR code for certificate verification.
        """
        try:
            # Create QR code
            verification_url = f"https://portal.regulensai.com/certificates/verify/{verification_code}"
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(verification_url)
            qr.make(fit=True)
            
            # Create QR code image
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_path = temp_file.name
            temp_file.close()
            
            qr_img.save(temp_path)
            
            return temp_path
            
        except Exception as e:
            logger.error("Failed to generate QR code", verification_code=verification_code, error=str(e))
            return None
    
    def _generate_certificate_files(self, certificate: TrainingCertificate) -> None:
        """
        Generate and store certificate files.
        """
        try:
            # Generate PDF
            pdf_path = self._generate_pdf_certificate(certificate)
            
            # Store in file storage
            pdf_key = f"certificates/{certificate.id}/certificate.pdf"
            self.file_storage.upload_file(pdf_path, pdf_key)
            
            # Clean up temporary file
            os.unlink(pdf_path)
            
            # Update certificate with file path
            certificate.certificate_data = {'pdf_key': pdf_key}
            db.session.commit()
            
        except Exception as e:
            logger.error("Failed to generate certificate files", certificate_id=str(certificate.id), error=str(e))
    
    def _send_certificate_notification(self, certificate: TrainingCertificate) -> None:
        """
        Send email notification about certificate generation.
        """
        try:
            # Prepare email data
            email_data = {
                'user_name': certificate.user.full_name,
                'module_title': certificate.module.title,
                'certificate_number': certificate.certificate_number,
                'verification_url': f"https://portal.regulensai.com/certificates/verify/{certificate.verification_code}",
                'download_url': f"https://portal.regulensai.com/certificates/{certificate.id}/download"
            }
            
            # Send email
            self.email_service.send_template_email(
                to_email=certificate.user.email,
                template_name='certificate_issued',
                template_data=email_data,
                subject=f"Certificate Issued: {certificate.module.title}"
            )
            
        except Exception as e:
            logger.error("Failed to send certificate notification", certificate_id=str(certificate.id), error=str(e))
