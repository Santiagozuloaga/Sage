"""
Code Parser

Extracts and analyzes source code files.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

from ..processor import ProcessedFile, FileType


logger = logging.getLogger(__name__)


class CodeParser:
    """Parser for source code files."""

    # Language detection by extension
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.c': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.sh': 'shell',
        '.bash': 'shell',
        '.zsh': 'shell',
        '.fish': 'shell',
        '.ps1': 'powershell',
        '.sql': 'sql',
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.ini': 'ini',
        '.cfg': 'ini',
        '.conf': 'ini',
    }

    async def parse(
        self,
        file_data: bytes,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedFile:
        """
        Parse source code file and extract content.
        
        Args:
            file_data: Raw code bytes
            filename: Original filename
            metadata: Additional metadata
            
        Returns:
            ProcessedFile with code content
        """
        try:
            # Detect language
            ext = Path(filename).suffix.lower()
            language = self.LANGUAGE_MAP.get(ext, 'unknown')
            
            # Decode text
            try:
                code_content = file_data.decode('utf-8')
            except UnicodeDecodeError:
                code_content = file_data.decode('latin-1')
            
            # Count lines, functions, classes (basic heuristics)
            lines = code_content.split('\n')
            non_empty_lines = [l for l in lines if l.strip()]
            
            # Basic code metrics
            code_metadata = {
                "language": language,
                "line_count": len(lines),
                "non_empty_line_count": len(non_empty_lines),
                "char_count": len(code_content)
            }
            
            # Language-specific heuristics
            if language == 'python':
                code_metadata.update(self._analyze_python(code_content))
            elif language in ('javascript', 'typescript'):
                code_metadata.update(self._analyze_javascript(code_content))
            elif language == 'java':
                code_metadata.update(self._analyze_java(code_content))
            elif language == 'go':
                code_metadata.update(self._analyze_go(code_content))
            elif language == 'rust':
                code_metadata.update(self._analyze_rust(code_content))
            
            # Merge with provided metadata
            if metadata:
                code_metadata.update(metadata)
            
            return ProcessedFile(
                filename=filename,
                file_type=FileType.CODE,
                content=code_content,
                metadata=code_metadata
            )
            
        except Exception as e:
            logger.error(f"[CODE_PARSER] Failed to parse code file: {e}")
            raise

    def _analyze_python(self, code: str) -> Dict[str, Any]:
        """Basic Python code analysis."""
        return {
            "function_count": code.count('def '),
            "class_count": code.count('class '),
            "import_count": code.count('import ') + code.count('from '),
            "comment_count": code.count('#')
        }

    def _analyze_javascript(self, code: str) -> Dict[str, Any]:
        """Basic JavaScript/TypeScript code analysis."""
        return {
            "function_count": code.count('function ') + code.count('=>'),
            "class_count": code.count('class '),
            "import_count": code.count('import '),
            "export_count": code.count('export ')
        }

    def _analyze_java(self, code: str) -> Dict[str, Any]:
        """Basic Java code analysis."""
        return {
            "class_count": code.count('class '),
            "interface_count": code.count('interface '),
            "method_count": code.count('public ') + code.count('private ') + code.count('protected '),
            "import_count": code.count('import ')
        }

    def _analyze_go(self, code: str) -> Dict[str, Any]:
        """Basic Go code analysis."""
        return {
            "function_count": code.count('func '),
            "import_count": code.count('import '),
            "package_count": code.count('package ')
        }

    def _analyze_rust(self, code: str) -> Dict[str, Any]:
        """Basic Rust code analysis."""
        return {
            "function_count": code.count('fn '),
            "struct_count": code.count('struct '),
            "impl_count": code.count('impl '),
            "use_count": code.count('use ')
        }
