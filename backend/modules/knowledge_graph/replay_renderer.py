# File: backend/modules/replay/replay_renderer.py

import datetime
import time
from typing import List, Dict, Optional, Any
from backend.modules.state_manager import get_active_universal_container_system
from backend.modules.glyphnet.glyphnet_ws import broadcast_event  # ✅ WebSocket broadcast
from backend.modules.glyphnet.glyph_trace_logger import glyph_trace  # ✅ Replay logs
from backend.modules.glyphnet.agent_identity_registry import agent_identity_registry  # ✅ Permission + Identity Registry

class GlyphReplayRenderer:
    def __init__(self):
        self.container = get_active_container()
        self.grid = self.container.get("glyph_grid", [])
        self.is_playing = False
        self.current_frame_index = 0
        self.current_replay: Optional[Dict[str, Any]] = None

    def render_replay_sequence(
        self,
        glyph_types: Optional[List[str]] = None,
        include_metadata: bool = True,
        include_trace: bool = True,
        sort_by_time: bool = True,
        limit: Optional[int] = None,
        requesting_agent: Optional[str] = None,  # 🆕 Identity-aware filtering
    ) -> List[Dict[str, Any]]:
        """
        Return a structured list of glyph replay entries from the active container,
        filtered by agent identity with permission tagging.
        """
        result = []
        for glyph in self.grid:
            if glyph_types and glyph.get("type") not in glyph_types:
                continue

            agent_id = glyph.get("agent_id", "system")
            permission = self._resolve_permission(agent_id, requesting_agent)

            # 🔒 Hide glyph if permission is "hidden"
            if permission == "hidden":
                continue

            entry = {
                "id": glyph.get("id"),
                "type": glyph.get("type"),
                "content": glyph.get("content") if permission != "hidden" else "🔒 HIDDEN",
                "timestamp": glyph.get("timestamp"),
                "permission": permission,  # ✅ Permission tagging
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
        """
        Determine permission level for a glyph relative to the requesting agent.
        """
        if not requesting_agent:
            return "read-only"  # Default safe fallback

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
    # 🆕 Frame-by-Frame Replay Renderer (A6a)
    # ──────────────────────────────
    def load_glyph_replay(self, replay_entry: Dict[str, Any]):
        """
        Load a replay log entry from glyph_trace for playback.
        """
        self.current_replay = replay_entry
        self.current_frame_index = 0
        print(f"🎞️ Loaded replay: {len(replay_entry['glyphs'])} glyphs, ticks {replay_entry['tick_start']} → {replay_entry['tick_end']}")

    def play(self, frame_delay: float = 0.2):
        """
        Play the current replay sequence frame-by-frame, emitting WebSocket frames.
        """
        if not self.current_replay:
            print("⚠️ No replay loaded. Call load_glyph_replay() first.")
            return

        self.is_playing = True
        glyphs = self.current_replay["glyphs"]

        while self.is_playing and self.current_frame_index < len(glyphs):
            glyph_state = glyphs[self.current_frame_index]
            self.emit_frame(self.current_frame_index, glyph_state)
            self.current_frame_index += 1
            time.sleep(frame_delay)  # Frame pacing

        print("✅ Replay playback complete.")

    def pause(self):
        """
        Pause the replay playback.
        """
        self.is_playing = False
        print(f"⏸️ Replay paused at frame {self.current_frame_index}")

    def seek(self, frame_index: int):
        """
        Seek to a specific frame in the replay.
        """
        if not self.current_replay:
            print("⚠️ No replay loaded to seek.")
            return
        self.current_frame_index = max(0, min(frame_index, len(self.current_replay["glyphs"]) - 1))
        print(f"⏩ Seeked to frame {self.current_frame_index}")

    def emit_frame(self, frame_index: int, glyph_state: Dict[str, Any]):
        """
        Emit a replay frame via WebSocket for GHX/UI sync.
        """
        payload = {
            "type": "glyph_replay_frame",
            "frame_index": frame_index,
            "glyph_state": glyph_state,
            "total_frames": len(self.current_replay["glyphs"]),
            "snapshot_id": self.current_replay.get("snapshot_id"),
            "entangled_links": self.current_replay.get("entangled_links", []),
        }
        from asyncio import create_task
        create_task(broadcast_event(payload))
        print(f"🖼️ Emitted frame {frame_index}/{len(self.current_replay['glyphs'])}")

    def load_latest_replay(self):
        """
        Helper: Load the most recent replay log from glyph_trace.
        """
        if not glyph_trace.replay_log:
            print("⚠️ No replay logs available.")
            return None
        latest = glyph_trace.replay_log[-1]
        self.load_glyph_replay(latest)
        return latest


# ✅ Singleton instance
glyph_replay_renderer = GlyphReplayRenderer()