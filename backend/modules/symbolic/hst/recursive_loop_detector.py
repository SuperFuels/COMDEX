import logging
from typing import Dict, List, Set

from backend.modules.symbolic.hst.symbol_tree_generator import SymbolicMeaningTree, SymbolicTreeNode
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter

logger = logging.getLogger(__name__)


class RecursiveLoopDetector:
    def __init__(self):
        self.kg_writer = KnowledgeGraphWriter()

    def detect_loops(self, tree: SymbolicMeaningTree) -> List[List[str]]:
        """
        Detect recursive loops in the symbolic tree. Returns list of cycles as node ID paths.
        """
        visited: Set[str] = set()
        stack: List[str] = []
        loop_paths: List[List[str]] = []

        def dfs(node_id: str, path: List[str]):
            if node_id in path:
                loop_start = path.index(node_id)
                loop = path[loop_start:] + [node_id]
                loop_paths.append(loop)
                return

            visited.add(node_id)
            path.append(node_id)
            node = tree.node_index.get(node_id)

            if node:
                for child in node.children:
                    dfs(child.id, path[:])  # clone path to isolate branches

        for node_id in tree.node_index:
            if node_id not in visited:
                dfs(node_id, [])

        # Annotate loops in metadata
        for loop in loop_paths:
            for nid in loop:
                node = tree.node_index.get(nid)
                if node:
                    node.metadata.setdefault("loop_detected", True)
                    node.metadata.setdefault("loop_ids", []).extend(loop)
                    self.kg_writer.write_symbol_node(node)

        logger.info(f"[♻️] Detected {len(loop_paths)} recursive loop(s).")
        return loop_paths