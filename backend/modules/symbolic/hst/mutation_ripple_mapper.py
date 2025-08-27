import logging
from typing import Dict, List, Optional
from backend.modules.symbolic.hst.symbol_tree_generator import SymbolicTreeNode, SymbolicMeaningTree
from backend.modules.codex.codexlang_rewriter import measure_glyph_divergence

logger = logging.getLogger(__name__)


class MutationRippleMapper:
    def __init__(self):
        pass

    def compute_ripple_map(self, tree: SymbolicMeaningTree) -> Dict[str, Dict]:
        """
        Traverse the symbolic tree and compute mutation ripple paths,
        tracking depth and divergence for each mutation node.
        """
        ripple_map = {}

        for node_id, node in tree.node_index.items():
            if node.metadata.get("type") != "mutation":
                continue

            origin_id = node.metadata.get("source") or self._find_origin_ancestor(tree, node_id)
            if not origin_id:
                continue

            try:
                origin_node = tree.node_index.get(origin_id)
                ripple_depth = self._compute_mutation_depth(tree, origin_id, node_id)
                divergence = measure_glyph_divergence(origin_node.glyph, node.glyph)

                ripple_data = {
                    "origin": origin_id,
                    "depth": ripple_depth,
                    "divergence_score": divergence,
                    "lineage": self._build_lineage(tree, node_id),
                }

                node.metadata["mutation_ripple"] = ripple_data
                ripple_map[node_id] = ripple_data

                logger.info(f"[🧬] Ripple mapped: {node_id} ← {origin_id} | depth={ripple_depth}, div={divergence:.3f}")

            except Exception as e:
                logger.warning(f"[⚠️] Failed ripple mapping for {node_id}: {e}")

        return ripple_map

    def _find_origin_ancestor(self, tree: SymbolicMeaningTree, node_id: str) -> Optional[str]:
        """Walk up the tree to find the first non-mutation ancestor."""
        current = tree.node_index.get(node_id)
        while current and current.parent_id:
            parent = tree.node_index.get(current.parent_id)
            if not parent:
                break
            if parent.metadata.get("type") != "mutation":
                return parent.id
            current = parent
        return None

    def _compute_mutation_depth(self, tree: SymbolicMeaningTree, origin_id: str, node_id: str) -> int:
        """Count the number of mutation hops from origin to node."""
        depth = 0
        current = tree.node_index.get(node_id)
        while current and current.id != origin_id:
            parent = tree.node_index.get(current.parent_id)
            if not parent or parent.id == current.id:
                break
            depth += 1
            current = parent
        return depth

    def _build_lineage(self, tree: SymbolicMeaningTree, node_id: str) -> List[str]:
        """Build mutation lineage chain from origin to this node."""
        lineage = []
        current = tree.node_index.get(node_id)
        while current:
            lineage.append(current.id)
            parent = tree.node_index.get(current.parent_id)
            if not parent or parent.id == current.id:
                break
            current = parent
        lineage.reverse()
        return lineage