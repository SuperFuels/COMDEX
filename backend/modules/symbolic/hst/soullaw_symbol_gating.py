import logging
from typing import List, Dict

from backend.modules.symbolic.hst.symbol_tree_generator import SymbolicTreeNode, SymbolicMeaningTree
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.codex.soullaw_checker import evaluate_soullaw_violations

logger = logging.getLogger(__name__)


class SoulLawSymbolGate:
    def __init__(self):
        self.kg_writer = KnowledgeGraphWriter()

    def apply_soullaw_gating(self, tree: SymbolicMeaningTree) -> Dict[str, Dict]:
        """
        Evaluate each node in the symbolic tree for SoulLaw compliance.
        Nodes may be marked as blocked, pending, or safe.
        Returns a map of node_id → gating status and violations.
        """
        gating_report = {}

        for node_id, node in tree.node_index.items():
            if not node.glyph or not isinstance(node.glyph, dict):
                continue

            try:
                result = evaluate_soullaw_violations(node.glyph)

                gating_status = "allowed"
                if result.get("blocked"):
                    gating_status = "blocked"
                elif result.get("requires_review"):
                    gating_status = "pending"

                node.metadata["soullaw_gate"] = {
                    "status": gating_status,
                    "violations": result.get("violations", []),
                }

                gating_report[node_id] = node.metadata["soullaw_gate"]

                # Optional: inject into KG
                self.kg_writer.write_symbol_node(node)

                logger.debug(f"[🔓] Node {node_id} SoulLaw: {gating_status}")

            except Exception as e:
                logger.warning(f"[⚠️] SoulLaw evaluation failed for node {node_id}: {e}")

        logger.info(f"[🔓] Applied SoulLaw gating to {len(gating_report)} nodes.")
        return gating_report