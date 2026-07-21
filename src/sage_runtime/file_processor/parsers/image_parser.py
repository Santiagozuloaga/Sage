"""
Image Parser

Processes image files and extracts metadata.
"""

import logging
from typing import Dict, Any, Optional

try:
    from PIL import Image
    from PIL import ImageOps
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from ..processor import ProcessedFile, FileType


logger = logging.getLogger(__name__)


class ImageParser:
    """Parser for image files."""

    def __init__(self):
        if not PILLOW_AVAILABLE:
            logger.warning("[IMAGE_PARSER] Pillow not installed")

    async def parse(
        self,
        file_data: bytes,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedFile:
        """
        Parse image file and extract metadata.
        
        Args:
            file_data: Raw image bytes
            filename: Original filename
            metadata: Additional metadata
            
        Returns:
            ProcessedFile with image metadata
        """
        if not PILLOW_AVAILABLE:
            raise ImportError("Pillow not installed. Install with: pip install Pillow")
        
        try:
            import io
            
            image_file = io.BytesIO(file_data)
            image = Image.open(image_file)
            
            # Extract image metadata
            image_metadata = {
                "format": image.format,
                "mode": image.mode,
                "size": image.size,
                "width": image.width,
                "height": image.height,
                "has_transparency": image.mode in ('RGBA', 'LA', 'P')
            }
            
            # Get EXIF data if available
            if hasattr(image, '_getexif'):
                try:
                    exif = image._getexif()
                    if exif:
                        image_metadata["exif"] = dict(exif)
                except Exception as e:
                    logger.debug(f"[IMAGE_PARSER] Failed to extract EXIF: {e}")
            
            # Merge with provided metadata
            if metadata:
                image_metadata.update(metadata)
            
            # Content is a description of the image
            content = f"Image file: {filename}\nFormat: {image.format}\nSize: {image.size[0]}x{image.size[1]}\nMode: {image.mode}"
            
            return ProcessedFile(
                filename=filename,
                file_type=FileType.IMAGE,
                content=content,
                metadata=image_metadata
            )
            
        except Exception as e:
            logger.error(f"[IMAGE_PARSER] Failed to parse image: {e}")
            raise
