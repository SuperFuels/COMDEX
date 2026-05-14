import uuid
import random
import logging
from typing import List, Dict, Optional

from backend.modules.symbolic.hst.symbol_tree_generator import SymbolicMeaningTree, SymbolicTreeNode
from backend.modules.codex.mutation_scorer import estimate_goal_alignment_score
from backend.modules.consciousness.prediction_engine import PredictionEngine
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter

logger = logging.getLogger(__name__)


class MultiverseForkEngine:
    def __init__(self, prediction_engine: Optional[PredictionEngine] = None):
        self.prediction_engine = prediction_engine or PredictionEngine()
        self.kg_writer = KnowledgeGraphWriter()

    def fork_node_multiverse(self, tree: SymbolicMeaningTree, node_id: str, forks: int = 3) -> List[SymbolicTreeNode]:
        """
        Creates N alternate symbolic forks from the specified node.
        """
        if node_id not in tree.node_index:
            logger.warning(f"[⚠️] Node {node_id} not found for forking.")
            return []

        base_node = tree.node_index[node_id]
        if not base_node.glyph:
            logger.warning(f"[⚠️] Node {node_id} has no glyph data.")
            return []

        forked_nodes = []

        for _ in range(forks):
            try:
                # 🧠 Predict alternate symbolic path
                prediction = self.prediction_engine.predict_next_symbolic_step(base_node.glyph, variation=True)
                if not prediction or "glyph" not in prediction:
                    continue

                alt_glyph = prediction["glyph"]
                alt_label = prediction.get("label", "ForkedNode")
                goal_score = estimate_goal_alignment_score(alt_glyph)

                fork_node = SymbolicTreeNode(
                    id=f"fork-{uuid.uuid4().hex[:8]}",
                    label=alt_label,
                    glyph=alt_glyph,
                    metadata={
                        "type": "fork",
                        "source": node_id,
                        "goal_alignment_score": goal_score,
                        "multiverse_label": prediction.get("multiverse_label", f"Alt-{random.randint(1000,9999)}")
                    }
                )

                # Add fork to the tree
                tree.add_node(fork_node, parent_id=node_id)
                forked_nodes.append(fork_node)

                # Inject to KG
                self.kg_writer.write_symbol_node(fork_node)

                logger.info(f"[🌀] Forked node under {node_id}: {fork_node.label} (score: {goal_score:.2f})")

            except Exception as e:
                logger.error(f"[❌] Error during fork creation: {e}")

        return forked_nodes