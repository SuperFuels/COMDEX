# ──────────────────────────────────────────────
#  Tessaris • QuantumMorphicRuntime (HQCE v1.0)
#  Live ψ–κ–T field regulation with SLE → Holographic Core coupling
#  Includes Morphic Ledger + GlyphVault signing + Telemetry broadcast
# ──────────────────────────────────────────────

import os
import json
import uuid
import time
import logging
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.modules.hologram.holographic_renderer import HolographicRenderer
from backend.modules.hologram.holographic_trigger_controller import HolographicTriggerController
from backend.modules.hologram.knowledge_pack_generator import generate_knowledge_pack
from backend.modules.holograms.compile_field_tensor import compile_field_tensor
from backend.modules.holograms.morphic_feedback_controller import MorphicFeedbackController

from backend.modules.glyphos.symbolic_prediction_engine import run_prediction_on_container
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.glyphos.entanglement_fusion import sync_entangled_state
from backend.modules.hologram.symbolic_hsx_bridge import SymbolicHSXBridge
from backend.modules.websocket.ghx_ws_broadcast import broadcast_ghx_runtime_update
from backend.modules.holograms.morphic_ledger import morphic_ledger
from backend.modules.security.glyphvault_signing import glyphvault_signer

logger = logging.getLogger(__name__)


