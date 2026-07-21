"""
PDF Parser

Extracts text content from PDF files.
"""

import logging
from typing import Dict, Any, Optional

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

from ..processor import ProcessedFile, FileType


logger = logging.getLogger(__name__)


class PDFParser:
    """Parser for PDF files."""

    def __init__(self):
        if not PYPDF2_AVAILABLE:
            logger.warning("[PDF_PARSER] PyPDF2 not installed")

    async def parse(
        self,
        file_data: bytes,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedFile:
        """
        Parse PDF file and extract text.
        
        Args:
            file_data: Raw PDF bytes
            filename: Original filename
            metadata: Additional metadata
            
        Returns:
            ProcessedFile with extracted text
        """
        if not PYPDF2_AVAILABLE:
            raise ImportError("PyPDF2 not installed. Install with: pip install PyPDF2")
        
        try:
            import io
            
            pdf_file = io.BytesIO(file_data)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Extract text from all pages
            text_content = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text.strip():
                        text_content.append(f"--- Page {page_num + 1} ---\n{text}")
                except Exception as e:
                    logger.warning(f"[PDF_PARSER] Failed to extract page {page_num}: {e}")
            
            full_text = "\n\n".join(text_content)
            
            # Extract metadata
            pdf_metadata = {
                "page_count": len(pdf_reader.pages),
                "is_encrypted": pdf_reader.is_encrypted
            }
            
            if pdf_reader.metadata:
                pdf_metadata.update({
                    "title": pdf_reader.metadata.get('/Title', ''),
                    "author": pdf_reader.metadata.get('/Author', ''),
                    "subject": pdf_reader.metadata.get('/Subject', ''),
                    "creator": pdf_reader.metadata.get('/Creator', '')
                })
            
            # Merge with provided metadata
            if metadata:
                pdf_metadata.update(metadata)
            
            return ProcessedFile(
                filename=filename,
                file_type=FileType.PDF,
                content=full_text,
                metadata=pdf_metadata
            )
            
        except Exception as e:
            logger.error(f"[PDF_PARSER] Failed to parse PDF: {e}")
            raise
