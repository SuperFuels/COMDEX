# ──────────────────────────────────────────────
#  Tessaris * QuantumMorphicRuntime (HQCE v1.1)
#  Live ψ-κ-T field regulation with SLE -> Holographic Core coupling
#  Includes Morphic Ledger + GlyphVault signing + Telemetry broadcast
#  (Extended: Field History Buffer, Semantic Gravity Streaming)
# ──────────────────────────────────────────────

import os
import json
import uuid
import time
import logging
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.modules.holograms.holographic_renderer import HolographicRenderer
from backend.modules.holograms.holographic_trigger_controller import HolographicTriggerController
from backend.modules.holograms.knowledge_pack_generator import generate_knowledge_pack
from backend.modules.holograms.compile_field_tensor import compile_field_tensor
from backend.modules.holograms.morphic_feedback_controller import MorphicFeedbackController

from backend.modules.glyphos.symbolic_prediction_engine import run_prediction_on_container
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.glyphos.entanglement_fusion import sync_entangled_state
from backend.modules.holograms.symbolic_hsx_bridge import SymbolicHSXBridge
from backend.modules.websocket.ghx_ws_broadcast import broadcast_ghx_runtime_update
from backend.modules.holograms.morphic_ledger import morphic_ledger
from backend.modules.security.glyphvault_signing import glyphvault_signer
from backend.modules.holograms.ghx_visual_bridge import GHXVisualBridge
from backend.modules.fabric.fabric_ontology import FabricOntology

# ✅ HUD event interface
try:
    from backend.modules.codex.codex_websocket_interface import send_codex_ws_event
except Exception:
    def send_codex_ws_event(event_type: str, payload: dict):
        print(f"[Fallback HUD] {event_type} -> {json.dumps(payload)}")

logger = logging.getLogger(__name__)


