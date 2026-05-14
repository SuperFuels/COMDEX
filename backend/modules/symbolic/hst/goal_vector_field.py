import uuid
import logging
from typing import List, Dict, Optional

from backend.modules.symbolic.hst.symbol_tree_generator import SymbolicMeaningTree, SymbolicTreeNode
from backend.modules.codex.mutation_scorer import estimate_goal_alignment_score, compute_goal_vector
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter

logger = logging.getLogger(__name__)


class GoalVectorFieldEngine:
    def __init__(self, goal_vector: Optional[List[float]] = None):
        # You can inject a goal vector externally or compute from active goals
        self.goal_vector = goal_vector
        self.kg_writer = KnowledgeGraphWriter()

    def inject_vector_field(self, tree: SymbolicMeaningTree) -> Dict[str, Dict[str, float]]:
        """
        Injects a vector field into the symbolic tree by computing alignment pressure
        between each node's glyph and the global goal vector.
        Returns a mapping of node_id to pressure data.
        """
        if not self.goal_vector:
            logger.warning("[⚠️] No goal vector provided; computing default vector.")
            self.goal_vector = compute_goal_vector()  # Pull from active goal embeddings

        pressure_map = {}

        for node_id, node in tree.node_index.items():
            if not node.glyph or not isinstance(node.glyph, dict):
                continue

            try:
                alignment_score = estimate_goal_alignment_score(node.glyph, goal_vector=self.goal_vector)

                node.metadata["goal_pressure"] = {
                    "alignment_score": alignment_score,
                    "direction_vector": self.goal_vector,
                }

                pressure_map[node_id] = {
                    "alignment_score": alignment_score,
                }

                # Optional: inject goal pressure to Knowledge Graph
                self.kg_writer.write_symbol_node(node)

                logger.debug(f"[🧭] Node {node_id} goal pressure: {alignment_score:.4f}")

            except Exception as e:
                logger.warning(f"[⚠️] Failed to compute pressure for node {node_id}: {e}")

        logger.info(f"[🧭] Injected goal vector pressure into {len(pressure_map)} nodes.")
        return pressure_map