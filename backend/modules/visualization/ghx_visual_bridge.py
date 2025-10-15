"""
🟣 GHX Visual Bridge — SRK-18 + SRK-20 Unified
Live visualization layer connecting ResonanceLedger → GHX/QFC overlays,
now extended with GWV replay capability.

Features:
 • Converts active resonance links → GHX node/edge schema
 • Maps coherence to color hue; Lyapunov stability → overall brightness
 • Streams frames to QFC overlay via WebSocket (if available)
 • Supports playback of recorded .gwv sequences via ReplayController
"""

import asyncio
import time
import math
from typing import Dict, Any, List, Optional

from backend.modules.photon.resonance.resonance_ledger import ResonanceLedger
from backend.modules.websocket_manager import broadcast_event
from backend.modules.glyphwave.emit_gwave_replay import ReplayController


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _coherence_to_color(coherence: float) -> Dict[str, Any]:
    """Map coherence [0,1] → HSL color, RGB tuple, and alpha channel."""
    c = max(0.0, min(1.0, coherence))
    hue = 270 * (1 - c)            # violet → white hue gradient
    val = 80 + int(c * 120)        # brightness range
    # Rough RGB approximation based on coherence intensity
    rgb = [
        round(255 * c),            # R
        round(180 + 75 * c),       # G
        round(255 * (1 - c / 2)),  # B
    ]
    return {
        "hsl": f"hsl({hue:.0f}, 80%, {val}%)",
        "rgb": rgb,
        "alpha": round(0.5 + 0.5 * c, 2),  # semi-transparent at low coherence
    }

# ---------------------------------------------------------------------------
# GHX ↔ Visualization Bridge
# ---------------------------------------------------------------------------

class GHXVisualBridge:
    """Synchronizes a ResonanceLedger’s state into GHX visual frames."""

    def __init__(self, ledger: ResonanceLedger):
        self.ledger = ledger
        self.frame_index = 0
        self._replay_controller: Optional[ReplayController] = None
        self._last_ingested_frame: Optional[Dict[str, Any]] = None

    # -----------------------------------------------------------------------
    # Live frame generation
    # -----------------------------------------------------------------------

    async def build_frame(self) -> Dict[str, Any]:
        """Create a single GHX frame from current ledger state."""
        links = self.ledger.active_links()
        stability = await self.ledger.compute_lyapunov_stability()

        nodes = {}
        edges: List[Dict[str, Any]] = []

        for a, b, data in links:
            color = _coherence_to_color(data.get("coherence", 1.0))
            edges.append({
                "source": a,
                "target": b,
                "phi": round(data.get("phi_delta", 0.0), 4),
                "coherence": data.get("coherence", 1.0),
                "color": color,
            })
            nodes[a] = {"id": a, "color": color}
            nodes[b] = {"id": b, "color": color}

        self.frame_index += 1
        return {
            "type": "ghx_frame",
            "timestamp": time.time(),
            "frame_index": self.frame_index,
            "stability": stability,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": list(nodes.values()),
            "edges": edges,
        }

    async def broadcast_frame(self):
        """Emit GHX frame to QFC overlay websocket channel."""
        frame = await self.build_frame()
        try:
            await broadcast_event({
                "type": "ghx_resonance_update",
                "data": frame,
            })
            return {"status": "broadcast", "count": frame["edge_count"]}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def live_loop(self, interval: float = 1.0):
        """Continuously stream GHX frames at fixed intervals."""
        print(f"[GHX] Live visualization loop started @ {interval}s intervals")
        while True:
            await self.broadcast_frame()
            await asyncio.sleep(interval)

    # -----------------------------------------------------------------------
    # Replay integration (GWV ↔ GHX bridge)
    # -----------------------------------------------------------------------

    async def ingest_frame(self, frame: Dict[str, Any]):
        """Accept frame data during GWV replay for visualization."""
        self._last_ingested_frame = frame
        # Future: hook into QFC overlay or analysis system here

    async def start_replay(self, gwv_path: str, delay: float = 0.1, loop: bool = False):
        """Initialize GWave replay controller and start playback."""
        if self._replay_controller:
            await self.stop_replay()

        self._replay_controller = ReplayController(
            ghx_bridge=self, gwv_path=gwv_path, delay=delay, loop=loop
        )
        await self._replay_controller.start()
        return {"status": "started", "file": gwv_path}

    def pause_replay(self):
        """Pause GWave replay emission."""
        if self._replay_controller:
            self._replay_controller.pause()
            return {"status": "paused"}
        return {"status": "no_replay"}

    def resume_replay(self):
        """Resume a paused replay."""
        if self._replay_controller:
            self._replay_controller.resume()
            return {"status": "resumed"}
        return {"status": "no_replay"}

    def stop_replay(self):
        """Stop and dispose of replay controller."""
        if self._replay_controller:
            self._replay_controller.stop()
            self._replay_controller = None
            return {"status": "stopped"}
        return {"status": "no_replay"}