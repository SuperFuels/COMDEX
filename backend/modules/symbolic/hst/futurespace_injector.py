import uuid
import random
from typing import Optional, List, Dict, Any

from backend.modules.symbolic.hst.symbol_tree_generator import SymbolicTreeNode, SymbolicMeaningTree
from backend.modules.consciousness.prediction_engine import PredictionEngine
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.sqi.sqi_utils import compute_entropy_vector
from backend.modules.codex.codex_ast_encoder import CodexAST
from backend.modules.codex.mutation_scorer import estimate_goal_alignment_score

logger = __import__("logging").getLogger(__name__)


class FuturespaceNodeInjector:
    def __init__(self, prediction_engine: Optional[PredictionEngine] = None):
        self.prediction_engine = prediction_engine or PredictionEngine()
        self.kg_writer = KnowledgeGraphWriter()

    def inject_futurespace_nodes(self, tree: SymbolicMeaningTree) -> List[SymbolicTreeNode]:
        futures = []
        for node_id, node in tree.node_index.items():
            if not node.glyph or not isinstance(node.glyph, dict):
                continue

            try:
                # 🧠 Predict symbolic future nodes from current glyph
                prediction = self.prediction_engine.predict_next_symbolic_step(node.glyph)
                if not prediction:
                    continue

                predicted_glyph = prediction.get("glyph")
                prediction_metadata = prediction.get("metadata", {})
                if not predicted_glyph:
                    continue

                # 🔮 Compute entropy and alignment scoring
                entropy_vector = compute_entropy_vector(predicted_glyph)
                goal_score = estimate_goal_alignment_score(predicted_glyph)

                # 🪞 Create future node
                future_node = SymbolicTreeNode(
                    id=f"future-{uuid.uuid4().hex[:8]}",
                    label=prediction.get("label", "FutureNode"),
                    glyph=predicted_glyph,
                    metadata={
                        "type": "futurespace",
                        "source": node.id,
                        "entropy": entropy_vector,
                        "goal_alignment_score": goal_score,
                        **prediction_metadata,
                    }
                )

                tree.add_node(future_node, parent_id=node_id)
                futures.append(future_node)

                # 🧩 Inject to Knowledge Graph for entanglement
                self.kg_writer.write_symbol_node(future_node)

                logger.info(f"[🔮] Injected futurespace node under {node_id}: {future_node.label}")

            except Exception as e:
                logger.warning(f"[⚠️] Failed to inject future node under {node_id}: {e}")

        return futures