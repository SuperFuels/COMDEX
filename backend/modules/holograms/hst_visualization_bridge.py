# ──────────────────────────────────────────────
#  Tessaris * HST Visualization Bridge (P5 Core)
#  Connects SLE LightWave beam collapse data -> Holographic Spatial Tensor (HST)
#  Supports live replay, semantic overlays, and ψ-κ-T coherence streaming
# ──────────────────────────────────────────────

import json
import uuid
import time
import logging
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional

# HST WebSocket streamer for real-time visualization
try:
    from backend.modules.holograms.hst_websocket_streamer import broadcast_replay_paths
except Exception:
    def broadcast_replay_paths(payload):
        print(f"[HST Bridge Fallback] {json.dumps(payload)[:200]}...")

# Field tensor compiler (ψ-κ-T computation)
from backend.modules.holograms.compile_field_tensor import compile_field_tensor

logger = logging.getLogger(__name__)


class HSTVisualizationBridge:
    """
    Bridge between SLE LightWave telemetry and HST renderer.
    Injects collapsed beams as semantic nodes, computes ψ-κ-T field signatures,
    and broadcasts replay streams for GHX/HST hybrid visualization.
    """

    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.node_buffer: List[Dict[str, Any]] = []
        self.last_tensor: Optional[Dict[str, float]] = None
        self.broadcast_interval = 0.5  # seconds
        self.last_broadcast_time = 0.0

    # ────────────────────────────────────────────
    #  LightWave Injection
    # ────────────────────────────────────────────
    def inject_beam(self, beam_packet: Dict[str, Any]):
        """
        Accepts a collapsed LightWave beam from SLE runtime.
        Converts to an HST node (semantic + photonic data).
        """
        try:
            node = self._convert_beam_to_node(beam_packet)
            self.node_buffer.append(node)
            logger.info(f"[HST Bridge] Beam injected -> Node {node['node_id']}")
        except Exception as e:
            logger.error(f"[HST Bridge] Beam injection failed: {e}")

    def _convert_beam_to_node(self, beam: Dict[str, Any]) -> Dict[str, Any]:
        beam_id = beam.get("beam_id", str(uuid.uuid4()))
        entropy = float(beam.get("entropy", 0.0))
        drift = float(beam.get("drift", 0.0))
        goal_match = float(beam.get("goal_match", np.clip(1.0 - entropy, 0.0, 1.0)))
        coherence = float(beam.get("coherence", 0.9))
        timestamp = beam.get("timestamp", time.time())

        # Compute local ψ-κ-T signature for this beam
        tensor = compile_field_tensor({
            "drift_entropy": entropy,
            "avg_coherence": coherence,
            "collapse_count": 1,
            "tick_time": 1.0,
            "field_decay": max(beam.get("decay", 1e-3), 1e-6)
        })
        self.last_tensor = tensor

        node = {
            "node_id": beam_id,
            "symbol": beam.get("symbol", "💡"),
            "entropy": entropy,
            "goal_match": goal_match,
            "drift": drift,
            "coherence": coherence,
            "psi_kappa_T": tensor,
            "origin": beam.get("source", "SLE"),
            "injected_at": timestamp,
            "color": self._color_from_coherence(coherence),
            "semantic_overlay": {
                "goal_match": goal_match,
                "entropy": entropy,
                "drift": drift
            }
        }
        return node

    # ────────────────────────────────────────────
    #  Broadcast Loop
    # ────────────────────────────────────────────
    def broadcast_update(self, force: bool = False):
        """
        Broadcast current node buffer + ψ-κ-T overlays to the HST renderer.
        """
        now = time.time()
        if not force and (now - self.last_broadcast_time) < self.broadcast_interval:
            return  # prevent flooding

        payload = {
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "nodes": self.node_buffer[-128:],  # rolling buffer
            "last_tensor": self.last_tensor,
            "type": "hst_field_update",
        }

        try:
            broadcast_replay_paths(payload)
            self.last_broadcast_time = now
            logger.debug(f"[HST Bridge] Broadcast {len(payload['nodes'])} nodes")
        except Exception as e:
            logger.error(f"[HST Bridge] Broadcast failed: {e}")

    # ────────────────────────────────────────────
    #  Utility Methods
    # ────────────────────────────────────────────
    def _color_from_coherence(self, value: float) -> str:
        """
        Map coherence (0-1) -> spectral gradient color (blue->gold).
        """
        v = np.clip(value, 0.0, 1.0)
        if v < 0.5:
            r, g, b = 0, int(100 + 255 * v), 255
        else:
            r, g, b = 255, int(255 * (1.0 - (v - 0.5) * 2)), int(120 + 120 * v)
        return f"rgb({r},{g},{b})"

    def summarize_nodes(self, n: int = 5) -> List[Dict[str, Any]]:
        """Return a summary of the latest HST nodes."""
        return self.node_buffer[-n:]

    def clear_buffer(self):
        """Reset internal HST node buffer."""
        self.node_buffer = []

# ──────────────────────────────────────────────
# Example Integration
# ──────────────────────────────────────────────
"""
# Inside SLE -> Holographic Core coupling:

from backend.modules.holograms.hst_visualization_bridge import HSTVisualizationBridge

hst_bridge = HSTVisualizationBridge()

# After a LightWave beam collapses:
hst_bridge.inject_beam({
    "beam_id": "beam_001",
    "entropy": 0.12,
    "drift": 0.03,
    "coherence": 0.94,
    "goal_match": 0.91,
    "source": "SLE.QWaveBeam"
})

# Periodically (or on tick):
hst_bridge.broadcast_update()
"""