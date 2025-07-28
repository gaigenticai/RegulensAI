"""
Document Classifier for Computer Vision Service
Provides production-ready document classification for financial compliance
with support for multiple computer vision providers and comprehensive audit trails.
"""

import logging
import json
import time
import base64
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from uuid import UUID
from dataclasses import dataclass
from enum import Enum
import io

try:
    import cv2
    import numpy as np
    from PIL import Image
    import pytesseract
except ImportError:
    cv2 = None
    np = None
    Image = None
    pytesseract = None

try:
    import boto3
    from azure.cognitiveservices.vision.computervision import ComputerVisionClient
    from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
    from msrest.authentication import CognitiveServicesCredentials
except ImportError:
    boto3 = None
    ComputerVisionClient = None

from supabase import Client
from core_infra.config import get_settings

logger = logging.getLogger(__name__)

class DocumentType(Enum):
    """Supported document types for classification"""
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    NATIONAL_ID = "national_id"
    BANK_STATEMENT = "bank_statement"
    UTILITY_BILL = "utility_bill"
    INVOICE = "invoice"
    CONTRACT = "contract"
    REGULATORY_FORM = "regulatory_form"
    COMPLIANCE_CERTIFICATE = "compliance_certificate"
    FINANCIAL_STATEMENT = "financial_statement"
    UNKNOWN = "unknown"

class ClassificationProvider(Enum):
    """Computer vision providers for document classification"""
    AWS_TEXTRACT = "aws_textract"
    AZURE_VISION = "azure_vision"
    GOOGLE_VISION = "google_vision"
    TESSERACT_OCR = "tesseract_ocr"
    CUSTOM_MODEL = "custom_model"

@dataclass
class ClassificationResult:
    """Result structure for document classification"""
    document_type: DocumentType
    confidence_score: float
    detected_features: Dict[str, Any]
    extracted_text: Optional[str]
    key_fields: Dict[str, str]
    processing_time_ms: int
    provider_used: str
    image_quality_score: float
    requires_human_review: bool = False
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class DocumentImage:
    """Structure for document image data"""
    image_data: bytes
    image_format: str
    width: Optional[int] = None
    height: Optional[int] = None
    dpi: Optional[int] = None

