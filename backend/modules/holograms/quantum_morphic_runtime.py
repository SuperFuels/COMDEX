import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.modules.hologram.holographic_renderer import HolographicRenderer
from backend.modules.hologram.holographic_trigger_controller import HolographicTriggerController
from backend.modules.hologram.knowledge_pack_generator import generate_knowledge_pack
from backend.modules.glyphos.symbolic_prediction_engine import run_prediction_on_container
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.glyphos.entanglement_fusion import sync_entangled_state
from backend.modules.websocket.ghx_ws_broadcast import broadcast_ghx_runtime_update  # (optional future hook)
from backend.modules.hologram.symbolic_hsx_bridge import SymbolicHSXBridge

logger = logging.getLogger(__name__)


class QuantumMorphicRuntime:
    def __init__(self, ghx_packet: Dict[str, Any], avatar_state: Dict[str, Any]):
        self.packet = ghx_packet
        self.avatar = avatar_state
        self.runtime_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat()
        self.metrics = CodexMetrics()
        self.renderer = HolographicRenderer(ghx_packet)
        self.trigger_controller = HolographicTriggerController(ghx_packet, avatar_state)
        self.active_overlay: Optional[Dict] = None
        self.symbolic_bridge = SymbolicHSXBridge(self.packet, self.avatar)

    def run(self) -> Dict:
        """
        Full GHX runtime cycle:
        - Render hologram field
        - Trigger projection based on avatar state
        - Inject goal/prediction overlays
        - Sync entangled states
        - Trace symbolic overlays
        - Return enriched runtime state
        """
        logger.info(f"[QuantumMorphicRuntime] Starting runtime cycle for {self.packet.get('container_id')}")
        triggered = self.trigger_controller.evaluate_triggers()
        overlay = self._inject_goal_predictions()
        self._sync_entangled_glyphs()
        self._run_symbolic_overlay()
        runtime_state = self._assemble_runtime_state(triggered, overlay)

        try:
            broadcast_ghx_runtime_update(runtime_state)
        except Exception as e:
            logger.debug(f"GHX WebSocket broadcast failed (safe to ignore in local mode): {e}")

        return runtime_state

    def _inject_goal_predictions(self) -> Optional[Dict]:
        """
        Inject predictive glyph overlays into the GHX projection based on active goals.
        """
        try:
            predictions = run_prediction_on_container(self.packet)
            self.active_overlay = predictions
            return predictions
        except Exception as e:
            logger.warning(f"[QuantumMorphicRuntime] Prediction overlay failed: {e}")
            return None

    def _sync_entangled_glyphs(self):
        """
        Update glyph entanglement state in-place (fusion logic).
        """
        try:
            sync_entangled_state(self.packet)
        except Exception as e:
            logger.warning(f"[QuantumMorphicRuntime] Entanglement sync failed: {e}")

    def _run_symbolic_overlay(self):
        """
        Run symbolic HSX bridge for trails, alignment, and entropy overlays.
        """
        try:
            self.symbolic_bridge.run()
        except Exception as e:
            logger.warning(f"[QuantumMorphicRuntime] SymbolicHSXBridge failed: {e}")

    def _assemble_runtime_state(self, triggered: List[Dict], overlay: Optional[Dict]) -> Dict:
        """
        Compose final runtime projection, including:
        - Trigger log
        - Predictions
        - Goal alignment score
        - Codex metrics
        """
        glyphs = self.renderer.rendered_projection
        goal_score = self.metrics.score_glyph_tree(glyphs)

        return {
            "runtime_id": self.runtime_id,
            "timestamp": self.timestamp,
            "container_id": self.packet.get("container_id"),
            "triggered_glyphs": triggered,
            "goal_overlay": overlay,
            "goal_alignment_score": goal_score,
            "metrics": {
                "glyph_count": len(glyphs),
                "avg_entropy": self.metrics.entropy_level(glyphs),
                "collapse_rate": sum(1 for g in glyphs if g.get("collapse_trace")) / len(glyphs)
            },
            "morphic_state": {
                "nodes": glyphs,
                "links": self.renderer.links
            }
        }

    def export_snapshot(self) -> Dict:
        """
        Return the current state as a full GHX snapshot pack.
        """
        return generate_knowledge_pack(
            self.renderer.rendered_projection,
            self.packet.get("container_id", "unknown")
        )