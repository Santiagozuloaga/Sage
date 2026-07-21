"""
Dependency Graph

Builds dependency graphs from import statements.
"""

import logging
from typing import Dict, Any, List, Set, Optional
from collections import defaultdict


logger = logging.getLogger(__name__)


class DependencyGraph:
    """Builds dependency graphs from code analysis."""

    def __init__(self):
        self._graph: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_graph: Dict[str, Set[str]] = defaultdict(set)

    async def build_graph(self, file_analyses: List) -> Dict[str, Any]:
        """
        Build dependency graph from file analyses.
        
        Args:
            file_analyses: List of FileAnalysis objects
            
        Returns:
            Dict with graph structure
        """
        self._graph.clear()
        self._reverse_graph.clear()
        
        # Build graph from imports
        for analysis in file_analyses:
            if not analysis.is_code:
                continue
            
            source_file = analysis.path
            
            for import_stmt in analysis.imports:
                # Try to resolve import to local file
                target_file = self._resolve_import(import_stmt, analysis.path, file_analyses)
                
                if target_file:
                    self._graph[source_file].add(target_file)
                    self._reverse_graph[target_file].add(source_file)
        
        # Calculate metrics
        metrics = self._calculate_metrics()
        
        return {
            'graph': {k: list(v) for k, v in self._graph.items()},
            'reverse_graph': {k: list(v) for k, v in self._reverse_graph.items()},
            'metrics': metrics
        }

    def _resolve_import(
        self,
        import_stmt: str,
        source_file: str,
        file_analyses: List
    ) -> Optional[str]:
        """Resolve import statement to local file path."""
        # Extract module name from import
        module_name = import_stmt.split('.')[0]
        
        # Look for matching files
        for analysis in file_analyses:
            filename = analysis.metadata.get('filename', '')
            name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
            
            if name_without_ext == module_name:
                return analysis.path
        
        return None

    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate graph metrics."""
        total_nodes = len(self._graph)
        total_edges = sum(len(deps) for deps in self._graph.values())
        
        # Calculate in-degree and out-degree
        in_degree = {node: len(self._reverse_graph[node]) for node in self._graph}
        out_degree = {node: len(self._graph[node]) for node in self._graph}
        
        # Find most connected nodes
        most_connected = sorted(out_degree.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_nodes': total_nodes,
            'total_edges': total_edges,
            'average_out_degree': total_edges / total_nodes if total_nodes > 0 else 0,
            'most_connected': most_connected
        }