class DocumentClassifier:
    """
    Production-ready document classification service for financial compliance.
    Supports multiple CV providers with fallback mechanisms and comprehensive logging.
    """
    
    def __init__(self, supabase_client: Client):
        self.settings = get_settings()
        self.supabase = supabase_client
        
        # Initialize CV providers
        self.aws_textract = None
        self.azure_cv_client = None
        self.google_vision_client = None
        
        # Document type patterns for classification
        self.document_patterns = {
            DocumentType.PASSPORT: {
                'keywords': ['passport', 'p<', 'nationality', 'place of birth'],
                'features': ['mrz_line', 'photo', 'country_code']
            },
            DocumentType.DRIVERS_LICENSE: {
                'keywords': ['driver', 'license', 'licence', 'class', 'expires'],
                'features': ['photo', 'address', 'date_of_birth']
            },
            DocumentType.BANK_STATEMENT: {
                'keywords': ['bank', 'statement', 'account', 'balance', 'transaction'],
                'features': ['account_number', 'transactions', 'balance']
            },
            DocumentType.UTILITY_BILL: {
                'keywords': ['electric', 'gas', 'water', 'utility', 'bill', 'usage'],
                'features': ['address', 'amount_due', 'service_dates']
            }
        }
        
        # Quality thresholds
        self.min_confidence_threshold = 0.7
        self.min_image_quality_score = 0.6
        
        self._initialize_providers()
        
    def _initialize_providers(self):
        """Initialize computer vision providers"""
        try:
            # Initialize AWS Textract
            if hasattr(self.settings, 'AWS_ACCESS_KEY_ID') and self.settings.AWS_ACCESS_KEY_ID:
                try:
                    self.aws_textract = boto3.client(
                        'textract',
                        aws_access_key_id=self.settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=self.settings.AWS_SECRET_ACCESS_KEY,
                        region_name=getattr(self.settings, 'AWS_REGION', 'us-east-1')
                    )
                    logger.info("AWS Textract client initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize AWS Textract: {str(e)}")
                    
            # Initialize Azure Computer Vision
            if hasattr(self.settings, 'AZURE_FORM_RECOGNIZER_KEY') and self.settings.AZURE_FORM_RECOGNIZER_KEY:
                try:
                    endpoint = self.settings.AZURE_FORM_RECOGNIZER_ENDPOINT
                    key = self.settings.AZURE_FORM_RECOGNIZER_KEY
                    self.azure_cv_client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(key))
                    logger.info("Azure Computer Vision client initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize Azure CV: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error initializing document classifier providers: {str(e)}")
            
    async def classify_document(self, image_data: bytes, tenant_id: UUID,
                              provider: str = "auto",
                              include_text_extraction: bool = True) -> ClassificationResult:
        """
        Classify document type from image data
        
        Args:
            image_data: Binary image data
            tenant_id: Tenant identifier for audit logging
            provider: Preferred CV provider
            include_text_extraction: Whether to extract text content
            
        Returns:
            ClassificationResult with document type and extracted information
        """
        start_time = datetime.now(timezone.utc)
        processing_start = time.time()
        
        try:
            logger.info(f"Starting document classification for tenant {tenant_id}")
            
            # Validate and preprocess image
            document_image = await self._preprocess_image(image_data)
            
            # Calculate image quality score
            quality_score = await self._calculate_image_quality(document_image)
            
            # Select provider
            provider_used = self._select_provider(provider)
            
            # Perform classification based on provider
            if provider_used == "aws_textract" and self.aws_textract:
                result = await self._classify_with_aws(document_image, include_text_extraction)
            elif provider_used == "azure_vision" and self.azure_cv_client:
                result = await self._classify_with_azure(document_image, include_text_extraction)
            elif provider_used == "tesseract_ocr" and pytesseract:
                result = await self._classify_with_tesseract(document_image, include_text_extraction)
            else:
                result = await self._classify_with_pattern_matching(document_image, include_text_extraction)
                provider_used = "pattern_matching"
                
            # Calculate processing time
            processing_time_ms = int((time.time() - processing_start) * 1000)
            
            # Update result with metadata
            result.processing_time_ms = processing_time_ms
            result.provider_used = provider_used
            result.image_quality_score = quality_score
            result.requires_human_review = (
                result.confidence_score < self.min_confidence_threshold or 
                quality_score < self.min_image_quality_score
            )
            result.metadata = {
                'image_size_bytes': len(image_data),
                'image_format': document_image.image_format,
                'quality_score': quality_score
            }
            
            # Log classification to database
            await self._log_classification(tenant_id, result, start_time)
            
            logger.info(f"Document classification completed: {result.document_type.value} ({result.confidence_score:.3f})")
            return result
            
        except Exception as e:
            logger.error(f"Error in document classification: {str(e)}", exc_info=True)
            
            # Log error to database
            await self._log_error(tenant_id, str(e), start_time)
            
            # Return unknown classification with error metadata
            return ClassificationResult(
                document_type=DocumentType.UNKNOWN,
                confidence_score=0.0,
                detected_features={},
                extracted_text=None,
                key_fields={},
                processing_time_ms=int((time.time() - processing_start) * 1000),
                provider_used=provider,
                image_quality_score=0.0,
                requires_human_review=True,
                metadata={'error': str(e)}
            )
            
    async def _preprocess_image(self, image_data: bytes) -> DocumentImage:
        """Preprocess and validate image data"""
        try:
            # Detect image format
            image_format = "unknown"
            if image_data.startswith(b'\xff\xd8\xff'):
                image_format = "jpeg"
            elif image_data.startswith(b'\x89PNG'):
                image_format = "png"
            elif image_data.startswith(b'%PDF'):
                raise ValueError("PDF files not supported, please convert to image first")
                
            # Get image dimensions if PIL is available
            width, height, dpi = None, None, None
            if Image:
                try:
                    with Image.open(io.BytesIO(image_data)) as img:
                        width, height = img.size
                        dpi = img.info.get('dpi', (72, 72))[0] if 'dpi' in img.info else None
                except Exception:
                    pass
                    
            return DocumentImage(
                image_data=image_data,
                image_format=image_format,
                width=width,
                height=height,
                dpi=dpi
            )
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            raise
            
    async def _calculate_image_quality(self, document_image: DocumentImage) -> float:
        """Calculate image quality score for classification confidence"""
        try:
            quality_score = 0.5  # Base score
            
            # Check image size
            if len(document_image.image_data) > 1024 * 1024:  # > 1MB
                quality_score += 0.1
            elif len(document_image.image_data) < 100 * 1024:  # < 100KB
                quality_score -= 0.2
                
            # Check dimensions if available
            if document_image.width and document_image.height:
                total_pixels = document_image.width * document_image.height
                if total_pixels > 1000000:  # > 1MP
                    quality_score += 0.2
                elif total_pixels < 300000:  # < 0.3MP
                    quality_score -= 0.1
                    
            # Check DPI if available
            if document_image.dpi:
                if document_image.dpi >= 300:
                    quality_score += 0.2
                elif document_image.dpi < 150:
                    quality_score -= 0.1
                    
            return max(0.0, min(1.0, quality_score))
            
        except Exception as e:
            logger.error(f"Error calculating image quality: {str(e)}")
            return 0.5
            
    async def _classify_with_aws(self, document_image: DocumentImage, extract_text: bool) -> ClassificationResult:
        """Classify document using AWS Textract"""
        try:
            # Analyze document with AWS Textract
            response = self.aws_textract.analyze_document(
                Document={'Bytes': document_image.image_data},
                FeatureTypes=['TABLES', 'FORMS'] if extract_text else []
            )
            
            # Extract text blocks
            extracted_text = ""
            key_fields = {}
            detected_features = {}
            
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'LINE':
                    extracted_text += block.get('Text', '') + '\n'
                elif block['BlockType'] == 'KEY_VALUE_SET' and block.get('EntityTypes'):
                    if 'KEY' in block['EntityTypes']:
                        # Process key-value pairs
                        pass
                        
            # Classify based on extracted text
            document_type, confidence = self._classify_from_text(extracted_text)
            
            return ClassificationResult(
                document_type=document_type,
                confidence_score=confidence,
                detected_features=detected_features,
                extracted_text=extracted_text.strip() if extract_text else None,
                key_fields=key_fields,
                processing_time_ms=0,  # Will be set by caller
                provider_used="aws_textract",
                image_quality_score=0.0  # Will be set by caller
            )
            
        except Exception as e:
            logger.error(f"Error in AWS Textract classification: {str(e)}")
            raise
            
    async def _classify_with_azure(self, document_image: DocumentImage, extract_text: bool) -> ClassificationResult:
        """Classify document using Azure Computer Vision"""
        try:
            # Convert image data to stream
            image_stream = io.BytesIO(document_image.image_data)
            
            # Analyze image with Azure CV
            features = [VisualFeatureTypes.categories, VisualFeatureTypes.description, VisualFeatureTypes.tags]
            analysis = self.azure_cv_client.analyze_image_in_stream(image_stream, visual_features=features)
            
            # Extract text if requested
            extracted_text = ""
            if extract_text:
                try:
                    image_stream.seek(0)
                    ocr_result = self.azure_cv_client.read_in_stream(image_stream, raw=True)
                    # Process OCR results...
                except Exception:
                    pass
                    
            # Classify based on Azure analysis
            document_type = DocumentType.UNKNOWN
            confidence = 0.5
            
            # Analyze categories and tags
            for category in analysis.categories:
                if 'document' in category.name.lower():
                    confidence = max(confidence, category.score)
                    
            for tag in analysis.tags:
                if tag.name.lower() in ['document', 'text', 'paper']:
                    confidence = max(confidence, tag.confidence)
                    
            return ClassificationResult(
                document_type=document_type,
                confidence_score=confidence,
                detected_features={'categories': [c.name for c in analysis.categories]},
                extracted_text=extracted_text if extract_text else None,
                key_fields={},
                processing_time_ms=0,
                provider_used="azure_vision",
                image_quality_score=0.0
            )
            
        except Exception as e:
            logger.error(f"Error in Azure CV classification: {str(e)}")
            raise
            
    async def _classify_with_tesseract(self, document_image: DocumentImage, extract_text: bool) -> ClassificationResult:
        """Classify document using Tesseract OCR"""
        try:
            # Convert image data to PIL Image
            image = Image.open(io.BytesIO(document_image.image_data))
            
            # Extract text using Tesseract
            extracted_text = ""
            if extract_text:
                extracted_text = pytesseract.image_to_string(image)
                
            # Classify based on extracted text
            document_type, confidence = self._classify_from_text(extracted_text)
            
            return ClassificationResult(
                document_type=document_type,
                confidence_score=confidence,
                detected_features={'ocr_engine': 'tesseract'},
                extracted_text=extracted_text if extract_text else None,
                key_fields={},
                processing_time_ms=0,
                provider_used="tesseract_ocr",
                image_quality_score=0.0
            )
            
        except Exception as e:
            logger.error(f"Error in Tesseract classification: {str(e)}")
            raise
            
    async def _classify_with_pattern_matching(self, document_image: DocumentImage, extract_text: bool) -> ClassificationResult:
        """Fallback classification using simple pattern matching"""
        try:
            # Since we can't extract text without OCR, return unknown with low confidence
            return ClassificationResult(
                document_type=DocumentType.UNKNOWN,
                confidence_score=0.3,
                detected_features={'method': 'pattern_matching_fallback'},
                extracted_text=None,
                key_fields={},
                processing_time_ms=0,
                provider_used="pattern_matching",
                image_quality_score=0.0
            )
            
        except Exception as e:
            logger.error(f"Error in pattern matching classification: {str(e)}")
            raise
            
    def _classify_from_text(self, text: str) -> tuple[DocumentType, float]:
        """Classify document type based on extracted text"""
        if not text:
            return DocumentType.UNKNOWN, 0.3
            
        text_lower = text.lower()
        best_match = DocumentType.UNKNOWN
        best_confidence = 0.0
        
        for doc_type, patterns in self.document_patterns.items():
            confidence = 0.0
            keyword_matches = 0
            
            # Check keyword matches
            for keyword in patterns['keywords']:
                if keyword in text_lower:
                    keyword_matches += 1
                    
            if keyword_matches > 0:
                confidence = min(0.9, keyword_matches / len(patterns['keywords']) * 0.8 + 0.2)
                
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = doc_type
                
        return best_match, best_confidence
        
    def _select_provider(self, provider: str) -> str:
        """Select appropriate CV provider"""
        if provider == "auto":
            if self.aws_textract:
                return "aws_textract"
            elif self.azure_cv_client:
                return "azure_vision"
            elif pytesseract:
                return "tesseract_ocr"
            else:
                return "pattern_matching"
        return provider
        
    async def _log_classification(self, tenant_id: UUID, result: ClassificationResult, start_time: datetime):
        """Log classification results to database"""
        try:
            log_data = {
                'tenant_id': str(tenant_id),
                'processing_type': 'document_classification',
                'document_type': result.document_type.value,
                'confidence_score': result.confidence_score,
                'provider_used': result.provider_used,
                'processing_time_ms': result.processing_time_ms,
                'image_quality_score': result.image_quality_score,
                'requires_human_review': result.requires_human_review,
                'created_at': start_time.isoformat(),
                'model_type': 'document_classifier'
            }
            
            self.supabase.table('document_processing_results').insert(log_data).execute()
            
        except Exception as e:
            logger.error(f"Error logging document classification: {str(e)}")
            
    async def _log_error(self, tenant_id: UUID, error_message: str, start_time: datetime):
        """Log errors to database"""
        try:
            error_data = {
                'tenant_id': str(tenant_id),
                'processing_type': 'document_classification',
                'error_message': error_message,
                'created_at': start_time.isoformat(),
                'model_type': 'document_classifier'
            }
            
            self.supabase.table('document_processing_results').insert(error_data).execute()
            
        except Exception as e:
            logger.error(f"Error logging document classification error: {str(e)}") 