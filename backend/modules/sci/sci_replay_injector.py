# ============================================================
# 🧠 SCI ↔ Photon Replay Injector (Unified Reinjection Version)
# ============================================================
# Provides three replay modes:
#   1️⃣ Local scroll replay (from ResonantMemoryCache → QFC HUD)
#   2️⃣ Photon resonance replay via HTTP (for live optical telemetry)
#   3️⃣ Workspace reinjection (keeps SCI IDE + container state synchronized)
# ------------------------------------------------------------
from __future__ import annotations
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import aiohttp
import asyncio
import json
import time
import logging

logger = logging.getLogger("sci_replay_injector")

# ------------------------------------------------------------
# Optional Integrations — fallbacks auto-stubbed
# ------------------------------------------------------------
try:
    from backend.modules.visualization.quantum_field_canvas_api import trigger_qfc_render
except Exception:
    async def trigger_qfc_render(payload, source="sci_replay_injector"):
        print(f"[StubQFC] Render skipped from {source}")

try:
    from backend.modules.sci.sci_qfc_export_bridge import broadcast_qfc_event
except Exception:
    async def broadcast_qfc_event(payload):
        print(f"[StubBroadcast] {json.dumps(payload, indent=2)}")

try:
    from backend.modules.sci.container_workspace_loader import load_workspace_container
except Exception:
    async def load_workspace_container(container_id):
        print(f"[StubContainer] Loaded {container_id}")
        return {"id": container_id, "loaded": True}

try:
    from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
    RMC = ResonantMemoryCache.get_instance()
except Exception:
    RMC = None

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
PHOTON_API_BASE = "http://localhost:8000/api/photon"


