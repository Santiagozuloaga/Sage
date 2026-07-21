"""
Image Analyzer

Provides image analysis capabilities using LLM providers.
"""

import logging
import base64
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class ImageAnalysisResult:
    """Result of image analysis."""
    description: str
    classification: str
    ocr_text: Optional[str] = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = None
    analyzed_at: datetime = None
    
    def __post_init__(self):
        if self.analyzed_at is None:
            self.analyzed_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class ImageAnalyzer:
    """
    Image analyzer using LLM providers.
    
    Integrates with ProviderRouter to generate image descriptions
    and classifications using vision-capable models.
    """

    def __init__(self, provider_router=None):
        self._provider_router = provider_router
        self._ocr_engine = None
        self._initialize_ocr()

    def _initialize_ocr(self):
        """Initialize OCR engine."""
        try:
            from .ocr_engine import OCREngine
            self._ocr_engine = OCREngine()
            logger.info("[IMAGE_ANALYSIS] OCR engine initialized")
        except Exception as e:
            logger.warning(f"[IMAGE_ANALYSIS] OCR engine initialization failed: {e}")

    def set_provider_router(self, provider_router):
        """Set the provider router for LLM integration."""
        self._provider_router = provider_router

    async def analyze_image(
        self,
        image_data: bytes,
        image_format: str = "png"
    ) -> ImageAnalysisResult:
        """
        Analyze an image using LLM providers.
        
        Args:
            image_data: Raw image bytes
            image_format: Image format (png, jpg, etc.)
            
        Returns:
            ImageAnalysisResult with description and classification
        """
        # Encode image to base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # Generate description using LLM
        description = ""
        classification = ""
        
        if self._provider_router:
            try:
                # Use provider's analyze_image method
                from providers.base_provider import ProviderResponse
                response = await self._provider_router.analyze_image(
                    image_data=image_data,
                    image_format=image_format
                )
                
                if response:
                    description = response.content
                    classification = self._classify_from_description(description)
            except Exception as e:
                logger.error(f"[IMAGE_ANALYSIS] LLM analysis failed: {e}")
                description = "Analysis unavailable"
                classification = "unknown"
        else:
            description = "No provider router available for analysis"
            classification = "unknown"
        
        # Perform OCR if available
        ocr_text = None
        if self._ocr_engine:
            try:
                ocr_text = await self._ocr_engine.extract_text(image_data)
            except Exception as e:
                logger.warning(f"[IMAGE_ANALYSIS] OCR failed: {e}")
        
        return ImageAnalysisResult(
            description=description,
            classification=classification,
            ocr_text=ocr_text,
            metadata={
                "format": image_format,
                "size_bytes": len(image_data)
            }
        )

    def _classify_from_description(self, description: str) -> str:
        """Classify image based on description."""
        description_lower = description.lower()
        
        # Simple classification based on keywords (check more specific patterns first)
        categories = {
            "screenshot": ["screenshot", "interface", "ui", "button", "menu"],
            "chart": ["chart", "graph", "diagram", "plot", "bar chart", "line chart"],
            "document": ["text", "document", "paper", "writing", "page"],
            "technology": ["computer", "phone", "device", "laptop", "keyboard"],
            "vehicle": ["car", "truck", "vehicle", "automobile", "bus", "motorcycle"],
            "building": ["building", "house", "architecture", "structure", "office"],
            "nature": ["tree", "mountain", "sky", "ocean", "forest", "landscape", "beach"],
            "animal": ["dog", "cat", "animal", "bird", "pet", "horse"],
            "person": ["person", "human", "face", "man", "woman", "people"],
            "food": ["food", "meal", "dish", "restaurant", "pizza", "burger"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in description_lower for keyword in keywords):
                return category
        
        return "general"

    async def analyze_image_from_path(
        self,
        image_path: str
    ) -> ImageAnalysisResult:
        """
        Analyze an image from file path.
        
        Args:
            image_path: Path to image file
            
        Returns:
            ImageAnalysisResult with analysis
        """
        from pathlib import Path
        
        image_file = Path(image_path)
        if not image_file.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        image_data = image_file.read_bytes()
        image_format = image_file.suffix[1:]  # Remove dot
        
        return await self.analyze_image(image_data, image_format)
