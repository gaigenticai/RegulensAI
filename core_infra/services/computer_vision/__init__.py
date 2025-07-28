"""
Computer Vision Service for Phase 6 Advanced AI & Automation

This module provides enterprise-grade computer vision capabilities including:
- Document classification and categorization
- KYC document verification and validation
- Signature and seal recognition
- OCR and form extraction
- Table and structured data extraction

Key Features:
- Multi-provider support (AWS Textract, Azure Form Recognizer, Google Vision)
- Real-time document processing
- Confidence scoring and validation workflows
- Multi-format support (PDF, JPG, PNG, TIFF)
- Enterprise audit trails and compliance
"""

from .cv_service import ComputerVisionService, CVRequest, CVResult, CVProvider, ProcessingType
from .document_classifier import DocumentClassifier
from .kyc_verifier import KYCVerifier
from .signature_detector import SignatureDetector
from .ocr_processor import OCRProcessor
from .form_extractor import FormExtractor

__all__ = [
    'ComputerVisionService',
    'CVRequest',
    'CVResult', 
    'CVProvider',
    'ProcessingType',
    'DocumentClassifier',
    'KYCVerifier',
    'SignatureDetector',
    'OCRProcessor',
    'FormExtractor'
]

__version__ = "1.0.0" 