# ============================================================
# 🔁 Main Class
# ============================================================
class SCIReplayInjector:
    """
    Unified SCI Replay Injector
    - Replays scrolls from Resonant Memory (QFC / D3)
    - Streams Photon telemetry frames via API
    - Reinjection to workspace containers for IDE sync
    """

    def __init__(self, send_fn: Optional[Callable] = None, session: Optional[aiohttp.ClientSession] = None):
        self.send_fn = send_fn
        self.session = session or aiohttp.ClientSession()
        self.replay_speed = 1.0
        self.active = False

    # ============================================================
    # 📜 Scroll-Based Replay (Resonant Memory → QFC)
    # ============================================================
    def replay_scroll(self, label: str, container_id: Optional[str] = None, user_id: Optional[str] = None):
        """Replay a saved memory scroll from ResonantMemoryCache."""
        if not RMC:
            logger.warning("ResonantMemoryCache unavailable.")
            return {"ok": False, "error": "ResonantMemoryCache missing"}

        scroll = RMC.get_entry_by_label(label)
        if not scroll:
            logger.warning(f"[SCIReplayInjector] Scroll not found: {label}")
            return {"ok": False, "error": f"Scroll '{label}' not found"}

        logger.info(f"[SCIReplayInjector] Replaying scroll '{label}' for container={container_id}")
        frame_state = scroll.get("state") or scroll

        # Broadcast to QFC
        asyncio.create_task(self._async_qfc_broadcast(frame_state, container_id, user_id))
        # Reinjection
        asyncio.create_task(self._async_workspace_reinject(frame_state, container_id))

        return {"ok": True, "label": label}

    async def _async_qfc_broadcast(self, frame_state: Dict[str, Any], container_id: str, user_id: str):
        """Emit state to QFC visualization."""
        payload = {
            "event": "qfc_scroll_replay",
            "container_id": container_id,
            "user_id": user_id,
            "state": frame_state,
            "timestamp": time.time(),
        }
        await broadcast_qfc_event(payload)
        await trigger_qfc_render(frame_state, source="replay_scroll")
        logger.info(f"[SCIReplayInjector] ✅ QFC broadcast complete for {container_id}")

    async def _async_workspace_reinject(self, frame_state: Dict[str, Any], container_id: str):
        """Refresh active workspace container with replayed state."""
        try:
            ws = await load_workspace_container(container_id)
            ws["reinjected_state"] = frame_state
            logger.info(f"[SCIReplayInjector] 🔄 Workspace rehydrated for {container_id}")
        except Exception as e:
            logger.warning(f"[SCIReplayInjector] Workspace reinjection failed: {e}")

    # ============================================================
    # 🌐 Photon Telemetry Integration
    # ============================================================
    async def fetch_snapshots(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch Photon telemetry snapshot metadata."""
        url = f"{PHOTON_API_BASE}/available_snapshots?limit={limit}"
        async with self.session.get(url) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Snapshot listing failed: {resp.status}")
            data = await resp.json()
            return data.get("snapshots", [])

    async def replay_photon_timeline(self, limit: int = 5, reinjection: bool = True, delay: float = 0.8):
        """
        Streams Photon resonance frames and reinjects them into SCI/QFC.
        """
        url = f"{PHOTON_API_BASE}/replay_timeline?limit={limit}&broadcast=true&delay={delay}"
        async with self.session.get(url) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Replay failed: {resp.status}")
            payload = await resp.json()
            frames = payload.get("frames", [])

        if reinjection:
            for frame in frames:
                container_id = frame.get("container_id", "default_container")
                await load_workspace_container(container_id)
                await self._reinjection_broadcast(frame, container_id)
                await asyncio.sleep(0.2)

        return frames

    async def _reinjection_broadcast(self, frame: Dict[str, Any], container_id: str):
        """Unified reinjection + visualization pipeline."""
        packet = {
            "type": "sci_replay_frame",
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "container_id": container_id,
            "frame": frame,
            "source": "sci_replay_injector",
        }
        await broadcast_qfc_event(packet)
        await trigger_qfc_render({"type": "replay", "frame": frame}, source="sci_replay_injector")
        logger.info(f"♻️ Reinjected workspace for [{container_id}] from {frame.get('replayed_from')}")

    # ============================================================
    # 📡 Local Scroll Timed Playback
    # ============================================================
    def start_replay(self, replay_log: List[Dict[str, Any]], observer_id: Optional[str] = None, speed: float = 1.0):
        """Timed playback for local D3/QFC replays."""
        if not replay_log:
            print("⚠️ No replay log provided.")
            return

        self.active = True
        self.replay_speed = speed
        print(f"🔁 Starting SCI replay: {len(replay_log)} frames @ {speed}x speed")

        last_timestamp = None
        for frame in replay_log:
            if not self.active:
                break
            timestamp = frame.get("timestamp")
            payload = frame.get("payload")
            if last_timestamp is not None and timestamp is not None:
                delay = (timestamp - last_timestamp) / self.replay_speed
                time.sleep(max(0, delay))
            last_timestamp = timestamp
            if payload and self.send_fn:
                self.send_fn({
                    "type": "qfc.replay_frame",
                    "observer": observer_id,
                    "frame": payload
                })

        print("✅ Replay complete.")
        self.active = False

    def stop_replay(self):
        self.active = False
        print("⏹️ Replay stopped.")

    async def close(self):
        await self.session.close()


# ============================================================
# 🧪 Demo Harness
# ============================================================
async def _demo():
    injector = SCIReplayInjector(send_fn=lambda e: print(f"📤 Sent: {e}"))

    # Local replay demo
    mock_log = [
        {"timestamp": 0, "payload": {"nodes": ["A"]}},
        {"timestamp": 1, "payload": {"nodes": ["B"]}},
    ]
    injector.start_replay(mock_log, observer_id="demo", speed=2.0)

    # Photon replay demo
    try:
        frames = await injector.replay_photon_timeline(limit=1)
        print(f"✅ Replayed {len(frames)} Photon frames")
    except Exception as e:
        print(f"Photon demo skipped: {e}")

    await injector.close()


if __name__ == "__main__":
    asyncio.run(_demo())