"""
SAGE OS File Processor

Main processor for handling file uploads and parsing.
Routes files to appropriate parsers based on type.
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime


logger = logging.getLogger(__name__)


class FileType(Enum):
    """Supported file types."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "md"
    ZIP = "zip"
    IMAGE = "image"
    CODE = "code"
    UNKNOWN = "unknown"


@dataclass
class ProcessedFile:
    """Result of file processing."""
    filename: str
    file_type: FileType
    content: str
    metadata: Dict[str, Any]
    extracted_files: Optional[list] = None
    processed_at: datetime = None
    
    def __post_init__(self):
        if self.processed_at is None:
            self.processed_at = datetime.now()


class FileProcessor:
    """
    Main file processor.
    
    Routes files to appropriate parsers and returns processed content.
    All uploaded files become available to Engineering Memory.
    """

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._parsers = {}
        self._initialize_parsers()

    def _initialize_parsers(self):
        """Initialize all parsers."""
        try:
            from .parsers.pdf_parser import PDFParser
            self._parsers[FileType.PDF] = PDFParser()
            logger.info("[FILE_PROCESSOR] PDF parser initialized")
        except ImportError:
            logger.warning("[FILE_PROCESSOR] PDF parser not available (PyPDF2 not installed)")
        
        try:
            from .parsers.docx_parser import DocxParser
            self._parsers[FileType.DOCX] = DocxParser()
            logger.info("[FILE_PROCESSOR] DOCX parser initialized")
        except ImportError:
            logger.warning("[FILE_PROCESSOR] DOCX parser not available (python-docx not installed)")
        
        try:
            from .parsers.text_parser import TextParser
            self._parsers[FileType.TXT] = TextParser()
            self._parsers[FileType.MARKDOWN] = TextParser()
            logger.info("[FILE_PROCESSOR] Text parser initialized")
        except ImportError:
            logger.warning("[FILE_PROCESSOR] Text parser not available")
        
        try:
            from .parsers.zip_parser import ZipParser
            self._parsers[FileType.ZIP] = ZipParser()
            logger.info("[FILE_PROCESSOR] ZIP parser initialized")
        except ImportError:
            logger.warning("[FILE_PROCESSOR] ZIP parser not available")
        
        try:
            from .parsers.image_parser import ImageParser
            self._parsers[FileType.IMAGE] = ImageParser()
            logger.info("[FILE_PROCESSOR] Image parser initialized")
        except ImportError:
            logger.warning("[FILE_PROCESSOR] Image parser not available (Pillow not installed)")
        
        try:
            from .parsers.code_parser import CodeParser
            self._parsers[FileType.CODE] = CodeParser()
            logger.info("[FILE_PROCESSOR] Code parser initialized")
        except ImportError:
            logger.warning("[FILE_PROCESSOR] Code parser not available")

    def detect_file_type(self, filename: str) -> FileType:
        """Detect file type from extension."""
        ext = Path(filename).suffix.lower()
        
        type_mapping = {
            '.pdf': FileType.PDF,
            '.docx': FileType.DOCX,
            '.txt': FileType.TXT,
            '.md': FileType.MARKDOWN,
            '.zip': FileType.ZIP,
            '.jpg': FileType.IMAGE,
            '.jpeg': FileType.IMAGE,
            '.png': FileType.IMAGE,
            '.gif': FileType.IMAGE,
            '.bmp': FileType.IMAGE,
            '.webp': FileType.IMAGE,
        }
        
        # Check for code files
        code_extensions = {
            '.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.hpp',
            '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
            '.sh', '.bash', '.zsh', '.fish', '.ps1', '.sql', '.html', '.css',
            '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg'
        }
        
        if ext in code_extensions:
            return FileType.CODE
        
        return type_mapping.get(ext, FileType.UNKNOWN)

    async def process_file(
        self,
        file_data: bytes,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedFile:
        """
        Process an uploaded file.
        
        Args:
            file_data: Raw file bytes
            filename: Original filename
            metadata: Additional metadata
            
        Returns:
            ProcessedFile with extracted content
        """
        file_type = self.detect_file_type(filename)
        logger.info(f"[FILE_PROCESSOR] Processing {filename} as {file_type.value}")
        
        if file_type == FileType.UNKNOWN:
            logger.warning(f"[FILE_PROCESSOR] Unknown file type: {filename}")
            # Try to process as text
            file_type = FileType.TXT
        
        parser = self._parsers.get(file_type)
        
        if not parser:
            raise ValueError(f"No parser available for file type: {file_type.value}")
        
        try:
            # Store file
            file_path = self.storage_dir / filename
            file_path.write_bytes(file_data)
            
            # Parse file
            result = await parser.parse(file_data, filename, metadata or {})
            
            logger.info(f"[FILE_PROCESSOR] Successfully processed {filename}")
            return result
            
        except Exception as e:
            logger.error(f"[FILE_PROCESSOR] Failed to process {filename}: {e}")
            raise

    async def process_file_path(
        self,
        file_path: Path,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedFile:
        """
        Process a file from path.
        
        Args:
            file_path: Path to file
            metadata: Additional metadata
            
        Returns:
            ProcessedFile with extracted content
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_data = file_path.read_bytes()
        return await self.process_file(file_data, file_path.name, metadata)

    def get_supported_types(self) -> list[FileType]:
        """Get list of supported file types."""
        return list(self._parsers.keys())

    def cleanup_old_files(self, max_age_days: int = 7):
        """Clean up files older than max_age_days."""
        cutoff = datetime.now().timestamp() - (max_age_days * 86400)
        
        for file_path in self.storage_dir.iterdir():
            if file_path.is_file() and file_path.stat().st_mtime < cutoff:
                file_path.unlink()
                logger.debug(f"[FILE_PROCESSOR] Cleaned up old file: {file_path.name}")
