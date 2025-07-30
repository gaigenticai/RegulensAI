"""
Email Service
Enterprise-grade email service for notifications, certificates, and communications.
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template
import structlog

logger = structlog.get_logger(__name__)


class EmailService:
    """Enterprise email service with template support and delivery tracking."""
    
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'localhost')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@regulensai.com')
        self.from_name = os.getenv('FROM_NAME', 'RegulensAI')
        
        # Template configuration
        self.template_dir = os.getenv('EMAIL_TEMPLATE_DIR', 'templates/email')
        self.jinja_env = None
        self._setup_templates()
    
    def _setup_templates(self):
        """Setup Jinja2 template environment."""
        try:
            if os.path.exists(self.template_dir):
                self.jinja_env = Environment(
                    loader=FileSystemLoader(self.template_dir),
                    autoescape=True
                )
            else:
                logger.warning("Email template directory not found", path=self.template_dir)
        except Exception as e:
            logger.error("Failed to setup email templates", error=str(e))
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email with optional HTML content and attachments.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: Optional HTML body
            attachments: Optional list of attachments
            cc_emails: Optional CC recipients
            bcc_emails: Optional BCC recipients
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            # Add text part
            text_part = MIMEText(body_text, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Add HTML part if provided
            if body_html:
                html_part = MIMEText(body_html, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    self._add_attachment(msg, attachment)
            
            # Build recipient list
            recipients = [to_email]
            if cc_emails:
                recipients.extend(cc_emails)
            if bcc_emails:
                recipients.extend(bcc_emails)
            
            # Send email
            return self._send_smtp_email(msg, recipients)
            
        except Exception as e:
            logger.error("Failed to send email", to_email=to_email, subject=subject, error=str(e))
            return False
    
    def send_template_email(
        self,
        to_email: str,
        template_name: str,
        template_data: Dict[str, Any],
        subject: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Send an email using a Jinja2 template.
        
        Args:
            to_email: Recipient email address
            template_name: Template file name (without extension)
            template_data: Data to render in template
            subject: Email subject
            attachments: Optional attachments
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            if not self.jinja_env:
                logger.error("Email templates not configured")
                return False
            
            # Load and render templates
            text_template = self._load_template(f"{template_name}.txt")
            html_template = self._load_template(f"{template_name}.html")
            
            body_text = text_template.render(**template_data) if text_template else ""
            body_html = html_template.render(**template_data) if html_template else None
            
            if not body_text and not body_html:
                logger.error("No email template content found", template=template_name)
                return False
            
            return self.send_email(
                to_email=to_email,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                attachments=attachments
            )
            
        except Exception as e:
            logger.error("Failed to send template email", template=template_name, error=str(e))
            return False
    
    def _load_template(self, template_name: str) -> Optional[Template]:
        """Load a Jinja2 template."""
        try:
            return self.jinja_env.get_template(template_name)
        except Exception:
            # Template not found or error loading
            return None
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """Add an attachment to the email message."""
        try:
            file_path = attachment.get('file_path')
            filename = attachment.get('filename')
            content_type = attachment.get('content_type', 'application/octet-stream')
            
            if not file_path or not os.path.exists(file_path):
                logger.warning("Attachment file not found", file_path=file_path)
                return
            
            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename or os.path.basename(file_path)}'
            )
            
            msg.attach(part)
            
        except Exception as e:
            logger.error("Failed to add attachment", attachment=attachment, error=str(e))
    
    def _send_smtp_email(self, msg: MIMEMultipart, recipients: List[str]) -> bool:
        """Send email via SMTP."""
        try:
            # Create SMTP connection
            if self.smtp_use_tls:
                context = ssl.create_default_context()
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls(context=context)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            
            # Login if credentials provided
            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)
            
            # Send email
            text = msg.as_string()
            server.sendmail(self.from_email, recipients, text)
            server.quit()
            
            logger.info("Email sent successfully", recipients=recipients)
            return True
            
        except Exception as e:
            logger.error("SMTP send failed", recipients=recipients, error=str(e))
            return False
    
    def send_certificate_notification(
        self,
        user_email: str,
        user_name: str,
        module_title: str,
        certificate_number: str,
        verification_url: str,
        download_url: str
    ) -> bool:
        """
        Send certificate issuance notification.
        
        Args:
            user_email: User's email address
            user_name: User's full name
            module_title: Training module title
            certificate_number: Certificate number
            verification_url: URL to verify certificate
            download_url: URL to download certificate
            
        Returns:
            True if notification sent successfully
        """
        template_data = {
            'user_name': user_name,
            'module_title': module_title,
            'certificate_number': certificate_number,
            'verification_url': verification_url,
            'download_url': download_url,
            'company_name': 'RegulensAI',
            'support_email': 'support@regulensai.com'
        }
        
        return self.send_template_email(
            to_email=user_email,
            template_name='certificate_issued',
            template_data=template_data,
            subject=f"Certificate Issued: {module_title}"
        )
    
    def send_training_reminder(
        self,
        user_email: str,
        user_name: str,
        module_title: str,
        due_date: str,
        portal_url: str
    ) -> bool:
        """
        Send training completion reminder.
        
        Args:
            user_email: User's email address
            user_name: User's full name
            module_title: Training module title
            due_date: Due date for completion
            portal_url: URL to training portal
            
        Returns:
            True if reminder sent successfully
        """
        template_data = {
            'user_name': user_name,
            'module_title': module_title,
            'due_date': due_date,
            'portal_url': portal_url,
            'company_name': 'RegulensAI'
        }
        
        return self.send_template_email(
            to_email=user_email,
            template_name='training_reminder',
            template_data=template_data,
            subject=f"Training Reminder: {module_title}"
        )
    
    def send_enrollment_confirmation(
        self,
        user_email: str,
        user_name: str,
        module_title: str,
        estimated_duration: int,
        portal_url: str
    ) -> bool:
        """
        Send training enrollment confirmation.
        
        Args:
            user_email: User's email address
            user_name: User's full name
            module_title: Training module title
            estimated_duration: Estimated completion time in minutes
            portal_url: URL to training portal
            
        Returns:
            True if confirmation sent successfully
        """
        template_data = {
            'user_name': user_name,
            'module_title': module_title,
            'estimated_duration': estimated_duration,
            'portal_url': portal_url,
            'company_name': 'RegulensAI'
        }
        
        return self.send_template_email(
            to_email=user_email,
            template_name='enrollment_confirmation',
            template_data=template_data,
            subject=f"Training Enrollment Confirmed: {module_title}"
        )
    
    def create_default_templates(self):
        """Create default email templates if they don't exist."""
        try:
            os.makedirs(self.template_dir, exist_ok=True)
            
            # Certificate issued template
            cert_template_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Certificate Issued</title>
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #2c5aa0;">Congratulations, {{ user_name }}!</h1>
                    
                    <p>We're pleased to inform you that you have successfully completed the training module:</p>
                    
                    <div style="background: #f8f9fa; padding: 20px; border-left: 4px solid #2c5aa0; margin: 20px 0;">
                        <h2 style="margin: 0; color: #2c5aa0;">{{ module_title }}</h2>
                        <p style="margin: 10px 0 0 0;"><strong>Certificate Number:</strong> {{ certificate_number }}</p>
                    </div>
                    
                    <p>Your certificate is now available for download and verification:</p>
                    
                    <div style="margin: 30px 0;">
                        <a href="{{ download_url }}" style="background: #2c5aa0; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">Download Certificate</a>
                        <a href="{{ verification_url }}" style="background: #6c757d; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; margin-left: 10px;">Verify Certificate</a>
                    </div>
                    
                    <p>Thank you for your commitment to professional development!</p>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #666;">
                        This email was sent by {{ company_name }}. If you have any questions, please contact us at {{ support_email }}.
                    </p>
                </div>
            </body>
            </html>
            """
            
            cert_template_text = """
            Congratulations, {{ user_name }}!
            
            You have successfully completed the training module: {{ module_title }}
            Certificate Number: {{ certificate_number }}
            
            Download your certificate: {{ download_url }}
            Verify your certificate: {{ verification_url }}
            
            Thank you for your commitment to professional development!
            
            --
            {{ company_name }}
            {{ support_email }}
            """
            
            # Write templates
            with open(os.path.join(self.template_dir, 'certificate_issued.html'), 'w') as f:
                f.write(cert_template_html)
            
            with open(os.path.join(self.template_dir, 'certificate_issued.txt'), 'w') as f:
                f.write(cert_template_text)
            
            logger.info("Default email templates created", template_dir=self.template_dir)
            
        except Exception as e:
            logger.error("Failed to create default templates", error=str(e))
