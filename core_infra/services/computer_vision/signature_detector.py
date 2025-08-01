"""Signature Detector for Computer Vision Service

This module provides signature detection and verification functionality
for document processing and authentication.
"""

import base64
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from PIL import Image, ImageFilter
import io
from dataclasses import dataclass
from datetime import datetime

from core_infra.config import settings
from core_infra.exceptions import ValidationError
from core_infra.monitoring.observability import monitor_performance

logger = logging.getLogger(__name__)


@dataclass
class SignatureRegion:
    """Represents a detected signature region in an image."""
    x: int
    y: int
    width: int
    height: int
    confidence: float
    signature_data: np.ndarray
    metadata: Dict[str, Any]


@dataclass
class SignatureVerificationResult:
    """Result of signature verification."""
    is_match: bool
    similarity_score: float
    confidence: float
    details: Dict[str, Any]


class SignatureDetector:
    """
    Signature detection and verification service.
    
    Features:
    - Signature region detection in documents
    - Signature extraction and preprocessing
    - Signature matching and verification
    - Forgery detection capabilities
    """
    
    def __init__(self):
        """Initialize signature detector with configuration."""
        self.min_signature_area = 500  # Minimum pixels for valid signature
        self.max_signature_area = 50000  # Maximum pixels for valid signature
        self.confidence_threshold = 0.7
        logger.info("Signature detector initialized")
    
    @monitor_performance
    async def detect_signatures(
        self, 
        image_data: bytes,
        expected_regions: Optional[List[Dict[str, int]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect signature regions in a document image.
        
        Args:
            image_data: Document image data
            expected_regions: Optional list of expected signature locations
            
        Returns:
            List of detected signature regions with metadata
        """
        try:
            # Decode image
            image = self._decode_image(image_data)
            
            # Preprocess for signature detection
            processed = self._preprocess_for_signatures(image)
            
            # Detect signature regions
            regions = self._detect_signature_regions(processed, expected_regions)
            
            # Extract and analyze each signature
            signatures = []
            for region in regions:
                signature_data = self._extract_signature(image, region)
                analysis = self._analyze_signature(signature_data)
                
                signatures.append({
                    "region": {
                        "x": region.x,
                        "y": region.y,
                        "width": region.width,
                        "height": region.height
                    },
                    "confidence": region.confidence,
                    "characteristics": analysis,
                    "timestamp": datetime.utcnow().isoformat(),
                    "quality_score": self._calculate_quality_score(signature_data)
                })
            
            return signatures
            
        except Exception as e:
            logger.error(f"Signature detection failed: {e}")
            return []
    
    async def verify_signature(
        self,
        signature_image: bytes,
        reference_signature: bytes,
        threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Verify if two signatures match.
        
        Args:
            signature_image: Signature to verify
            reference_signature: Reference signature for comparison
            threshold: Similarity threshold for verification
            
        Returns:
            Verification result with similarity score
        """
        try:
            # Decode both signatures
            sig_img = self._decode_image(signature_image)
            ref_img = self._decode_image(reference_signature)
            
            # Preprocess signatures
            sig_processed = self._preprocess_signature(sig_img)
            ref_processed = self._preprocess_signature(ref_img)
            
            # Calculate similarity
            similarity = self._calculate_similarity(sig_processed, ref_processed)
            
            # Check for forgery indicators
            forgery_score = self._detect_forgery_indicators(sig_processed, ref_processed)
            
            # Final verification
            is_verified = similarity >= threshold and forgery_score < 0.3
            
            return {
                "verified": is_verified,
                "similarity_score": float(similarity),
                "forgery_indicators": float(forgery_score),
                "confidence": float(similarity * (1 - forgery_score)),
                "threshold_used": threshold,
                "details": {
                    "preprocessing_applied": True,
                    "comparison_method": "structural_similarity",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return {
                "verified": False,
                "similarity_score": 0.0,
                "error": str(e)
            }
    
    def _decode_image(self, image_data: bytes) -> np.ndarray:
        """Decode image from bytes to numpy array."""
        try:
            if isinstance(image_data, str):
                image_data = base64.b64decode(image_data)
            
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to grayscale for signature processing
            if image.mode != 'L':
                image = image.convert('L')
            
            return np.array(image)
            
        except Exception as e:
            logger.error(f"Failed to decode image: {e}")
            raise ValidationError("Invalid image data")
    
    def _preprocess_for_signatures(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for signature detection."""
        try:
            # Apply edge detection to highlight signatures
            from PIL import Image as PILImage
            pil_image = PILImage.fromarray(image)
            
            # Apply edge enhancement
            enhanced = pil_image.filter(ImageFilter.EDGE_ENHANCE_MORE)
            
            # Convert back to numpy
            processed = np.array(enhanced)
            
            # Apply threshold to create binary image
            threshold = np.mean(processed) - np.std(processed)
            binary = (processed < threshold).astype(np.uint8) * 255
            
            return binary
            
        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            return image
    
    def _detect_signature_regions(
        self, 
        image: np.ndarray,
        expected_regions: Optional[List[Dict[str, int]]]
    ) -> List[SignatureRegion]:
        """Detect potential signature regions in the image."""
        regions = []
        
        # If expected regions provided, check those first
        if expected_regions:
            for exp_region in expected_regions:
                x, y = exp_region.get('x', 0), exp_region.get('y', 0)
                w, h = exp_region.get('width', 100), exp_region.get('height', 50)
                
                # Extract region
                region_data = image[y:y+h, x:x+w] if y+h <= image.shape[0] and x+w <= image.shape[1] else image
                
                # Check if contains signature
                if self._is_signature_region(region_data):
                    regions.append(SignatureRegion(
                        x=x, y=y, width=w, height=h,
                        confidence=0.9,
                        signature_data=region_data,
                        metadata={"source": "expected_region"}
                    ))
        
        # Scan for signatures using sliding window
        if not regions:
            regions.extend(self._scan_for_signatures(image))
        
        return regions
    
    def _scan_for_signatures(self, image: np.ndarray) -> List[SignatureRegion]:
        """Scan image for signature-like regions."""
        regions = []
        h, w = image.shape
        
        # Define typical signature dimensions
        sig_heights = [40, 60, 80]
        sig_widths = [150, 200, 250]
        
        # Simplified scanning - in production would use more sophisticated methods
        for sig_h in sig_heights:
            for sig_w in sig_widths:
                # Scan bottom portion of document (common signature location)
                for y in range(max(0, h - 300), h - sig_h, 20):
                    for x in range(0, w - sig_w, 50):
                        region = image[y:y+sig_h, x:x+sig_w]
                        
                        if self._is_signature_region(region):
                            regions.append(SignatureRegion(
                                x=x, y=y, width=sig_w, height=sig_h,
                                confidence=self._calculate_signature_confidence(region),
                                signature_data=region,
                                metadata={"source": "scan"}
                            ))
        
        # Return top candidates
        regions.sort(key=lambda r: r.confidence, reverse=True)
        return regions[:3]  # Max 3 signatures
    
    def _is_signature_region(self, region: np.ndarray) -> bool:
        """Check if region likely contains a signature."""
        if region.size == 0:
            return False
        
        # Calculate ink density
        ink_pixels = np.sum(region < 128)  # Dark pixels
        total_pixels = region.size
        ink_density = ink_pixels / total_pixels if total_pixels > 0 else 0
        
        # Signatures typically have 5-30% ink density
        if not (0.05 <= ink_density <= 0.3):
            return False
        
        # Check for connected components (signatures are usually connected)
        # Simplified check - count transitions
        horizontal_transitions = np.sum(np.diff(region[region.shape[0]//2] < 128))
        
        # Signatures have moderate number of transitions
        return 2 <= horizontal_transitions <= 20
    
    def _calculate_signature_confidence(self, region: np.ndarray) -> float:
        """Calculate confidence score for signature region."""
        # Factors: ink density, aspect ratio, smoothness
        
        # Ink density score
        ink_density = np.sum(region < 128) / region.size
        density_score = 1.0 - abs(ink_density - 0.15) / 0.15  # Optimal around 15%
        
        # Aspect ratio score
        h, w = region.shape
        aspect_ratio = w / h if h > 0 else 1
        ar_score = 1.0 - abs(aspect_ratio - 3.5) / 3.5  # Optimal around 3.5:1
        
        # Complexity score (based on variance)
        complexity = np.std(region) / 128
        
        # Combine scores
        confidence = (density_score * 0.3 + ar_score * 0.3 + complexity * 0.4)
        return max(0.0, min(1.0, confidence))
    
    def _extract_signature(self, image: np.ndarray, region: SignatureRegion) -> np.ndarray:
        """Extract signature from detected region."""
        # Extract with padding
        padding = 10
        y1 = max(0, region.y - padding)
        y2 = min(image.shape[0], region.y + region.height + padding)
        x1 = max(0, region.x - padding)
        x2 = min(image.shape[1], region.x + region.width + padding)
        
        return image[y1:y2, x1:x2]
    
    def _analyze_signature(self, signature: np.ndarray) -> Dict[str, Any]:
        """Analyze signature characteristics."""
        characteristics = {}
        
        # Stroke count (simplified)
        ink_pixels = signature < 128
        characteristics["estimated_strokes"] = self._estimate_stroke_count(ink_pixels)
        
        # Pressure variation (simulated through intensity variation)
        ink_intensities = signature[ink_pixels]
        characteristics["pressure_variation"] = float(np.std(ink_intensities)) if len(ink_intensities) > 0 else 0
        
        # Signature size
        characteristics["width"] = signature.shape[1]
        characteristics["height"] = signature.shape[0]
        characteristics["aspect_ratio"] = signature.shape[1] / signature.shape[0] if signature.shape[0] > 0 else 1
        
        # Complexity score
        characteristics["complexity"] = self._calculate_complexity(signature)
        
        return characteristics
    
    def _estimate_stroke_count(self, ink_pixels: np.ndarray) -> int:
        """Estimate number of strokes in signature."""
        # Simplified estimation based on connected components
        # In production, would use proper connected component analysis
        
        # Count horizontal gaps
        middle_row = ink_pixels[ink_pixels.shape[0]//2]
        gaps = 0
        in_gap = True
        
        for pixel in middle_row:
            if pixel and in_gap:
                gaps += 1
                in_gap = False
            elif not pixel:
                in_gap = True
        
        # Approximate stroke count
        return max(1, min(gaps + 1, 10))
    
    def _calculate_complexity(self, signature: np.ndarray) -> float:
        """Calculate signature complexity score."""
        # Based on edge density and curvature
        edges = np.gradient(signature.astype(float))
        edge_magnitude = np.sqrt(edges[0]**2 + edges[1]**2)
        
        complexity = np.mean(edge_magnitude) / 255
        return float(complexity)
    
    def _calculate_quality_score(self, signature: np.ndarray) -> float:
        """Calculate quality score of extracted signature."""
        # Factors: clarity, completeness, noise level
        
        # Clarity (contrast)
        if signature.size == 0:
            return 0.0
        
        clarity = (np.max(signature) - np.min(signature)) / 255
        
        # Completeness (no cut-off edges)
        edge_pixels = np.sum(signature[0] < 128) + np.sum(signature[-1] < 128)
        edge_pixels += np.sum(signature[:, 0] < 128) + np.sum(signature[:, -1] < 128)
        completeness = 1.0 - (edge_pixels / (2 * (signature.shape[0] + signature.shape[1])))
        
        # Noise level (simplified)
        noise_level = 1.0 - (np.std(signature) / 128)
        
        quality = clarity * 0.4 + completeness * 0.4 + noise_level * 0.2
        return max(0.0, min(1.0, quality))
    
    def _preprocess_signature(self, signature: np.ndarray) -> np.ndarray:
        """Preprocess signature for comparison."""
        # Normalize size
        target_height = 100
        aspect_ratio = signature.shape[1] / signature.shape[0] if signature.shape[0] > 0 else 1
        target_width = int(target_height * aspect_ratio)
        
        # Resize
        pil_sig = Image.fromarray(signature)
        resized = pil_sig.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Normalize intensity
        normalized = np.array(resized).astype(float) / 255.0
        
        return normalized
    
    def _calculate_similarity(self, sig1: np.ndarray, sig2: np.ndarray) -> float:
        """Calculate similarity between two signatures."""
        # Ensure same size
        min_h = min(sig1.shape[0], sig2.shape[0])
        min_w = min(sig1.shape[1], sig2.shape[1])
        
        sig1_cropped = sig1[:min_h, :min_w]
        sig2_cropped = sig2[:min_h, :min_w]
        
        # Calculate structural similarity
        # Simplified version - in production would use SSIM
        diff = np.abs(sig1_cropped - sig2_cropped)
        similarity = 1.0 - np.mean(diff)
        
        return similarity
    
    def _detect_forgery_indicators(self, sig1: np.ndarray, sig2: np.ndarray) -> float:
        """Detect potential forgery indicators."""
        # Look for signs of tracing or hesitation
        
        # Stroke smoothness difference
        smoothness1 = self._calculate_smoothness(sig1)
        smoothness2 = self._calculate_smoothness(sig2)
        smoothness_diff = abs(smoothness1 - smoothness2)
        
        # Speed indicators (simplified)
        # Forgeries often have more uniform intensity (traced slowly)
        intensity_var1 = np.var(sig1[sig1 < 0.5])
        intensity_var2 = np.var(sig2[sig2 < 0.5])
        intensity_diff = abs(intensity_var1 - intensity_var2)
        
        # Combine indicators
        forgery_score = smoothness_diff * 0.5 + intensity_diff * 0.5
        return min(1.0, forgery_score)
    
    def _calculate_smoothness(self, signature: np.ndarray) -> float:
        """Calculate smoothness of signature strokes."""
        # Based on curvature variation
        edges = np.gradient(signature.astype(float))
        curvature = np.gradient(edges[0]) + np.gradient(edges[1])
        
        smoothness = 1.0 / (1.0 + np.std(curvature))
        return smoothness 