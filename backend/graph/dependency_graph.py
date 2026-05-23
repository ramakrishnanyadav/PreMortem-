"""
dependency_graph.py
-------------------
Maintains the directed causal dependency graph using NetworkX.
For Phase 1, this uses hardcoded edges.
"""
import networkx as nx
import structlog
import threading
from typing import List, Dict, Any

logger = structlog.get_logger(__name__)

class DependencyGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self._lock = threading.Lock()
        self._init_hardcoded_edges()

    def _init_hardcoded_edges(self):
        """Initial hardcoded causal edges for Phase 1 display and basic traversal."""
        edges = [
            ("github", "vercel", 0.8),
            ("github", "cloudflare", 0.4),
            ("npm", "vercel", 0.9),
            ("npm", "github", 0.3),
            ("cloudflare", "stripe", 0.6),
            ("datadog", "vercel", 0.2),
            ("docker", "github", 0.5)
        ]
        with self._lock:
            for u, v, w in edges:
                self.graph.add_edge(u, v, weight=w)
                
            # Ensure nodes exist even if disconnected initially
            for node in ["github", "vercel", "cloudflare", "stripe", "datadog", "npm", "docker"]:
                if not self.graph.has_node(node):
                    self.graph.add_node(node)
                    
        logger.info("dependency_graph_initialized", num_nodes=self.graph.number_of_nodes(), num_edges=self.graph.number_of_edges())

    def update_edge(self, u: str, v: str, weight: float, lag_minutes: float = 0.0, edge_type: str = "pearson"):
        """Thread-safe update of a causal edge (e.g., from correlation engine)."""
        with self._lock:
            self.graph.add_edge(u, v, weight=weight, lag_minutes=lag_minutes, edge_type=edge_type)
            
    def get_downstream(self, node: str) -> List[str]:
        """Returns immediate downstream dependencies."""
        with self._lock:
            if self.graph.has_node(node):
                return list(self.graph.successors(node))
            return []

    def get_upstream(self, node: str) -> List[str]:
        """Returns immediate upstream dependencies."""
        with self._lock:
            if self.graph.has_node(node):
                return list(self.graph.predecessors(node))
            return []
            
    def export_for_frontend(self) -> Dict[str, Any]:
        """Exports graph in D3.js friendly format."""
        with self._lock:
            nodes = [{"id": n, "group": 1} for n in self.graph.nodes()]
            links = [{"source": u, "target": v, "value": self.graph[u][v]["weight"]} for u, v in self.graph.edges()]
            return {"nodes": nodes, "links": links}
