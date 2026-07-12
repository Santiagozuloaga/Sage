"""
AST Parser

Parses Abstract Syntax Trees for supported languages.
"""

import logging
from typing import Dict, Any, List, Optional


logger = logging.getLogger(__name__)


class ASTParser:
    """Parses AST for code analysis."""

    def __init__(self):
        self._python_available = False
        self._javascript_available = False
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if AST parsing dependencies are available."""
        try:
            import ast
            self._python_available = True
        except ImportError:
            pass
        
        # JavaScript AST would require additional dependencies
        # For now, we'll use regex-based heuristics
        self._javascript_available = True

    def parse(self, content: str, language: str) -> Dict[str, Any]:
        """
        Parse code and extract structure.
        
        Args:
            content: Source code content
            language: Programming language
            
        Returns:
            Dict with functions, classes, imports
        """
        if language == 'python' and self._python_available:
            return self._parse_python(content)
        elif language in ('javascript', 'typescript'):
            return self._parse_javascript(content)
        elif language == 'java':
            return self._parse_java(content)
        elif language == 'go':
            return self._parse_go(content)
        elif language == 'rust':
            return self._parse_rust(content)
        else:
            return self._parse_generic(content)

    def _parse_python(self, content: str) -> Dict[str, Any]:
        """Parse Python code using AST."""
        try:
            import ast
            
            tree = ast.parse(content)
            
            functions = []
            classes = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.AsyncFunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")
            
            return {
                'functions': functions,
                'classes': classes,
                'imports': imports
            }
            
        except Exception as e:
            logger.warning(f"[AST_PARSER] Python parsing failed: {e}")
            return self._parse_generic(content)

    def _parse_javascript(self, content: str) -> Dict[str, Any]:
        """Parse JavaScript/TypeScript using regex heuristics."""
        import re
        
        functions = []
        classes = []
        imports = []
        
        # Function detection
        func_pattern = r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(|(\w+)\s*\([^)]*\)\s*=>)'
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1) or match.group(2) or match.group(3)
            if func_name:
                functions.append(func_name)
        
        # Class detection
        class_pattern = r'class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            classes.append(match.group(1))
        
        # Import detection
        import_patterns = [
            r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',
            r'require\([\'"]([^\'"]+)[\'"]\)',
            r'import\s+[\'"]([^\'"]+)[\'"]'
        ]
        
        for pattern in import_patterns:
            for match in re.finditer(pattern, content):
                imports.append(match.group(1))
        
        return {
            'functions': functions,
            'classes': classes,
            'imports': imports
        }

    def _parse_java(self, content: str) -> Dict[str, Any]:
        """Parse Java using regex heuristics."""
        import re
        
        functions = []
        classes = []
        imports = []
        
        # Class detection
        class_pattern = r'(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            classes.append(match.group(1))
        
        # Method detection
        method_pattern = r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\([^)]*\)'
        for match in re.finditer(method_pattern, content):
            method_name = match.group(1)
            if method_name not in ['if', 'for', 'while', 'switch', 'catch']:
                functions.append(method_name)
        
        # Import detection
        import_pattern = r'import\s+([^;]+);'
        for match in re.finditer(import_pattern, content):
            imports.append(match.group(1).strip())
        
        return {
            'functions': functions,
            'classes': classes,
            'imports': imports
        }

    def _parse_go(self, content: str) -> Dict[str, Any]:
        """Parse Go using regex heuristics."""
        import re
        
        functions = []
        classes = []
        imports = []
        
        # Function detection
        func_pattern = r'func\s+(?:\([^)]*\)\s+)?(\w+)\s*\('
        for match in re.finditer(func_pattern, content):
            functions.append(match.group(1))
        
        # Struct detection (as classes)
        struct_pattern = r'type\s+(\w+)\s+struct'
        for match in re.finditer(struct_pattern, content):
            classes.append(match.group(1))
        
        # Import detection
        import_pattern = r'import\s+(?:\([^)]+\)|"([^"]+)")'
        for match in re.finditer(import_pattern, content):
            imports.append(match.group(1) if match.group(1) else 'multi-import')
        
        return {
            'functions': functions,
            'classes': classes,
            'imports': imports
        }

    def _parse_rust(self, content: str) -> Dict[str, Any]:
        """Parse Rust using regex heuristics."""
        import re
        
        functions = []
        classes = []
        imports = []
        
        # Function detection
        func_pattern = r'fn\s+(\w+)\s*\('
        for match in re.finditer(func_pattern, content):
            functions.append(match.group(1))
        
        # Struct detection (as classes)
        struct_pattern = r'struct\s+(\w+)'
        impl_pattern = r'impl\s+(\w+)'
        
        for match in re.finditer(struct_pattern, content):
            classes.append(match.group(1))
        for match in re.finditer(impl_pattern, content):
            classes.append(match.group(1))
        
        # Import detection
        import_pattern = r'use\s+([^;]+);'
        for match in re.finditer(import_pattern, content):
            imports.append(match.group(1).strip())
        
        return {
            'functions': functions,
            'classes': classes,
            'imports': imports
        }

    def _parse_generic(self, content: str) -> Dict[str, Any]:
        """Generic parsing for unsupported languages."""
        import re
        
        functions = []
        classes = []
        imports = []
        
        # Generic function pattern
        func_pattern = r'(?:def|function|func)\s+(\w+)'
        for match in re.finditer(func_pattern, content):
            functions.append(match.group(1))
        
        # Generic class pattern
        class_pattern = r'class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            classes.append(match.group(1))
        
        # Generic import pattern
        import_pattern = r'(?:import|require|use|from)\s+[\'"]?([^\'"\s;]+)[\'"]?'
        for match in re.finditer(import_pattern, content):
            imports.append(match.group(1))
        
        return {
            'functions': functions,
            'classes': classes,
            'imports': imports
        }
