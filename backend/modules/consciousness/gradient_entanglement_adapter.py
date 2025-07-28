"""
↔ gradient_entanglement_adapter.py

🔗 Entanglement-Aware Feedback Adapter for IGI Systems  
Propagates QGlyph collapse and symbolic gradient feedback across entangled ancestry.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌌 Entanglement Bias Adapter – Design Rubric
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Pull ↔ ancestry from `symbolic_entangler`
✅ Propagate QGlyph collapse influence to entangled glyphs
✅ Bias Codex confidence weights via entangled feedback
✅ Inject into Knowledge Graph zones (entangled_feedback)
✅ Plug-in style: runs alongside `symbolic_gradient_engine`
"""

from typing import Dict, List
from backend.modules.glyphnet.symbolic_entangler import get_entangled_for
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.codex.codex_metrics import CodexMetrics

class GradientEntanglementAdapter:
    def __init__(self):
        self.kg_writer = KnowledgeGraphWriter()
        self.codex_metrics = CodexMetrics()

    def propagate_from_collapse(self, collapse_result: Dict):
        """
        When a QGlyph collapses, bias entangled glyph weights and update KG.
        """
        qglyph_id = collapse_result.get("selected", {}).get("qbit_id")
        container_id = collapse_result.get("selected", {}).get("container")
        collapsed_value = collapse_result.get("selected", {}).get("collapsed", None)

        if not qglyph_id:
            return

        entangled_nodes = get_entangled_for(qglyph_id)
        if not entangled_nodes:
            return

        for entangled_id in entangled_nodes:
            self.kg_writer.store_predictive_node(
                container_id=container_id,
                zone="entangled_feedback",
                glyph={"id": entangled_id, "linked_from": qglyph_id},
                metadata={
                    "collapse_influence": collapsed_value,
                    "propagated": True
                }
            )

            # Bias Codex metrics confidence weights based on collapse value
            delta = 0.5 if collapsed_value == "1" else -0.5
            self.codex_metrics.record_confidence_event(glyph_id=entangled_id, delta=delta)

    def propagate_gradient_feedback(self, glyph_id: str, reason: str):
        """
        When symbolic feedback occurs (failure/goal drift), extend signal to ↔ entangled glyphs.
        """
        entangled_nodes = get_entangled_for(glyph_id)
        for entangled_id in entangled_nodes:
            self.kg_writer.store_predictive_node(
                container_id="global",
                zone="entangled_gradient",
                glyph={"id": entangled_id, "linked_from": glyph_id},
                metadata={"reason": reason, "propagated": True}
            )
            self.codex_metrics.record_blindspot_event(entangled_id)