class QuantumMorphicRuntime:
    """
    Holographic Runtime with real-time ψ-κ-T regulation.
    Activated during P5 bridge (SLE -> Holographic Core).
    """

    def __init__(self, ghx_packet: Dict[str, Any], avatar_state: Dict[str, Any]):
        """Initialize morphic runtime (stub mode)."""
        print("[QuantumMorphicRuntime] initialized (stub mode).")
        return True
        self.packet = ghx_packet
        self.avatar = avatar_state
        self.runtime_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat()
        self.metrics = CodexMetrics()

        self.renderer = HolographicRenderer(ghx_packet, observer_id=avatar_state.get("id", "anon"))
        self.trigger_controller = HolographicTriggerController(ghx_packet, avatar_state)
        self.symbolic_bridge = SymbolicHSXBridge(avatar_state.get("id", "anon"), ghx_packet)

        # HQCE ψ-κ-T regulation
        self.feedback_controller = MorphicFeedbackController(target_coherence=0.92)
        self.last_field_signature: Optional[Dict[str, float]] = None
        self.last_feedback: Optional[Dict[str, Any]] = None

        # 🧠 Field history for learning (Stage 6)
        self.field_history_buffer: List[Dict[str, Any]] = []
        self.max_history = 64
        self.fabric = FabricOntology()

        # Morphic ledger persistence + vault signing
        self.ledger_path = "data/ledger/morphic_runtime_log.jsonl"
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)

        # ────────────────────────────────────────────
        #  GHX Visual Bridge (Stage 13 Live Stream)
        # ────────────────────────────────────────────
        try:
            self.ghx_bridge = GHXVisualBridge(ledger=morphic_ledger)
            logger.info("[QuantumMorphicRuntime] GHXVisualBridge initialized for live ψκT streaming.")
        except Exception as e:
            self.ghx_bridge = None
            logger.warning(f"[QuantumMorphicRuntime] Could not initialize GHXVisualBridge: {e}")

    # ────────────────────────────────────────────
    #  Primary Runtime Loop
    # ────────────────────────────────────────────
    def run(self) -> Dict[str, Any]:
        """
        Full GHX runtime cycle (ψ-κ-T regulated):
        - Collect holographic field state
        - Sync symbolic + entangled glyphs
        - Compile ψ-κ-T from telemetry
        - Run morphic feedback regulation
        - Broadcast + log results
        - Sign ledger record with GlyphVault
        """
        cid = self.packet.get("container_id")
        logger.info(f"[QuantumMorphicRuntime] 🧠 HQCE ψ-κ-T loop start: {cid}")

        # 🔴 Start live GHX WebSocket streaming (background async)
        if self.ghx_bridge:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    loop.create_task(self.ghx_bridge.live_loop(interval=1.5))
                else:
                    asyncio.ensure_future(self.ghx_bridge.live_loop(interval=1.5))
                logger.info("[QuantumMorphicRuntime] GHXVisualBridge live stream loop started.")
            except Exception as e:
                logger.warning(f"[QuantumMorphicRuntime] Failed to launch GHX live loop: {e}")

        # 1️⃣ Field projection + triggers
        triggered = self.trigger_controller.evaluate_triggers()
        self.renderer.render_glyph_field()

        # 2️⃣ Overlay predictions + entanglement sync
        overlay = self._inject_goal_predictions()
        self._sync_entangled_glyphs()
        self._run_symbolic_overlay()

        # 3️⃣ Pull telemetry + compile ψκT
        telemetry = self._collect_telemetry_snapshot()
        psi_kappa_T = compile_field_tensor(telemetry)
        self.last_field_signature = psi_kappa_T
        self._update_field_history(psi_kappa_T)

        # 4️⃣ Feedback control
        field_nodes = self.renderer.rendered_projection or []
        feedback = self.feedback_controller.regulate(psi_kappa_T, field_nodes)
        self.last_feedback = feedback
        # 🧭 Apply adaptive feedback regulation to runtime parameters
        try:
            if feedback:
                # Dynamically adjust renderer lazy mode
                if "lazy_mode" in feedback:
                    self.renderer.lazy_mode = feedback["lazy_mode"]

                # Adjust entanglement update rate if provided
                if "rate_scale" in feedback:
                    scale = feedback.get("rate_scale", 1.0)
                    self.feedback_controller.rate_scale = scale
                    self.trigger_controller.update_rate = getattr(self.trigger_controller, "update_rate", 1.0) * scale

                # Update MorphicFeedbackController's target if coherence feedback present
                if "target_coherence" in feedback:
                    self.feedback_controller.target_coherence = feedback["target_coherence"]

                logger.debug(f"[QuantumMorphicRuntime] Adaptive feedback applied: {feedback}")
        except Exception as e:
            logger.warning(f"[QuantumMorphicRuntime] Feedback application failed: {e}")

        # 5️⃣ Assemble runtime state and persist
        runtime_state = self._assemble_runtime_state(triggered, overlay, feedback)
        self._write_ledger(runtime_state)

        # 6️⃣ GlyphVault sign snapshot
        try:
            signed = glyphvault_signer.sign_payload(self.avatar.get("id", "default_avatar"), runtime_state)
            glyphvault_signer.persist_signed_snapshot(signed, label=f"morphic_{self.runtime_id[:8]}")
        except Exception as e:
            logger.warning(f"[QuantumMorphicRuntime] GlyphVault signing failed: {e}")

        # 7️⃣ Broadcast runtime telemetry (WS + overlay)
        self._broadcast_runtime(runtime_state)

        logger.info("[QuantumMorphicRuntime] ✅ Runtime tick complete.")
        return runtime_state

    # ────────────────────────────────────────────
    #  Helper Subroutines
    # ────────────────────────────────────────────
    def _inject_goal_predictions(self) -> Optional[Dict[str, Any]]:
        try:
            return run_prediction_on_container(self.packet, context="ghx")
        except Exception as e:
            logger.warning(f"[QuantumMorphicRuntime] Prediction overlay failed: {e}")
            return None

    def _sync_entangled_glyphs(self):
        try:
            sync_entangled_state(self.packet)
        except Exception as e:
            logger.warning(f"[QuantumMorphicRuntime] Entanglement sync failed: {e}")

    def _run_symbolic_overlay(self):
        """Score overlay + compute semantic gravity + propagate ψκT into Fabric Ontology."""
        try:
            # Step 1 - Identity and scoring
            self.symbolic_bridge.inject_identity_trails()
            self.symbolic_bridge.score_overlay_paths()
            self.symbolic_bridge.broadcast_overlay()

            # Step 2 - 🌐 Forward latest semantic gravity map to GHX visual bridge
            try:
                gravity_map = self.symbolic_bridge.compute_semantic_gravity()
                if self.ghx_bridge:
                    self.ghx_bridge.ingest_semantic_gravity(gravity_map)
                    logger.debug("[QuantumMorphicRuntime] Semantic gravity ingested into GHX bridge.")
            except Exception as e:
                logger.warning(f"[QuantumMorphicRuntime] Failed to sync semantic gravity: {e}")

            # Step 3 - 🧩 Propagate ψ-κ-T deltas into Fabric Ontology
            try:
                if self.last_field_signature:
                    ψΔ = self.last_field_signature.get("psi", 0.0)
                    κΔ = self.last_field_signature.get("kappa", 0.0)
                    coherence = self.last_field_signature.get("coherence", 0.9)
                    self.fabric.propagate_resonance(ψΔ, κΔ, coherence)
                    logger.debug("[QuantumMorphicRuntime] ψ-κ-T deltas propagated into Fabric Ontology.")
            except Exception as e:
                logger.warning(f"[QuantumMorphicRuntime] FabricOntology propagation failed: {e}")

        except Exception as e:
            logger.warning(f"[QuantumMorphicRuntime] SymbolicHSXBridge failed: {e}")

    # ────────────────────────────────────────────
    #  Telemetry + ψ-κ-T Compilation
    # ────────────────────────────────────────────
    def _collect_telemetry_snapshot(self) -> Dict[str, Any]:
        """
        Pull a single snapshot of live or simulated SLE telemetry.
        Replace with LightWave feed during QQC runtime.
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

    def _update_field_history(self, ψκT: Dict[str, Any]):
        """Append current ψ-κ-T field snapshot to rolling buffer and persist to Morphic Ledger."""
        try:
            snapshot = {
                "timestamp": datetime.utcnow().isoformat(),
                "ψ": ψκT.get("psi", 0.0),
                "κ": ψκT.get("kappa", 0.0),
                "T": ψκT.get("T", 0.0),
                "coherence": ψκT.get("coherence", 0.0),
            }

            # Append to rolling field history buffer
            self.field_history_buffer.append(snapshot)
            if len(self.field_history_buffer) > self.max_history:
                self.field_history_buffer.pop(0)

            # 🧩 Auto-commit ψ-κ-T snapshot to Morphic Ledger for learning continuity
            if snapshot:
                morphic_ledger.append(snapshot, observer=self.avatar.get("id", "default_avatar"))
                logger.debug("[QuantumMorphicRuntime] ψ-κ-T snapshot committed to Morphic Ledger.")

        except Exception as e:
            logger.warning(f"[QuantumMorphicRuntime] Field history update failed: {e}")

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
                "field_history": self.field_history_buffer[-8:],
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
            logger.debug("[QuantumMorphicRuntime] Ledger entry appended.")
        except Exception as e:
            logger.warning(f"[QuantumMorphicRuntime] Ledger write failed: {e}")

    # ────────────────────────────────────────────
    #  Live Broadcast
    # ────────────────────────────────────────────
    def _broadcast_runtime(self, runtime_state: Dict[str, Any]):
        """Push live coherence + gravity overlays."""
        try:
            # ψ-κ-T live state
            broadcast_ghx_runtime_update(runtime_state)

            # HUD event
            send_codex_ws_event("coherence_update", {
                "Φ_coherence": runtime_state["metrics"]["avg_coherence"],
                "ψκT": self.last_field_signature,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.debug(f"[QuantumMorphicRuntime] Broadcast failed: {e}")

    # ────────────────────────────────────────────
    #  Export Snapshot for GHX Serialization
    # ────────────────────────────────────────────
    def export_snapshot(self) -> Dict[str, Any]:
        """Generate serializable GHX snapshot for downstream analysis."""
        return generate_knowledge_pack(
            self.renderer.rendered_projection,
            self.packet.get("container_id", "unknown"),
        )

    def propagate(signal=None):
        """Simulate morphic field propagation event."""
        print(f"[QuantumMorphicRuntime] Propagate called with: {signal}")
        return {"status": "ok", "signal": signal or "∅"}