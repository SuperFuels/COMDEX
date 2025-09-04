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
        Evaluate each node in the symbolic tree for SoulLaw compliance,
        including coherence-based gating from carrier metadata.

        Returns a map of node_id → gating status and violations.
        """
        gating_report = {}

        for node_id, node in tree.node_index.items():
            if not node.glyph or not isinstance(node.glyph, dict):
                continue

            try:
                glyph = node.glyph
                result = evaluate_soullaw_violations(glyph)

                gating_status = "allowed"
                if result.get("blocked"):
                    gating_status = "blocked"
                elif result.get("requires_review"):
                    gating_status = "pending"

                # 🔍 Check carrier coherence if available
                coherence = glyph.get("coherence", None)
                carrier_type = glyph.get("carrier_type", "SIMULATED")

                carrier_gate = "pass"
                if coherence is not None and coherence < 0.5:
                    # 🛑 Default to blocked for low coherence
                    gating_status = "blocked"
                    carrier_gate = "fail"

                    # 🧬 H10: Allow override for trusted long-range quantum/optical links
                    if carrier_type in ["QUANTUM", "OPTICAL"] and glyph.get("override_soullaw", False):
                        gating_status = "allowed"
                        carrier_gate = "override"
                        logger.info(
                            f"[SoulLaw] 🛡️ Override accepted for {carrier_type} link (node {node_id}) with low coherence ({coherence:.2f})"
                        )
                    else:
                        result.setdefault("violations", []).append(
                            f"Low coherence transmission via {carrier_type} ({coherence:.2f})"
                        )
                        logger.warning(
                            f"[SoulLaw] 🧨 Coherence violation: Node {node_id} "
                            f"coherence={coherence:.2f}, carrier={carrier_type}"
                        )

                node.metadata["soullaw_gate"] = {
                    "status": gating_status,
                    "violations": result.get("violations", []),
                    "carrier_gate": carrier_gate,
                }

                gating_report[node_id] = node.metadata["soullaw_gate"]

                # 🧠 Inject into KG
                self.kg_writer.write_symbol_node(node)

                logger.debug(f"[🔓] Node {node_id} SoulLaw: {gating_status}")

                if gating_status == "blocked":
                    logger.warning(
                        f"[SoulLaw] 🚫 Blocked collapse: Node {node_id} — Violations: {result['violations']}"
                    )

            except Exception as e:
                logger.warning(f"[⚠️] SoulLaw evaluation failed for node {node_id}: {e}")

        logger.info(f"[🔓] Applied SoulLaw gating to {len(gating_report)} nodes.")
        return gating_report

    def has_violations(self, gating_report: Dict[str, Dict]) -> bool:
        """
        Checks if any node in the gating report has a blocked status.
        Useful to intercept measurement or collapse calls.
        """
        return any(r.get("status") == "blocked" for r in gating_report.values())