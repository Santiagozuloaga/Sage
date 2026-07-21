"""
Language Detector

Detects programming languages from file extensions and content.
"""

import logging
from pathlib import Path
from typing import Dict, Optional


logger = logging.getLogger(__name__)


class LanguageDetector:
    """Detects programming languages from files."""

    # Language mapping by extension
    LANGUAGE_MAP = {
        # Python
        '.py': 'python',
        '.pyw': 'python',
        
        # JavaScript/TypeScript
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.mjs': 'javascript',
        '.cjs': 'javascript',
        
        # Java
        '.java': 'java',
        
        # C/C++
        '.c': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        '.hxx': 'cpp',
        
        # C#
        '.cs': 'csharp',
        
        # Go
        '.go': 'go',
        
        # Rust
        '.rs': 'rust',
        
        # Ruby
        '.rb': 'ruby',
        
        # PHP
        '.php': 'php',
        
        # Swift
        '.swift': 'swift',
        
        # Kotlin
        '.kt': 'kotlin',
        
        # Scala
        '.scala': 'scala',
        
        # Shell
        '.sh': 'shell',
        '.bash': 'shell',
        '.zsh': 'shell',
        '.fish': 'shell',
        '.ps1': 'powershell',
        
        # SQL
        '.sql': 'sql',
        
        # Web
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        
        # Data
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.ini': 'ini',
        '.cfg': 'ini',
        
        # Markdown
        '.md': 'markdown',
        '.markdown': 'markdown',
        
        # Text
        '.txt': 'text',
    }

    # Configuration files
    CONFIG_FILES = {
        'package.json': 'javascript',
        'tsconfig.json': 'typescript',
        'pom.xml': 'java',
        'build.gradle': 'java',
        'requirements.txt': 'python',
        'setup.py': 'python',
        'pyproject.toml': 'python',
        'Cargo.toml': 'rust',
        'go.mod': 'go',
        'composer.json': 'php',
        'Gemfile': 'ruby',
    }

    def __init__(self):
        self._custom_mappings: Dict[str, str] = {}

    def detect(self, file_path: Path) -> str:
        """
        Detect language from file path.
        
        Args:
            file_path: Path to file
            
        Returns:
            Language name
        """
        # Check custom mappings first
        if str(file_path) in self._custom_mappings:
            return self._custom_mappings[str(file_path)]
        
        # Check config files by name
        if file_path.name in self.CONFIG_FILES:
            return self.CONFIG_FILES[file_path.name]
        
        # Check by extension
        ext = file_path.suffix.lower()
        
        if ext in self.LANGUAGE_MAP:
            return self.LANGUAGE_MAP[ext]
        
        # Try content-based detection for unknown extensions
        return self._detect_by_content(file_path)

    def _detect_by_content(self, file_path: Path) -> str:
        """Detect language by file content."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Check for shebang
            if content.startswith('#!'):
                if 'python' in content[:100]:
                    return 'python'
                elif 'bash' in content[:100] or 'sh' in content[:100]:
                    return 'shell'
                elif 'node' in content[:100]:
                    return 'javascript'
            
            # Check for common patterns
            if 'def ' in content[:500] and 'import ' in content[:500]:
                return 'python'
            elif 'function ' in content[:500] and 'const ' in content[:500]:
                return 'javascript'
            elif 'public class ' in content[:500]:
                return 'java'
            elif 'package main' in content[:500]:
                return 'go'
            elif 'fn main' in content[:500]:
                return 'rust'
            
            return 'text'
            
        except Exception as e:
            logger.debug(f"[LANGUAGE_DETECTOR] Content detection failed for {file_path}: {e}")
            return 'unknown'

    def add_custom_mapping(self, file_path: str, language: str):
        """Add a custom file-to-language mapping."""
        self._custom_mappings[file_path] = language
