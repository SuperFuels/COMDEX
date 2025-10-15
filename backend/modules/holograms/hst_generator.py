# ──────────────────────────────────────────────
#  Tessaris • HST Generator (P5 Field Constructor)
#  Builds in-memory HST tensor graphs from LightWave beam injections
#  Integrates with VisualizationBridge + WebSocketStreamer
# ──────────────────────────────────────────────

import uuid
import time
import json
import numpy as np
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from backend.modules.holograms.morphic_feedback_controller import MorphicFeedbackController
from backend.modules.holograms.hst_visualization_bridge import HSTVisualizationBridge
from backend.modules.symbolic.hst.hst_websocket_streamer import broadcast_replay_paths as broadcast_replay_paths_hst

logger = logging.getLogger(__name__)


class HSTGenerator:
    """
    The Holographic Spatial Tensor (HST) generator.
    Maintains the live holographic node graph (ψ–κ–T field) and
    synchronizes it with the HST visualization + websocket layers.
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.links: List[Dict[str, Any]] = []
        self.field_tensor: Optional[Dict[str, float]] = None
        self.hst_bridge = HSTVisualizationBridge()
        self.container_id = self.session_id

        self.last_update_time = 0.0
        self.update_interval = 0.5  # seconds
        self.active = True

        logger.info(f"[HSTGenerator] Initialized session {self.session_id}")

    # ──────────────────────────────────────────────
    #  Node & Beam Management
    # ──────────────────────────────────────────────
    def inject_lightwave_beam(self, beam_packet: Dict[str, Any]):
        """
        Accept a LightWave beam collapse and register it as an HST node.
        Converts list-based node structures back into a dict to ensure
        stable ID-based access during injection.
        """
        try:
            # ✅ Ensure nodes are stored as a dict (fix for post-feedback conversion)
            if isinstance(self.nodes, list):
                self.nodes = {n.get("id", str(uuid.uuid4())): n for n in self.nodes}

            node_id = beam_packet.get("beam_id", str(uuid.uuid4()))

            if node_id in self.nodes:
                # Update existing node coherence and entropy
                self._update_node(node_id, beam_packet)
            else:
                node = self._create_node_from_beam(beam_packet)
                self.nodes[node_id] = node

            # Update the ψ–κ–T field tensor after beam injection
            self._update_field_tensor()
            logger.debug(f"[HSTGenerator] Beam injected → {node_id}")

        except Exception as e:
            logger.error(f"[HSTGenerator] Beam injection failed: {e}")

    def _create_node_from_beam(self, beam: Dict[str, Any]) -> Dict[str, Any]:
        coherence = float(beam.get("coherence", 1.0))
        entropy = float(beam.get("entropy", 0.0))
        drift = float(beam.get("drift", 0.0))
        goal_match = float(beam.get("goal_match", 1.0 - entropy))

        return {
            "node_id": beam.get("beam_id", str(uuid.uuid4())),
            "symbol": beam.get("symbol", "💡"),
            "entropy": entropy,
            "coherence": coherence,
            "drift": drift,
            "goal_match": goal_match,
            "injected_at": datetime.utcnow().isoformat(),
            "semantic_overlay": {
                "entropy": entropy,
                "goal_match": goal_match,
                "drift": drift
            },
            "color": self._color_from_coherence(coherence)
        }

    def _update_node(self, node_id: str, beam_packet: Dict[str, Any]):
        """
        Merge updated coherence/entropy into an existing node.
        """
        node = self.nodes[node_id]
        node["entropy"] = 0.5 * (node["entropy"] + beam_packet.get("entropy", 0.0))
        node["coherence"] = 0.5 * (node["coherence"] + beam_packet.get("coherence", 1.0))
        node["goal_match"] = 0.5 * (node["goal_match"] + beam_packet.get("goal_match", 1.0))
        node["drift"] = 0.5 * (node["drift"] + beam_packet.get("drift", 0.0))
        node["color"] = self._color_from_coherence(node["coherence"])
        node["updated_at"] = datetime.utcnow().isoformat()

    def _color_from_coherence(self, value: float) -> str:
        """
        Map coherence (0–1) → perceptual color.
        """
        v = np.clip(value, 0.0, 1.0)
        if v < 0.5:
            return f"rgb({int(0)}, {int(100 + 200 * v)}, 255)"
        else:
            return f"rgb(255, {int(255 * (1 - (v - 0.5) * 2))}, {int(150 + 100 * v)})"

    # ──────────────────────────────────────────────
    #  Field Tensor Computation (ψ–κ–T)
    # ──────────────────────────────────────────────
    def _update_field_tensor(self):
        if not self.nodes:
            return

        entropy_values = [n["entropy"] for n in self.nodes.values()]
        coherence_values = [n["coherence"] for n in self.nodes.values()]
        drift_values = [n["drift"] for n in self.nodes.values()]

        ψ = float(np.mean(entropy_values))
        κ = float(np.tanh(len(self.nodes) / 50.0))  # curvature proxy
        T = float(time.time() % 1000 / max(np.mean(coherence_values), 1e-6))

        self.field_tensor = {"psi": ψ, "kappa": κ, "T": T}
        logger.debug(f"[HSTGenerator] Field tensor updated ψ={ψ:.3f} κ={κ:.3f} T={T:.3f}")

    # ──────────────────────────────────────────────
    #  HQCE Stage 3 Integration — Broadcast + Feedback
    # ──────────────────────────────────────────────
    import time
    from datetime import datetime
    from backend.modules.holograms.morphic_feedback_controller import MorphicFeedbackController
    from backend.modules.symbolic.hst.hst_websocket_streamer import broadcast_replay_paths as broadcast_replay_paths_hst

    def broadcast_state(self, force: bool = False):
        """
        Broadcast the current field tensor and node states,
        applying Morphic Feedback regulation if ψ–κ–T data is present.
        """
        now = time.time()
        if not force and (now - getattr(self, "last_update_time", 0)) < getattr(self, "update_interval", 0.5):
            return

        self.last_update_time = now

        if hasattr(self, "field_tensor") and hasattr(self, "nodes") and self.field_tensor:
            controller = MorphicFeedbackController()
            adjustment = controller.regulate(self.field_tensor, list(self.nodes) if isinstance(self.nodes, list) else list(self.nodes.values()))
            self.nodes = controller.generate_field_overlay(list(self.nodes.values()))
            print(f"⚙️ Morphic Feedback: {adjustment['status']} (Δ={adjustment['correction']:+.4f})")

        payload = {
            "session_id": getattr(self, "session_id", "unknown"),
            "timestamp": datetime.utcnow().isoformat(),
            "nodes": list(self.nodes.values()) if isinstance(self.nodes, dict) else self.nodes,
            "field_tensor": getattr(self, "field_tensor", {}),
            "type": "hst_field_state"
        }

        try:
            broadcast_replay_paths_hst(self.container_id, [])
            print(f"📡 HST broadcast complete for {payload['session_id']}")
        except Exception as e:
            print(f"⚠️ Broadcast failed: {e}")

    # ──────────────────────────────────────────────
    #  Export & Persistence
    # ──────────────────────────────────────────────
    def export_snapshot(self, path: str):
        """
        Save current HST field snapshot to disk.
        """
        snapshot = {
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "nodes": list(self.nodes.values()),
            "links": self.links,
            "field_tensor": self.field_tensor
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)
        logger.info(f"[HSTGenerator] Snapshot exported → {path}")

    def clear(self):
        """Reset all nodes and field data."""
        self.nodes.clear()
        self.links.clear()
        self.field_tensor = None
        logger.info("[HSTGenerator] Cleared field data.")

# ──────────────────────────────────────────────
# Example Usage
# ──────────────────────────────────────────────
"""
from backend.modules.holograms.hst_generator import HSTGenerator

hst = HSTGenerator()

# Inject a LightWave beam
hst.inject_lightwave_beam({
    "beam_id": "beam_42",
    "entropy": 0.15,
    "coherence": 0.92,
    "goal_match": 0.87,
    "drift": 0.02,
    "symbol": "🌊"
})

# Periodic broadcast (to HSTVisualizer + GHX overlay)
hst.broadcast_state()

# Export to disk
hst.export_snapshot("telemetry/hst_snapshot.json")
"""