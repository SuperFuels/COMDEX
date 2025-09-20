# File: backend/modules/glyphnet/replay_timeline_renderer.py

"""
🎞️ Replay Timeline Renderer (A6a)
────────────────────────────────────────────
Converts glyph replay logs into frame-by-frame playback with WebSocket streaming.

✅ Frame-by-frame playback of glyph replay logs.
✅ Aligns frames with tick progression (tick_start → tick_end).
✅ Supports pause/play/seek for scrubbable replay.
✅ Streams incremental frames via WebSocket (GHX/UI sync).
✅ Live WebSocket control (pause/resume/seek/stop/play).
"""

import asyncio
import logging
from typing import List, Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.modules.glyphnet.glyph_trace_logger import glyph_trace
from backend.modules.glyphnet.glyphnet_ws import stream_replay_frame

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/glyphnet", tags=["Replay"])


class ReplayTimelineRenderer:
    def __init__(self, playback_speed: float = 1.0):
        self.playback_speed = playback_speed
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Start unpaused
        self.is_playing = False
        self.current_frame = 0

    async def play_replay(self, replay_index: int = -1, auto_loop: bool = False):
        """Play a recorded glyph replay log frame-by-frame."""
        if not glyph_trace.replay_log:
            logger.warning("⚠️ No replays available in glyph_trace.")
            return

        if replay_index < -1 or replay_index >= len(glyph_trace.replay_log):
            raise IndexError(f"Replay index {replay_index} out of range.")

        # Default to last replay if index = -1
        replay_entry = glyph_trace.replay_log[replay_index]
        glyphs: List[Dict[str, Any]] = replay_entry["glyphs"]
        tick_start: int = replay_entry["tick_start"]
        tick_end: int = replay_entry["tick_end"]
        container_id: str = replay_entry["container_id"]

        total_ticks = max(1, tick_end - tick_start)
        frame_interval = (total_ticks / max(1, len(glyphs))) / self.playback_speed

        self.is_playing = True
        self.current_frame = 0

        logger.info(
            f"[Replay] ▶️ Starting playback: container={container_id}, "
            f"frames={len(glyphs)}, speed={self.playback_speed}x"
        )

        while self.is_playing and self.current_frame < len(glyphs):
            await self._pause_event.wait()  # Pause support

            glyph_state = {
                "glyph": glyphs[self.current_frame],
                "frame": self.current_frame,
                "total_frames": len(glyphs),
                "tick": tick_start + int((self.current_frame / len(glyphs)) * total_ticks),
                "entangled_links": replay_entry.get("entangled_links", []),
                "snapshot_id": replay_entry.get("snapshot_id"),
            }

            await stream_replay_frame(
                frame_index=self.current_frame,
                glyph_state=glyph_state,
                container_id=container_id,
            )

            await asyncio.sleep(frame_interval)
            self.current_frame += 1

        logger.info(f"[Replay] ⏹️ Completed playback for container {container_id}")

        if auto_loop and self.is_playing:
            logger.info("[Replay] 🔁 Looping enabled, restarting playback.")
            await self.play_replay(replay_index, auto_loop=True)

    def pause(self):
        self._pause_event.clear()
        logger.info("[Replay] ⏸️ Paused.")

    def resume(self):
        self._pause_event.set()
        logger.info("[Replay] ▶️ Resumed.")

    def resume_from(self, frame_index: int):
        self.current_frame = max(0, frame_index)
        self.is_playing = True
        self._pause_event.set()
        logger.info(f"[Replay] ▶️ Resumed from frame {self.current_frame}")

    def seek(self, frame_index: int):
        self.current_frame = max(0, frame_index)
        logger.info(f"[Replay] ⏩ Seeked to frame {self.current_frame}. Resume to continue playback.")

    def stop(self):
        self.is_playing = False
        self._pause_event.set()
        logger.info("[Replay] ⏹️ Stopped.")


# ✅ Singleton instance
replay_renderer = ReplayTimelineRenderer()


# ───────────────────────────────────────────────
# 🎮 WebSocket Control API
# ───────────────────────────────────────────────
@router.websocket("/ws/replay-control")
async def replay_control_ws(websocket: WebSocket):
    await websocket.accept()
    logger.info("[ReplayWS] 🎮 Client connected for replay control.")

    try:
        while True:
            msg = await websocket.receive_json()
            action = msg.get("action")

            if action == "pause":
                replay_renderer.pause()
                await websocket.send_json({"status": "ok", "action": "pause"})

            elif action == "resume":
                replay_renderer.resume()
                await websocket.send_json({"status": "ok", "action": "resume"})

            elif action == "seek":
                frame = int(msg.get("frame", 0))
                replay_renderer.seek(frame)
                await websocket.send_json({"status": "ok", "action": "seek", "frame": frame})

            elif action == "stop":
                replay_renderer.stop()
                await websocket.send_json({"status": "ok", "action": "stop"})

            elif action == "play":
                index = int(msg.get("index", -1))
                asyncio.create_task(replay_renderer.play_replay(replay_index=index))
                await websocket.send_json({"status": "ok", "action": "play", "index": index})

            else:
                await websocket.send_json({"status": "error", "message": f"Unknown action {action}"})

    except WebSocketDisconnect:
        logger.info("[ReplayWS] ❌ Client disconnected.")
    except Exception as e:
        logger.error(f"[ReplayWS] Error: {e}")
        await websocket.close()