class QuantumMorphicRuntime:
    """
    Holographic Runtime with real-time ψ–κ–T regulation.
    Activated during P5 bridge (SLE → Holographic Core).
    """

    def __init__(self, ghx_packet: Dict[str, Any], avatar_state: Dict[str, Any]):
        self.packet = ghx_packet
        self.avatar = avatar_state
        self.runtime_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat()
        self.metrics = CodexMetrics()
        self.renderer = HolographicRenderer(ghx_packet)
        self.trigger_controller = HolographicTriggerController(ghx_packet, avatar_state)
        self.symbolic_bridge = SymbolicHSXBridge(self.packet, self.avatar)

        # HQCE ψ–κ–T regulation
        self.feedback_controller = MorphicFeedbackController(target_coherence=0.92)
        self.last_field_signature: Optional[Dict[str, float]] = None
        self.last_feedback: Optional[Dict[str, Any]] = None

        # Morphic ledger persistence + vault signing
        self.ledger_path = "data/ledger/morphic_runtime_log.jsonl"
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)

    # ────────────────────────────────────────────
    #  Primary Runtime Loop
    # ────────────────────────────────────────────
    def run(self) -> Dict[str, Any]:
        """
        Full GHX runtime cycle (ψ–κ–T regulated):
        - Collect holographic field state
        - Sync symbolic + entangled glyphs
        - Compile ψ–κ–T from telemetry
        - Run morphic feedback regulation
        - Broadcast + log results
        - Sign ledger record with GlyphVault
        """
        logger.info(f"[QuantumMorphicRuntime] 🧠 HQCE ψ–κ–T loop start: {self.packet.get('container_id')}")

        # 1. Field projection and triggers
        triggered = self.trigger_controller.evaluate_triggers()
        self.renderer.render_glyph_field()

        # 2. Overlay predictions and entanglement sync
        overlay = self._inject_goal_predictions()
        self._sync_entangled_glyphs()
        self._run_symbolic_overlay()

        # 3. Pull telemetry (from SLE or fallback)
        telemetry = self._collect_telemetry_snapshot()
        psi_kappa_T = compile_field_tensor(telemetry)
        self.last_field_signature = psi_kappa_T

        # 4. Feedback control (ψ–κ–T → coherence correction)
        field_nodes = self.renderer.rendered_projection or []
        feedback = self.feedback_controller.regulate(psi_kappa_T, field_nodes)
        self.last_feedback = feedback

        # 5. Assemble runtime state and persist to ledger
        runtime_state = self._assemble_runtime_state(triggered, overlay, feedback)
        self._write_ledger(runtime_state)

        # 6. Sign ledger snapshot via GlyphVault
        signed = glyphvault_signer.sign_payload(self.avatar.get("id", "default_avatar"), runtime_state)
        glyphvault_signer.persist_signed_snapshot(signed, label=f"morphic_{self.runtime_id[:8]}")

        # 7. Broadcast runtime telemetry
        try:
            broadcast_ghx_runtime_update(runtime_state)
        except Exception as e:
            logger.debug(f"GHX WebSocket broadcast failed: {e}")

        logger.info("[QuantumMorphicRuntime] ✅ Runtime tick complete.")
        return runtime_state

    # ────────────────────────────────────────────
    #  Helper Subroutines
    # ────────────────────────────────────────────
    def _inject_goal_predictions(self) -> Optional[Dict[str, Any]]:
        try:
            predictions = run_prediction_on_container(self.packet, context="ghx")
            return predictions
        except Exception as e:
            logger.warning(f"[QuantumMorphicRuntime] Prediction overlay failed: {e}")
            return None

    def _sync_entangled_glyphs(self):
        try:
            sync_entangled_state(self.packet)
        except Exception as e:
            logger.warning(f"[QuantumMorphicRuntime] Entanglement sync failed: {e}")

    def _run_symbolic_overlay(self):
        try:
            self.symbolic_bridge.run()
        except Exception as e:
            logger.warning(f"[QuantumMorphicRuntime] SymbolicHSXBridge failed: {e}")

    # ────────────────────────────────────────────
    #  Telemetry + ψ–κ–T Compilation
    # ────────────────────────────────────────────
    def _collect_telemetry_snapshot(self) -> Dict[str, Any]:
        """
        Pull a single snapshot of live or simulated SLE telemetry.
        Replace this with the actual LightWave feed during QQC runtime.
        """
        try:
            return {
                "nodes": [
                    {"entropy": np.random.uniform(0.05, 0.25), "coherence": np.random.uniform(0.7, 0.95)}
                    for _ in range(8)
                ],
                "links": [{"a": f"n{i}", "b": f"n{(i+1)%8}"} for i in range(8)],
                "tick_time": 1.0,
                "field_decay": np.random.uniform(0.001, 0.01),
            }
        except Exception as e:
            logger.error(f"[QuantumMorphicRuntime] Telemetry collection error: {e}")
            return {}

    # ────────────────────────────────────────────
    #  Ledger + Output Assembly
    # ────────────────────────────────────────────
    def _assemble_runtime_state(
        self,
        triggered: List[Dict[str, Any]],
        overlay: Optional[Dict[str, Any]],
        feedback: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        glyphs = self.renderer.rendered_projection or []
        goal_score = self.metrics.score_glyph_tree(glyphs)

        return {
            "runtime_id": self.runtime_id,
            "timestamp": self.timestamp,
            "container_id": self.packet.get("container_id"),
            "triggered_glyphs": triggered,
            "goal_overlay": overlay,
            "goal_alignment_score": goal_score,
            "psi_kappa_T": self.last_field_signature,
            "feedback": feedback,
            "metrics": {
                "glyph_count": len(glyphs),
                "avg_entropy": self.metrics.entropy_level(glyphs),
                "collapse_rate": (
                    sum(1 for g in glyphs if g.get("collapse_trace")) / len(glyphs)
                    if glyphs else 0
                ),
                "avg_coherence": np.mean([g.get("coherence", 0.5) for g in glyphs]) if glyphs else 0.0,
            },
            "morphic_state": {
                "nodes": glyphs,
                "links": self.renderer.links,
            },
        }

    def _write_ledger(self, record: Dict[str, Any]):
        """Append concise record to Morphic Ledger file and runtime memory."""
        try:
            entry = {
                "timestamp": time.time(),
                "runtime_id": record.get("runtime_id"),
                "psi_kappa_T": record.get("psi_kappa_T"),
                "feedback": record.get("feedback"),
                "avg_entropy": record.get("metrics", {}).get("avg_entropy"),
                "avg_coherence": record.get("metrics", {}).get("avg_coherence"),
            }
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            morphic_ledger.append(entry, observer=self.avatar.get("id", "default_avatar"))
            logger.debug(f"[QuantumMorphicRuntime] Ledger entry appended.")
        except Exception as e:
            logger.warning(f"[QuantumMorphicRuntime] Ledger write failed: {e}")

    # ────────────────────────────────────────────
    #  Export Snapshot for GHX Serialization
    # ────────────────────────────────────────────
    def export_snapshot(self) -> Dict[str, Any]:
        """Generate serializable GHX snapshot for downstream analysis."""
        return generate_knowledge_pack(
            self.renderer.rendered_projection,
            self.packet.get("container_id", "unknown"),
        )