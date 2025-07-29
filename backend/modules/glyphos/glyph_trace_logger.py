import time
import json
from pathlib import Path
from typing import List, Optional, Dict
from asyncio import create_task

from backend.modules.glyphnet.glyphnet_ws import broadcast_event  # ✅ WebSocket broadcast
from backend.modules.glyphvault.vault_bridge import get_container_snapshot_id  # ✅ Snapshot ID fetch
from backend.modules.replay.glyph_replay_renderer import GlyphReplayRenderer  # ✅ Auto-play renderer link

LOG_PATH = Path("logs/glyph_trace_log.json")


class GlyphTraceLogger:
    def __init__(self, persist: bool = True):
        self.trace_log: List[dict] = []
        self.replay_log: List[dict] = []  # ✅ Replay-specific log
        self.persist = persist
        self.replay_renderer = GlyphReplayRenderer()  # ✅ Auto-wire renderer
        self._load_existing_log()

    def _load_existing_log(self):
        if self.persist and LOG_PATH.exists():
            try:
                with open(LOG_PATH, "r") as f:
                    self.trace_log = json.load(f)
            except Exception:
                self.trace_log = []

    def _save_log(self):
        if not self.persist:
            return
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(LOG_PATH, "w") as f:
                json.dump(self.trace_log[-500:], f, indent=2)  # Keep last 500 entries
        except Exception as e:
            print(f"[⚠️] Failed to persist trace log: {e}")

    def log_trace(self, glyph: str, result: str, context: str = "runtime") -> dict:
        entry = {
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "glyph": glyph,
            "result": result,
            "context": context
        }
        self.trace_log.append(entry)
        self._save_log()
        return entry

    def get_recent_traces(self, limit: int = 25) -> List[dict]:
        return self.trace_log[-limit:]

    def filter_traces(self, glyph: Optional[str] = None, context: Optional[str] = None) -> List[dict]:
        filtered = self.trace_log
        if glyph:
            filtered = [t for t in filtered if t["glyph"] == glyph]
        if context:
            filtered = [t for t in filtered if t["context"] == context]
        return filtered[-100:]

    def export_to_scroll(self) -> dict:
        """
        Export the trace log as a .codexscroll structure.
        """
        return {
            "scroll_type": "glyph_trace",
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "entries": self.trace_log[-100:]  # last 100 traces
        }

    # ──────────────────────────────
    # 🧩 Replay Logging & Broadcast
    # ──────────────────────────────
    def add_glyph_replay(
        self,
        glyphs: List[Dict],
        container_id: str,
        tick_start: int,
        tick_end: int,
        entangled_links: Optional[List[Dict]] = None,
    ):
        """
        Logs a replayable glyph trace sequence with Vault snapshot ID, broadcasts it,
        and auto-triggers replay rendering to GHX/UI timeline.
        """
        snapshot_id = get_container_snapshot_id(container_id)  # ✅ Link replay to Vault snapshot

        replay_entry = {
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tick_start": tick_start,
            "tick_end": tick_end,
            "container_id": container_id,
            "snapshot_id": snapshot_id,          # ✅ Attached snapshot ID
            "glyphs": glyphs,
            "entangled_links": entangled_links or [],
        }

        self.replay_log.append(replay_entry)

        # 🛰️ Broadcast replay event over WebSocket
        try:
            broadcast_payload = {
                "type": "glyph_replay_log",
                "container_id": container_id,
                "snapshot_id": snapshot_id,
                "tick_start": tick_start,
                "tick_end": tick_end,
                "glyphs": glyphs,
                "links": entangled_links or [],
                "meta": {
                    "glyph_count": len(glyphs),
                    "entangled_link_count": len(entangled_links or []),
                },
            }
            create_task(broadcast_event(broadcast_payload))
        except Exception as e:
            print(f"[⚠️] Failed to broadcast glyph replay: {e}")

        # 🔁 Auto-load replay into renderer for frame emission
        try:
            print(f"[🎞️ Replay Auto-Load] Initiating frame render for {len(glyphs)} glyphs.")
            create_task(self.replay_renderer.load_and_play(replay_entry))
        except Exception as e:
            print(f"[⚠️] Failed to auto-load replay into renderer: {e}")

        print(f"🛰️ Logged glyph replay: {len(glyphs)} glyphs, ticks {tick_start} → {tick_end}, snapshot={snapshot_id}")
        return replay_entry

    # ──────────────────────────────
    # 🔁 Entangled Replay API (NEW)
    # ──────────────────────────────
    def add_entangled_replay(
        self,
        glyphs: List[Dict],
        container_id: str,
        entangled_links: List[Dict],
    ):
        """
        Shortcut: replay entangled glyphs only.
        """
        tick_start = int(time.time() * 1000)
        tick_end = tick_start + (len(glyphs) * 10)  # estimate progression ticks
        return self.add_glyph_replay(glyphs, container_id, tick_start, tick_end, entangled_links)


# ✅ Singleton instance
glyph_trace = GlyphTraceLogger()

# 🧪 Optional test
if __name__ == "__main__":
    glyph_trace.log_trace("⚛", "dream started", context="tessaris")
    glyph_trace.log_trace("⬁", "mutation proposed", context="dna")
    glyph_trace.add_glyph_replay(
        glyphs=[{"id": "g1", "glyph": "⚛"}, {"id": "g2", "glyph": "↔"}],
        container_id="test_container",
        tick_start=100,
        tick_end=120,
        entangled_links=[{"source": "g1", "target": "g2"}],
    )
    glyph_trace.add_entangled_replay(
        glyphs=[{"id": "g3", "glyph": "⧖"}],
        container_id="test_container",
        entangled_links=[{"source": "g2", "target": "g3"}],
    )
    print("Last 2 traces:", glyph_trace.get_recent_traces(2))
    print("Replay log:", json.dumps(glyph_trace.replay_log[-1], indent=2))