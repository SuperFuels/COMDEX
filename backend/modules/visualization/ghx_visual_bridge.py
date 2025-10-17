# ──────────────────────────────────────────────
#  Tessaris • GHX WebSocket Bridge (HQCE Stage 13)
#  Live ψ–κ–T, Φ–coherence, and semantic gravity stream bridge
#  Unifies ResonanceLedger → GHX/QFC overlays + GWV replay
# ──────────────────────────────────────────────

import asyncio
import time
import math
from typing import Dict, Any, List, Optional

from backend.modules.photon.resonance.resonance_ledger import ResonanceLedger
from backend.modules.websocket_manager import broadcast_event
from backend.modules.glyphwave.emit_gwave_replay import ReplayController
from backend.modules.holograms.morphic_ledger import morphic_ledger

# ✅ CodexLang HUD event bridge
try:
    from backend.modules.codex.codex_websocket_interface import send_codex_ws_event
except Exception:
    async def send_codex_ws_event(event_type: str, payload: dict):
        print(f"[Fallback HUD] {event_type} → {payload}")


# ──────────────────────────────────────────────
#  Color mapping helper
# ──────────────────────────────────────────────
def _coherence_to_color(coherence: float) -> Dict[str, Any]:
    """Map coherence [0,1] → HSL color, RGB tuple, and alpha channel."""
    c = max(0.0, min(1.0, coherence))
    hue = 270 * (1 - c)            # violet → white hue gradient
    val = 80 + int(c * 120)        # brightness range
    rgb = [
        round(255 * c),            # R
        round(180 + 75 * c),       # G
        round(255 * (1 - c / 2)),  # B
    ]
    return {
        "hsl": f"hsl({hue:.0f}, 80%, {val}%)",
        "rgb": rgb,
        "alpha": round(0.5 + 0.5 * c, 2),
    }


# ──────────────────────────────────────────────
#  GHX ↔ Visualization Bridge
# ──────────────────────────────────────────────
class GHXVisualBridge:
    """Synchronizes ResonanceLedger + MorphicTelemetry into GHX visual frames."""

    def __init__(self, ledger: ResonanceLedger):
        self.ledger = ledger
        self.frame_index = 0
        self._replay_controller: Optional[ReplayController] = None
        self._last_ingested_frame: Optional[Dict[str, Any]] = None
        self._last_semantic_gravity: Optional[Dict[str, Any]] = None

    # ────────────────────────────────────────────
    #  Frame Construction
    # ────────────────────────────────────────────
    async def build_frame(self) -> Dict[str, Any]:
        """Create GHX frame enriched with ψ–κ–T + gravity overlays."""
        links = self.ledger.active_links()
        stability = await self.ledger.compute_lyapunov_stability()

        # Fetch latest ψ–κ–T snapshot from Morphic Ledger if available
        latest_entry = morphic_ledger.latest_metrics() if hasattr(morphic_ledger, "latest_metrics") else {}
        psi = latest_entry.get("ψ", 0.0)
        kappa = latest_entry.get("κ", 0.0)
        coherence = latest_entry.get("C", 0.0)

        nodes, edges = {}, []
        for a, b, data in links:
            color = _coherence_to_color(data.get("coherence", coherence or 1.0))
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
        frame = {
            "type": "ghx_frame",
            "timestamp": time.time(),
            "frame_index": self.frame_index,
            "stability": stability,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "psi_kappa_T": {"ψ": psi, "κ": kappa, "C": coherence},
            "nodes": list(nodes.values()),
            "edges": edges,
        }

        return frame

    # ────────────────────────────────────────────
    #  Broadcast (GHX + HUD)
    # ────────────────────────────────────────────
    async def broadcast_frame(self):
        """Emit GHX frame to QFC overlay and CodexLang HUD."""
        frame = await self.build_frame()

        try:
            # Primary WebSocket broadcast (internal overlay)
            await broadcast_event({
                "type": "ghx_resonance_update",
                "data": frame,
            })

            # HUD broadcast (CodexLang protocol)
            await send_codex_ws_event("hqce_frame_update", {
                "ψκT": frame.get("psi_kappa_T"),
                "stability": frame.get("stability"),
                "node_count": frame.get("node_count"),
                "timestamp": frame.get("timestamp"),
            })

            # Semantic gravity stream (if available)
            if self._last_semantic_gravity:
                await send_codex_ws_event("semantic_gravity_update", self._last_semantic_gravity)

            return {"status": "broadcast", "count": frame["edge_count"]}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    # ────────────────────────────────────────────
    #  Live Loop (Adaptive)
    # ────────────────────────────────────────────
    async def live_loop(self, interval: float = 1.0):
        """Continuously stream GHX frames; adapt tick rate to stability."""
        print(f"[GHXVisualBridge] Live visualization loop started @ {interval}s intervals")
        while True:
            frame = await self.build_frame()
            stability = frame.get("stability", 1.0)
            dynamic_interval = max(0.2, interval * (1.0 + 0.5 * abs(1 - stability)))
            await self.broadcast_frame()
            await asyncio.sleep(dynamic_interval)

    # ────────────────────────────────────────────
    #  Semantic Gravity Ingestion
    # ────────────────────────────────────────────
    def ingest_semantic_gravity(self, gravity_map: Dict[str, Any]):
        """Accept external semantic gravity deltas (from SymbolicHSXBridge)."""
        self._last_semantic_gravity = gravity_map

    # ────────────────────────────────────────────
    #  Replay integration (GWV ↔ GHX bridge)
    # ────────────────────────────────────────────
    async def ingest_frame(self, frame: Dict[str, Any]):
        """Accept frame data during GWV replay for visualization."""
        self._last_ingested_frame = frame
        # Future: feed into Codex replay analytics
        await send_codex_ws_event("ghx_replay_ingest", {
            "frame_index": frame.get("frame_index"),
            "timestamp": frame.get("timestamp"),
            "stability": frame.get("stability"),
        })

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