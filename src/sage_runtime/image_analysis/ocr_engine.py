"""
OCR Engine

Extracts text from images using OCR capabilities.
"""

import logging
from typing import Optional


logger = logging.getLogger(__name__)


class OCREngine:
    """OCR engine for text extraction from images."""

    def __init__(self):
        self._tesseract_available = False
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if OCR dependencies are available."""
        try:
            import pytesseract
            from PIL import Image
            self._tesseract_available = True
        except ImportError:
            logger.warning("[OCR_ENGINE] pytesseract or Pillow not available")

    async def extract_text(self, image_data: bytes) -> Optional[str]:
        """
        Extract text from image data.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Extracted text or None if OCR unavailable
        """
        if not self._tesseract_available:
            logger.warning("[OCR_ENGINE] OCR not available, returning None")
            return None
        
        try:
            import io
            from PIL import Image
            import pytesseract
            
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Extract text
            text = pytesseract.image_to_string(image)
            
            # Clean up text
            text = text.strip()
            
            if text:
                logger.debug(f"[OCR_ENGINE] Extracted {len(text)} characters")
                return text
            else:
                logger.debug("[OCR_ENGINE] No text found in image")
                return None
                
        except Exception as e:
            logger.error(f"[OCR_ENGINE] Text extraction failed: {e}")
            return None

    async def extract_text_with_boxes(
        self,
        image_data: bytes
    ) -> Optional[list]:
        """
        Extract text with bounding boxes.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            List of dicts with text and bounding box info
        """
        if not self._tesseract_available:
            return None
        
        try:
            import io
            from PIL import Image
            import pytesseract
            
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Extract text with boxes
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            # Format results
            results = []
            for i, text in enumerate(data['text']):
                if text.strip():
                    results.append({
                        'text': text,
                        'left': data['left'][i],
                        'top': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i],
                        'confidence': data['conf'][i]
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"[OCR_ENGINE] Text extraction with boxes failed: {e}")
            return None
