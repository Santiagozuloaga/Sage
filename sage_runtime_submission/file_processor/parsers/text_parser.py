"""
Text Parser

Extracts text content from TXT and Markdown files.
"""

import logging
from typing import Dict, Any, Optional

from ..processor import ProcessedFile, FileType


logger = logging.getLogger(__name__)


class TextParser:
    """Parser for TXT and Markdown files."""

    async def parse(
        self,
        file_data: bytes,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedFile:
        """
        Parse text file and extract content.
        
        Args:
            file_data: Raw text bytes
            filename: Original filename
            metadata: Additional metadata
            
        Returns:
            ProcessedFile with text content
        """
        try:
            # Decode text with UTF-8, fallback to latin-1
            try:
                text_content = file_data.decode('utf-8')
            except UnicodeDecodeError:
                text_content = file_data.decode('latin-1')
            
            # Count lines, words, characters
            lines = text_content.split('\n')
            words = text_content.split()
            
            # Detect if markdown
            is_markdown = filename.lower().endswith('.md')
            
            text_metadata = {
                "line_count": len(lines),
                "word_count": len(words),
                "char_count": len(text_content),
                "is_markdown": is_markdown
            }
            
            # If markdown, count headers
            if is_markdown:
                headers = [line for line in lines if line.startswith('#')]
                text_metadata["header_count"] = len(headers)
            
            # Merge with provided metadata
            if metadata:
                text_metadata.update(metadata)
            
            return ProcessedFile(
                filename=filename,
                file_type=FileType.MARKDOWN if is_markdown else FileType.TXT,
                content=text_content,
                metadata=text_metadata
            )
            
        except Exception as e:
            logger.error(f"[TEXT_PARSER] Failed to parse text file: {e}")
            raise
