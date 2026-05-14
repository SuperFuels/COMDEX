"""
🎞️ Glyph Replay Renderer (Merged: Renderer + Timeline)
────────────────────────────────────────────
Combines identity-aware replay rendering with tick-aligned timeline playback.

✅ Identity & Permission-aware glyph rendering.
✅ Frame-by-frame playback with tick alignment.
✅ Pause/Resume/Seek support.
✅ GHX WebSocket frame streaming.
✅ Replay log integration from glyph_trace.
✅ Compatible with previous ReplayTimelineRenderer usage.
"""

import asyncio
import time
from typing import List, Dict, Optional, Any
from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime
from backend.routes.ws.glyphnet_ws import broadcast_event  # ✅ WebSocket broadcast
from backend.modules.glyphnet.agent_identity_registry import agent_identity_registry  # ✅ Permission + Identity Registry


class GlyphReplayRenderer:
    def __init__(self):
        self.container = self._get_active_container()
        self.grid = self.container.get("glyph_grid", []) if self.container else []
        self.is_playing = False
        self.current_frame_index = 0
        self.current_replay: Optional[Dict[str, Any]] = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self.playback_speed = 1.0

    def _get_active_container(self) -> dict:
        """Fetch the active container from UCS runtime singleton."""
        ucs = get_ucs_runtime()
        if ucs.containers:
            # Return the most recently loaded container
            return list(ucs.containers.values())[-1]
        return {}

    # ──────────────────────────────
    # 🎛️ Identity-Aware Replay Rendering
    # ──────────────────────────────
    def render_replay_sequence(
        self,
        glyph_types: Optional[List[str]] = None,
        include_metadata: bool = True,
        include_trace: bool = True,
        sort_by_time: bool = True,
        limit: Optional[int] = None,
        requesting_agent: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return a structured glyph replay list from the active container with permissions."""
        result = []
        for glyph in self.grid:
            if glyph_types and glyph.get("type") not in glyph_types:
                continue

            agent_id = glyph.get("agent_id", "system")
            permission = self._resolve_permission(agent_id, requesting_agent)
            if permission == "hidden":
                continue

            entry = {
                "id": glyph.get("id"),
                "type": glyph.get("type"),
                "content": glyph.get("content") if permission != "hidden" else "🔒 HIDDEN",
                "timestamp": glyph.get("timestamp"),
                "permission": permission,
            }

            if include_metadata:
                metadata = glyph.get("metadata", {}).copy()
                metadata["agent_id"] = agent_id
                metadata["permission"] = permission
                entry["metadata"] = metadata

            if include_trace and "trace_ref" in glyph:
                entry["trace_ref"] = glyph["trace_ref"]
            if "prediction" in glyph:
                entry["prediction"] = glyph["prediction"]
            if "coordinates" in glyph:
                entry["coordinates"] = glyph["coordinates"]
            if "region" in glyph:
                entry["region"] = glyph["region"]
            if "source_plugin" in glyph:
                entry["source_plugin"] = glyph["source_plugin"]

            result.append(entry)

        if sort_by_time:
            result.sort(key=lambda g: g.get("timestamp", ""))
        if limit:
            result = result[:limit]
        return result

    def _resolve_permission(self, glyph_agent: str, requesting_agent: Optional[str]) -> str:
        """Determine permission level for a glyph relative to the requesting agent."""
        if not requesting_agent:
            return "read-only"
        if requesting_agent == glyph_agent:
            return "editable"
        if agent_identity_registry.has_permission(requesting_agent, "kg_edit"):
            return "read-only"
        return "hidden"

    def get_replay_as_trace(self, glyph_type: str = "dream", requesting_agent: Optional[str] = None) -> str:
        replay = self.render_replay_sequence(glyph_types=[glyph_type], requesting_agent=requesting_agent)
        return "\n".join([f"[{g['timestamp']}] {g['content']}" for g in replay])

    def get_replay_stats(self) -> Dict[str, int]:
        counts = {}
        for glyph in self.grid:
            gtype = glyph.get("type", "unknown")
            counts[gtype] = counts.get(gtype, 0) + 1
        return counts

    # ──────────────────────────────
    # 🎞️ Replay Log Integration (A6a)
    # ──────────────────────────────
    def load_glyph_replay(self, replay_entry: Dict[str, Any]):
        """Load a replay log entry for playback."""
        self.current_replay = replay_entry
        self.current_frame_index = 0
        print(f"🎞️ Loaded replay: {len(replay_entry['glyphs'])} glyphs, ticks {replay_entry['tick_start']} -> {replay_entry['tick_end']}")

    def load_latest_replay(self):
        """Helper: Load the most recent replay log from glyph_trace."""
        from backend.modules.glyphos.glyph_trace_logger import glyph_trace  # ✅ Lazy import
        if not glyph_trace.replay_log:
            print("⚠️ No replay logs available.")
            return None
        latest = glyph_trace.replay_log[-1]
        self.load_glyph_replay(latest)
        return latest

    # ──────────────────────────────
    # ⏱️ Timeline Playback (Tick-Aligned)
    # ──────────────────────────────
    async def play_replay(self, replay_index: int = -1, auto_loop: bool = False):
        """Play a glyph replay log frame-by-frame with tick alignment."""
        from backend.modules.glyphos.glyph_trace_logger import glyph_trace  # ✅ Lazy import
        if replay_index >= len(glyph_trace.replay_log):
            raise IndexError(f"Replay index {replay_index} out of range.")
        replay_entry = glyph_trace.replay_log[replay_index]
        self.load_glyph_replay(replay_entry)

        glyphs = replay_entry["glyphs"]
        tick_start = replay_entry["tick_start"]
        tick_end = replay_entry["tick_end"]
        total_ticks = max(1, tick_end - tick_start)
        frame_interval = (total_ticks / len(glyphs)) / 1000.0 / self.playback_speed

        self.is_playing = True
        self.current_frame_index = 0
        print(f"[🎞️ Replay] Starting playback for container {replay_entry['container_id']}, frames={len(glyphs)}")

        while self.is_playing and self.current_frame_index < len(glyphs):
            await self._pause_event.wait()
            glyph_state = {
                "glyph": glyphs[self.current_frame_index],
                "frame": self.current_frame_index,
                "total_frames": len(glyphs),
                "tick": tick_start + int((self.current_frame_index / len(glyphs)) * total_ticks),
                "entangled_links": replay_entry.get("entangled_links", []),
                "snapshot_id": replay_entry.get("snapshot_id"),
            }
            await self.emit_frame(self.current_frame_index, glyph_state)
            await asyncio.sleep(frame_interval)
            self.current_frame_index += 1

        print(f"[🎞️ Replay] Completed playback.")
        if auto_loop and self.is_playing:
            print("[🔁 Replay] Looping enabled, restarting playback.")
            await self.play_replay(replay_index, auto_loop=True)

    async def emit_frame(self, frame_index: int, glyph_state: Dict[str, Any]):
        """Emit a replay frame via WebSocket for GHX/UI sync."""
        payload = {
            "type": "glyph_replay_frame",
            "frame_index": frame_index,
            "glyph_state": glyph_state,
            "total_frames": len(self.current_replay["glyphs"]),
            "snapshot_id": self.current_replay.get("snapshot_id"),
            "entangled_links": self.current_replay.get("entangled_links", []),
        }
        await broadcast_event(payload)
        print(f"🖼️ Emitted frame {frame_index}/{len(self.current_replay['glyphs'])}")

    # ──────────────────────────────
    # ▶️ Playback Controls
    # ──────────────────────────────
    def play(self, frame_delay: float = 0.2):
        """Legacy: Play current replay sequence (blocking)."""
        if not self.current_replay:
            print("⚠️ No replay loaded.")
            return
        self.is_playing = True
        glyphs = self.current_replay["glyphs"]
        while self.is_playing and self.current_frame_index < len(glyphs):
            asyncio.run(self.emit_frame(self.current_frame_index, {"glyph": glyphs[self.current_frame_index]}))
            self.current_frame_index += 1
            time.sleep(frame_delay)
        print("✅ Replay playback complete.")

    def pause(self):
        self._pause_event.clear()
        self.is_playing = False
        print(f"⏸️ Replay paused at frame {self.current_frame_index}")

    def resume(self):
        self._pause_event.set()
        self.is_playing = True
        print("[▶️ Replay] Resumed.")

    def seek(self, frame_index: int):
        if not self.current_replay:
            print("⚠️ No replay loaded to seek.")
            return
        self.current_frame_index = max(0, min(frame_index, len(self.current_replay["glyphs"]) - 1))
        print(f"⏩ Seeked to frame {self.current_frame_index}")

    def stop(self):
        self.is_playing = False
        self._pause_event.set()
        print("[⏹️ Replay] Stopped.")


# ✅ Singleton instance (preferred)
glyph_replay_renderer = GlyphReplayRenderer()

# ✅ Compatibility alias for legacy imports
ReplayTimelineRenderer = GlyphReplayRenderer