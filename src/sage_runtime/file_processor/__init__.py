"""
SAGE OS File Processing Layer

Handles file upload, parsing, and storage for various file types.
All uploaded files become available to Engineering Memory.
"""

from .processor import FileProcessor, ProcessedFile, FileType
from .parsers.pdf_parser import PDFParser
from .parsers.docx_parser import DocxParser
from .parsers.text_parser import TextParser
from .parsers.zip_parser import ZipParser
from .parsers.image_parser import ImageParser
from .parsers.code_parser import CodeParser

__all__ = [
    'FileProcessor',
    'ProcessedFile',
    'FileType',
    'PDFParser',
    'DocxParser',
    'TextParser',
    'ZipParser',
    'ImageParser',
    'CodeParser'
]
