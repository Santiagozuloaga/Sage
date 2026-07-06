"""
ZIP Parser

Extracts and processes files from ZIP archives.
"""

import logging
import zipfile
import io
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..processor import ProcessedFile, FileType


logger = logging.getLogger(__name__)


class ZipParser:
    """Parser for ZIP files."""

    async def parse(
        self,
        file_data: bytes,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedFile:
        """
        Parse ZIP file and extract contents.
        
        Args:
            file_data: Raw ZIP bytes
            filename: Original filename
            metadata: Additional metadata
            
        Returns:
            ProcessedFile with list of extracted files
        """
        try:
            zip_file = io.BytesIO(file_data)
            
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                # Extract metadata for each file
                extracted_files = []
                for file_path in file_list:
                    file_info = zip_ref.getinfo(file_path)
                    extracted_files.append({
                        "path": file_path,
                        "size": file_info.file_size,
                        "compressed_size": file_info.compress_size,
                        "is_directory": file_info.is_dir()
                    })
                
                # Extract text content from text files in ZIP
                text_contents = []
                for file_path in file_list:
                    if not file_path.endswith('/') and file_path.lower().endswith(('.txt', '.md', '.py', '.js', '.json', '.xml', '.yaml', '.yml')):
                        try:
                            with zip_ref.open(file_path) as f:
                                content = f.read().decode('utf-8', errors='ignore')
                                text_contents.append(f"\n--- {file_path} ---\n{content}")
                        except Exception as e:
                            logger.warning(f"[ZIP_PARSER] Failed to extract {file_path}: {e}")
                
                full_text = "\n".join(text_contents) if text_contents else "ZIP archive contains no extractable text files."
                
                zip_metadata = {
                    "file_count": len(file_list),
                    "total_size": sum(f.file_size for f in zip_ref.filelist),
                    "compressed_size": sum(f.compress_size for f in zip_ref.filelist),
                    "extracted_files": extracted_files
                }
                
                # Merge with provided metadata
                if metadata:
                    zip_metadata.update(metadata)
                
                return ProcessedFile(
                    filename=filename,
                    file_type=FileType.ZIP,
                    content=full_text,
                    metadata=zip_metadata,
                    extracted_files=extracted_files
                )
                
        except Exception as e:
            logger.error(f"[ZIP_PARSER] Failed to parse ZIP: {e}")
            raise
