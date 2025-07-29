"""
🎞️ Replay Timeline Renderer (A6a)
────────────────────────────────────────────
Converts glyph replay logs into frame-by-frame playback with WebSocket streaming.

✅ Frame-by-frame playback of glyph replay logs.
✅ Aligns frames with tick progression (tick_start → tick_end).
✅ Supports pause/play/seek for scrubbable replay.
✅ Streams incremental frames via WebSocket (GHX/UI sync).
"""

import asyncio
import time
from typing import List, Dict, Any, Optional

from backend.modules.glyphnet.glyph_trace_logger import glyph_trace
from backend.modules.glyphnet.glyphnet_ws import stream_replay_frame


class ReplayTimelineRenderer:
    def __init__(self, playback_speed: float = 1.0):
        """
        Args:
            playback_speed: Speed multiplier (1.0 = real-time ticks, 2.0 = double speed).
        """
        self.playback_speed = playback_speed
        self.is_playing = False
        self.current_frame = 0
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Start unpaused

    async def play_replay(self, replay_index: int = -1, auto_loop: bool = False):
        """
        Play a recorded glyph replay log frame-by-frame.
        """
        if replay_index >= len(glyph_trace.replay_log):
            raise IndexError(f"Replay index {replay_index} out of range.")
        
        replay_entry = glyph_trace.replay_log[replay_index]
        glyphs: List[Dict[str, Any]] = replay_entry["glyphs"]
        tick_start: int = replay_entry["tick_start"]
        tick_end: int = replay_entry["tick_end"]
        container_id: str = replay_entry["container_id"]

        # Compute frame timing
        total_ticks = max(1, tick_end - tick_start)
        frame_interval = (total_ticks / len(glyphs)) / 1000.0 / self.playback_speed

        self.is_playing = True
        self.current_frame = 0

        print(f"[🎞️ Replay] Starting playback for container {container_id}, frames={len(glyphs)}")

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

        print(f"[🎞️ Replay] Completed playback for container {container_id}")

        if auto_loop and self.is_playing:
            print("[🔁 Replay] Looping enabled, restarting playback.")
            await self.play_replay(replay_index, auto_loop=True)

    def pause(self):
        """Pause playback."""
        self._pause_event.clear()
        self.is_playing = False
        print("[⏸️ Replay] Paused.")

    def resume(self):
        """Resume playback if paused."""
        self._pause_event.set()
        self.is_playing = True
        print("[▶️ Replay] Resumed.")

    def seek(self, frame_index: int):
        """Seek to a specific frame index."""
        if not self.is_playing:
            self.current_frame = max(0, frame_index)
            print(f"[⏩ Replay] Seeked to frame {self.current_frame}. Resume to continue playback.")

    def stop(self):
        """Stop playback entirely."""
        self.is_playing = False
        self._pause_event.set()
        print("[⏹️ Replay] Stopped.")


# ✅ Singleton instance
replay_renderer = ReplayTimelineRenderer()

# 🧪 Test playback
if __name__ == "__main__":
    async def test_replay():
        if not glyph_trace.replay_log:
            print("⚠️ No replays available in glyph_trace. Run a replay log first.")
            return
        await replay_renderer.play_replay(replay_index=-1)

    asyncio.run(test_replay())