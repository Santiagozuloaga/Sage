"""
Repository Scanner

Main scanner for recursive repository traversal and analysis.
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import Counter


logger = logging.getLogger(__name__)


@dataclass
class FileAnalysis:
    """Analysis result for a single file."""
    path: str
    language: str
    line_count: int
    size_bytes: int
    is_code: bool
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanResult:
    """Result of repository scan."""
    repository_path: str
    total_files: int
    total_lines: int
    total_size_bytes: int
    languages: Dict[str, int]  # language -> file count
    file_analyses: List[FileAnalysis] = field(default_factory=list)
    dependency_graph: Optional[Dict[str, Any]] = None
    summary: str = ""
    scanned_at: datetime = None
    
    def __post_init__(self):
        if self.scanned_at is None:
            self.scanned_at = datetime.now()


class RepositoryScanner:
    """
    Scanner for repository analysis.
    
    Performs recursive scanning, language detection, AST parsing,
    dependency graph generation, and summary creation.
    """

    def __init__(self):
        self._language_detector = None
        self._ast_parser = None
        self._dependency_graph = None
        self._initialize_components()

    def _initialize_components(self):
        """Initialize scanner components."""
        try:
            from .language_detector import LanguageDetector
            self._language_detector = LanguageDetector()
            logger.info("[REPO_SCANNER] Language detector initialized")
        except Exception as e:
            logger.warning(f"[REPO_SCANNER] Language detector initialization failed: {e}")
        
        try:
            from .ast_parser import ASTParser
            self._ast_parser = ASTParser()
            logger.info("[REPO_SCANNER] AST parser initialized")
        except Exception as e:
            logger.warning(f"[REPO_SCANNER] AST parser initialization failed: {e}")
        
        try:
            from .dependency_graph import DependencyGraph
            self._dependency_graph = DependencyGraph()
            logger.info("[REPO_SCANNER] Dependency graph initialized")
        except Exception as e:
            logger.warning(f"[REPO_SCANNER] Dependency graph initialization failed: {e}")

    async def scan_repository(
        self,
        repository_path: Path,
        exclude_dirs: Optional[List[str]] = None,
        exclude_files: Optional[List[str]] = None
    ) -> ScanResult:
        """
        Scan a repository recursively.
        
        Args:
            repository_path: Path to repository
            exclude_dirs: Directories to exclude (e.g., ['.git', 'node_modules'])
            exclude_files: File patterns to exclude (e.g., ['*.pyc', '*.log'])
            
        Returns:
            ScanResult with analysis
        """
        if not repository_path.exists():
            raise FileNotFoundError(f"Repository not found: {repository_path}")
        
        exclude_dirs = exclude_dirs or ['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build']
        exclude_files = exclude_files or ['*.pyc', '*.log', '*.tmp', '.DS_Store']
        
        logger.info(f"[REPO_SCANNER] Scanning repository: {repository_path}")
        
        file_analyses = []
        total_lines = 0
        total_size = 0
        language_counter = Counter()
        
        # Recursive scan
        for root, dirs, files in os.walk(repository_path):
            # Filter excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_path = Path(root) / file
                
                # Filter excluded files
                if any(file_path.match(pattern) for pattern in exclude_files):
                    continue
                
                # Analyze file
                analysis = await self._analyze_file(file_path)
                
                if analysis:
                    file_analyses.append(analysis)
                    total_lines += analysis.line_count
                    total_size += analysis.size_bytes
                    language_counter[analysis.language] += 1
        
        # Build dependency graph
        dep_graph = None
        if self._dependency_graph:
            dep_graph = await self._dependency_graph.build_graph(file_analyses)
        
        # Generate summary
        summary = self._generate_summary(
            repository_path,
            len(file_analyses),
            total_lines,
            total_size,
            dict(language_counter)
        )
        
        result = ScanResult(
            repository_path=str(repository_path),
            total_files=len(file_analyses),
            total_lines=total_lines,
            total_size_bytes=total_size,
            languages=dict(language_counter),
            file_analyses=file_analyses,
            dependency_graph=dep_graph,
            summary=summary
        )
        
        logger.info(f"[REPO_SCANNER] Scan complete: {len(file_analyses)} files, {total_lines} lines")
        return result

    async def _analyze_file(self, file_path: Path) -> Optional[FileAnalysis]:
        """Analyze a single file."""
        try:
            # Detect language
            language = "unknown"
            if self._language_detector:
                language = self._language_detector.detect(file_path)
            
            # Read file
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            
            # Basic metrics
            line_count = len(lines)
            size_bytes = file_path.stat().st_size
            is_code = language != "unknown" and language != "text"
            
            # AST parsing for code files
            functions = []
            classes = []
            imports = []
            
            if is_code and self._ast_parser:
                ast_result = self._ast_parser.parse(content, language)
                functions = ast_result.get('functions', [])
                classes = ast_result.get('classes', [])
                imports = ast_result.get('imports', [])
            
            return FileAnalysis(
                path=str(file_path),
                language=language,
                line_count=line_count,
                size_bytes=size_bytes,
                is_code=is_code,
                functions=functions,
                classes=classes,
                imports=imports,
                metadata={
                    "extension": file_path.suffix,
                    "filename": file_path.name
                }
            )
            
        except Exception as e:
            logger.warning(f"[REPO_SCANNER] Failed to analyze {file_path}: {e}")
            return None

    def _generate_summary(
        self,
        repository_path: Path,
        total_files: int,
        total_lines: int,
        total_size: int,
        languages: Dict[str, int]
    ) -> str:
        """Generate repository summary."""
        summary_lines = [
            f"Repository: {repository_path.name}",
            f"Total Files: {total_files}",
            f"Total Lines: {total_lines}",
            f"Total Size: {total_size / 1024:.2f} KB",
            f"Languages: {', '.join(f'{lang} ({count})' for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True))}"
        ]
        
        return "\n".join(summary_lines)
