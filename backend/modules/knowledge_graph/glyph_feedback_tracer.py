"""
📡 glyph_feedback_tracer.py

🧬 Glyph Feedback Tracer for Knowledge Graph Learning
Maps glyph ancestry, traces causal paths, and injects symbolic gradient zones for failures & reinforcements.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔮 Glyph Feedback Tracer - Design Rubric
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Ancestry Reconstruction via Entanglement & Memory (↔ 🧠)
✅ Failure Gradient Zone Injection (❌ ➔ KG)
✅ Ethical Feedback Filtering (⚖️ SoulLaw Integration)
✅ Confidence Drop Estimation & Blindspot Recording
✅ Reinforcement Tracking for Successful Glyph Paths (🏆)
✅ Fully Integrated with Codex Metrics + KG Writer
✅ MemoryBridge Lineage Sync & Predictive Drift Ready
"""

import logging
from typing import List, Optional, Dict, Any
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.glyphos.symbolic_entangler import get_entangled_for, get_entangled_targets
from backend.modules.glyphvault.soul_law_validator import filter_unethical_feedback
from backend.modules.consciousness.memory_bridge import MemoryBridge

logger = logging.getLogger(__name__)


class GlyphFeedbackTracer:
    def __init__(self, container_id: str = "default-feedback"):
        """
        Initialize Glyph Feedback Tracer bound to a container context.
        Args:
            container_id (str): Contextual container ID for MemoryBridge lineage tracking.
        """
        self.container_id = container_id
        self.writer = get_kg_writer()
        self.metrics = CodexMetrics()
        self.memory = MemoryBridge(container_id=self.container_id)  # ✅ FIXED: Pass container_id explicitly

    # ──────────────────────────────────────────────
    # ❌ FAILURE TRACE + GRADIENT INJECTION
    # ──────────────────────────────────────────────
    def trace_feedback_path(self, glyph_id: str, event: Dict[str, Any], cause: str):
        """
        Trace the ancestry of a failed glyph to annotate the gradient zone.
        Applies SoulLaw filtering and injects symbolic gradient learning.
        """
        logger.debug(f"[GlyphFeedbackTracer] Tracing failure for glyph {glyph_id} (Cause: {cause}) in {self.container_id}")

        ancestry = self.identify_causal_glyphs(glyph_id)
        if not ancestry:
            self.annotate_gradient_zone([], glyph_id, cause, fallback=True)
            return

        filtered = filter_unethical_feedback({"ancestry": ancestry})  # ✅ Wrap for compliance
        ancestry_filtered = filtered.get("ancestry", ancestry)
        self.annotate_gradient_zone(ancestry_filtered, glyph_id, cause)

    def identify_causal_glyphs(self, glyph_id: str) -> List[str]:
        """
        Uses entanglement graph (↔) and MemoryBridge lineage to reconstruct symbolic ancestry.
        """
        entangled = get_entangled_targets(glyph_id)
        memory_lineage = self.memory.get_lineage_trace(glyph_id)
        ancestry = list(set(entangled + memory_lineage))
        logger.debug(f"[GlyphFeedbackTracer] Ancestry for {glyph_id}: {ancestry}")
        return ancestry

    def annotate_gradient_zone(
        self, glyph_ids: List[str], failed_glyph: str, cause: str, fallback: bool = False
    ):
        """
        Injects failure gradient metadata into Knowledge Graph.
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
            logger.warning(f"[GlyphFeedbackTracer] Mirror failure recorded for {failed_glyph}")
            return

        confidence_drop = self.metrics.estimate_confidence_delta(glyph_ids)
        zone = {
            "type": "gradient_zone",
            "target": failed_glyph,
            "status": "failure_gradient",
            "cause": cause,
            "path": glyph_ids,
            "confidence_drop": confidence_drop,
        }

        self.writer.inject_feedback_zone(zone)
        self.metrics.record_confidence_event(failed_glyph, delta=confidence_drop)
        logger.info(f"[GlyphFeedbackTracer] Failure gradient injected for {failed_glyph} (Δ={confidence_drop:.3f})")

    # ──────────────────────────────────────────────
    # 🏆 SUCCESS TRACE (REINFORCEMENT)
    # ──────────────────────────────────────────────
    def trace_success_path(self, glyph_id: str, tag: str = "success_gradient"):
        """
        Record successful glyph ancestry for reinforcement tracking.
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
            logger.info(f"[GlyphFeedbackTracer] Reinforcement zone injected for {glyph_id}")