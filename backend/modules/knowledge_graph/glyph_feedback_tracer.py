"""
📡 glyph_feedback_tracer.py

🧬 Glyph Feedback Tracer for Knowledge Graph Learning
Maps glyph ancestry, traces causal paths, and injects symbolic gradient zones for failures & reinforcements.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔮 Glyph Feedback Tracer – Design Rubric
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Ancestry Reconstruction via Entanglement & Memory (↔ 🧠)
✅ Failure Gradient Zone Injection (❌ ➔ KG)
✅ Ethical Feedback Filtering (⚖️ SoulLaw Integration)
✅ Confidence Drop Estimation & Blindspot Recording
✅ Reinforcement Tracking for Successful Glyph Paths (🏆)
✅ Fully Integrated with Codex Metrics + KG Writer
✅ MemoryBridge Lineage Sync & Predictive Drift Ready
"""

from typing import List, Optional, Dict, Any
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.glyphnet.symbolic_entangler import get_entangled_ancestors
from backend.modules.codex.soul_law_validator import filter_unethical_feedback
from backend.modules.runtime.memory_bridge import MemoryBridge

class GlyphFeedbackTracer:
    def __init__(self):
        self.writer = KnowledgeGraphWriter()
        self.metrics = CodexMetrics()
        self.memory = MemoryBridge()

    def trace_feedback_path(self, glyph_id: str, event: Dict[str, Any], cause: str):
        """
        Trace the ancestry of a failed glyph to annotate the gradient zone.
        """
        ancestry = self.identify_causal_glyphs(glyph_id)
        if not ancestry:
            self.annotate_gradient_zone([], glyph_id, cause, fallback=True)
            return

        filtered = filter_unethical_feedback(ancestry)
        self.annotate_gradient_zone(filtered, glyph_id, cause)

    def identify_causal_glyphs(self, glyph_id: str) -> List[str]:
        """
        Uses memory logs and entanglement to reconstruct symbolic ancestry.
        """
        entangled = get_entangled_ancestors(glyph_id)
        memory_lineage = self.memory.get_lineage_trace(glyph_id)
        ancestry = list(set(entangled + memory_lineage))
        return ancestry

    def annotate_gradient_zone(
        self, glyph_ids: List[str], failed_glyph: str, cause: str, fallback: bool = False
    ):
        """
        Injects failure metadata into the knowledge graph for learning.
        """
        if fallback:
            zone = {
                "type": "gradient_zone",
                "target": failed_glyph,
                "status": "mirror_failure",
                "cause": cause,
                "comment": "No causal path could be traced.",
            }
            self.writer.inject_feedback_zone(zone)
            self.metrics.record_blindspot_event(failed_glyph, cause)
            return

        zone = {
            "type": "gradient_zone",
            "target": failed_glyph,
            "status": "failure_gradient",
            "cause": cause,
            "path": glyph_ids,
            "confidence_drop": self.metrics.estimate_confidence_delta(glyph_ids),
        }

        self.writer.inject_feedback_zone(zone)
        self.metrics.record_confidence_event(failed_glyph, delta=zone["confidence_drop"])

    def trace_success_path(self, glyph_id: str, tag: str = "success_gradient"):
        """
        Optionally record successful glyphs for reinforcement tracking.
        """
        ancestry = self.identify_causal_glyphs(glyph_id)
        if ancestry:
            zone = {
                "type": "gradient_zone",
                "target": glyph_id,
                "status": tag,
                "path": ancestry,
                "reinforcement": True,
            }
            self.writer.inject_feedback_zone(zone)
            self.metrics.record_success_event(glyph_id)