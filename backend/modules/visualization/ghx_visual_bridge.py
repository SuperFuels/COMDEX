"""
🟣 GHX Visual Bridge — SRK-18 Task 1–3
Live visualization layer connecting ResonanceLedger to GHX/QFC overlays.

Features:
 • Converts active resonance links → GHX node/edge schema
 • Maps coherence to color hue; Lyapunov stability → overall brightness
 • Streams frames to QFC overlay via WebSocket (if available)
"""

import asyncio
import time
import math
from typing import Dict, Any, List

from backend.modules.photon.resonance.resonance_ledger import ResonanceLedger
from backend.modules.websocket_manager import broadcast_event


def _coherence_to_color(coherence: float) -> str:
    """Map coherence [0,1] to an RGB hex color (violet → white)."""
    c = max(0.0, min(1.0, coherence))
    hue = 270 * (1 - c)           # violet-white gradient
    val = 80 + int(c * 120)       # brightness
    return f"hsl({hue:.0f}, 80%, {val}%)"


class GHXVisualBridge:
    """Synchronizes a ResonanceLedger’s state into GHX visual frames."""

    def __init__(self, ledger: ResonanceLedger):
        self.ledger = ledger
        self.frame_index = 0

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