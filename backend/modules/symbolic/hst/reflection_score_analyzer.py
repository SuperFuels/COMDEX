import logging
from typing import Optional, Dict, Any

from backend.modules.symbolic.hst.symbol_tree_generator import SymbolicTreeNode, SymbolicMeaningTree
from backend.modules.codex.mutation_scorer import estimate_goal_alignment_score
from backend.modules.consciousness.logic_prediction_utils import detect_contradictions
from backend.modules.sqi.sqi_utils import compute_entropy_vector

logger = logging.getLogger(__name__)


class IntrospectiveReflectionScorer:
    def __init__(self):
        pass

    def score_tree(self, tree: SymbolicMeaningTree) -> Dict[str, Dict[str, Any]]:
        scores = {}

        for node_id, node in tree.node_index.items():
            try:
                # Skip if no glyph
                if not node.glyph or not isinstance(node.glyph, dict):
                    continue

                entropy_vector = compute_entropy_vector(node.glyph)
                goal_score = estimate_goal_alignment_score(node.glyph)
                contradiction_score = self._compute_contradiction_score(node)

                reflective_depth = self._estimate_reflective_depth(tree, node)

                score = {
                    "goal_alignment_score": goal_score,
                    "entropy": entropy_vector,
                    "contradiction_score": contradiction_score,
                    "reflective_depth": reflective_depth,
                    "is_self_referential": self._is_self_reflective(node),
                }

                # Save into node metadata
                node.metadata["introspective_score"] = score
                scores[node_id] = score

                logger.debug(f"[🪞] Node {node_id} scored: {score}")

            except Exception as e:
                logger.warning(f"[⚠️] Failed to score node {node_id}: {e}")

        return scores

    def _estimate_reflective_depth(self, tree: SymbolicMeaningTree, node: SymbolicTreeNode) -> int:
        """Estimate how many child mutations or predictive branches descend from this node."""
        count = 0
        for child in tree.get_children(node.id):
            if child.metadata.get("type") in ("mutation", "futurespace", "contradiction"):
                count += 1
        return count

    def _compute_contradiction_score(self, node: SymbolicTreeNode) -> float:
        try:
            contradictions = detect_contradictions(node.glyph)
            return float(len(contradictions))
        except Exception:
            return 0.0

    def _is_self_reflective(self, node: SymbolicTreeNode) -> bool:
        """Heuristic: check for introspective keywords in label or metadata."""
        label = (node.label or "").lower()
        if "self" in label or "reflect" in label or "introspect" in label:
            return True
        if node.metadata.get("type") == "self":
            return True
        return False