# File: backend/modules/glyphos/glyph_trace_logger.py
import asyncio
import hashlib
import inspect
import json
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# ✅ Lazy import for broadcast_event to break circular dependency
def get_broadcast_event():
    from backend.routes.ws.glyphnet_ws import broadcast_event
    return broadcast_event

from backend.modules.glyphvault.vault_bridge import get_container_snapshot_id  # ✅ Snapshot ID fetch
def get_glyph_replay_renderer():
    from backend.modules.replay.glyph_replay_renderer import GlyphReplayRenderer
    return GlyphReplayRenderer
    # ✅ Auto-play renderer link
from backend.modules.sqi.sqi_event_bus import publish_kg_added  # ✅ Debounced KG publisher

# ✅ Optional: config flag for GHX logging (won't crash if config missing)
try:
    from backend.config import ENABLE_GLYPH_LOGGING
except Exception:
    ENABLE_GLYPH_LOGGING = True

# ✅ Optional: safe GHX log shim — never raises even if interface changes/missing
try:
    from backend.modules.hologram.ghx_logging import safe_ghx_log
except Exception:
    def safe_ghx_log(ghx, evt):
        # Silent no-op fallback
        try:
            import logging
            logging.debug("[GHX][safe_ghx_log-fallback] %s", evt)
        except Exception:
            pass

LOG_PATH = Path("logs/glyph_trace_log.json")


class GlyphTraceLogger:
    def __init__(self, persist: bool = True):
        self.trace_log: List[dict] = []
        self.replay_log: List[dict] = []  # ✅ Replay-specific log
        self.persist = persist
        self.replay_renderer = GlyphReplayRenderer = get_glyph_replay_renderer()  # ✅ Auto-wire renderer
        self._load_existing_log()

        # ✅ Lightweight debounce to reduce broadcast spam for identical payloads
        self._recent: "OrderedDict[str, float]" = OrderedDict()
        self._DEBOUNCE_MS = 150
        self._RECENT_MAX = 2048

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

    def _sig(self, container_id: str, glyphs: List[Dict], tick_start: int, tick_end: int) -> str:
        """
        Create a short signature for debounce keyed on container+glyph content+tick window.
        """
        try:
            core = {
                "cid": container_id,
                "ts": tick_start,
                "te": tick_end,
                "g": glyphs,
            }
            blob = json.dumps(core, sort_keys=True, separators=(",", ":"))
        except Exception:
            # Fallback if non-serializable content sneaks in
            blob = f"{container_id}|{tick_start}|{tick_end}|{len(glyphs)}"
        return hashlib.sha256(blob.encode()).hexdigest()

    def _recent_drop(self, sig: str) -> bool:
        """
        Return True if we should drop/skip a broadcast for identical payloads
        seen within debounce window.
        """
        now_ms = time.time() * 1000
        ts = self._recent.get(sig)
        if ts and (now_ms - ts) < self._DEBOUNCE_MS:
            return True
        self._recent[sig] = now_ms
        # Trim LRU
        if len(self._recent) > self._RECENT_MAX:
            self._recent.popitem(last=False)
        return False

    def _safe_broadcast(self, payload: Dict) -> None:
        """Call ws broadcast in whatever context we’re in."""
        try:
            broadcast = get_broadcast_event()
            if inspect.iscoroutinefunction(broadcast):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(broadcast(payload))
                except RuntimeError:
                    # no running loop -> run it quickly in a temp loop
                    asyncio.run(broadcast(payload))
            else:
                # sync function
                broadcast(payload)
        except Exception as e:
            print(f"[⚠️] Failed to broadcast glyph replay: {e}")

    def _safe_render_replay(self, replay_entry: Dict) -> None:
        """Try a few method names; never crash if renderer is missing or different."""
        try:
            rr = self.replay_renderer
            if hasattr(rr, "load_and_play"):
                maybe = rr.load_and_play(replay_entry)
                if inspect.iscoroutine(maybe):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(maybe)
                    except RuntimeError:
                        asyncio.run(maybe)
            elif hasattr(rr, "render") and callable(rr.render):
                rr.render(replay_entry)
            elif hasattr(rr, "enqueue") and callable(rr.enqueue):
                rr.enqueue(replay_entry)
            else:
                # No known API—silently ignore
                pass
        except Exception as e:
            print(f"[⚠️] Failed to auto-load replay into renderer: {e}")

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

        # 🔎 Safe GHX log hook (optional)
        if ENABLE_GLYPH_LOGGING:
            safe_ghx_log(
                ghx=None,
                evt={
                    "event": "glyph_trace",
                    "glyph": glyph,
                    "result": result,
                    "context": context,
                    "iso_time": entry["iso_time"],
                },
            )
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
    def _publish_kg_proof_node(self, replay_entry: dict, relates_to: Optional[list] = None) -> None:
        from backend.modules.sqi.sqi_event_bus import publish_kg_added
        import uuid
        import hashlib
        from datetime import datetime, timezone

        container_id = replay_entry["container_id"]
        tick_start = replay_entry["tick_start"]
        tick_end = replay_entry["tick_end"]
        snapshot_id = replay_entry["snapshot_id"]
        glyphs = replay_entry.get("glyphs", [])
        entangled_links = replay_entry.get("entangled_links", [])

        payload = {
            "container_id": container_id,
            "entry": {
                "id": str(uuid.uuid4()),
                "hash": hashlib.sha256(
                    f"{container_id}|proof_replay|{tick_start}|{tick_end}|{snapshot_id}".encode()
                ).hexdigest(),
                "type": "proof_replay",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "tags": [
                    "replay", "proof",
                    f"glyph_count:{len(glyphs)}",
                    f"tick:{tick_start}-{tick_end}",
                ],
                "plugin": "glyph_replay_renderer",
                "meta": {
                    "snapshot_id": snapshot_id,
                    "tick_start": tick_start,
                    "tick_end": tick_end,
                    "entangled_link_count": len(entangled_links or []),
                },
            },
        }
        if relates_to:
            payload["entry"]["meta"]["relates_to"] = list(relates_to)

        published = publish_kg_added(payload)
        print("🧠 KG: proof_replay node published" if published else "🧠 KG: proof_replay node deduped (already published)")

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
            "snapshot_id": snapshot_id,
            "glyphs": glyphs,
            "entangled_links": entangled_links or [],
        }

        # Store in local replay log
        self.replay_log.append(replay_entry)

        # 🧠 Publish into KG as a proof_replay node (debounced/idempotent via bus)
        try:
            self._publish_kg_proof_node(replay_entry)
        except Exception as e:
            print(f"[⚠️] KG proof publish failed: {e}")

        # 🔎 Safe GHX telemetry (optional)
        if ENABLE_GLYPH_LOGGING:
            safe_ghx_log(
                ghx=None,
                evt={
                    "event": "glyph_replay_logged",
                    "container_id": container_id,
                    "snapshot_id": snapshot_id,
                    "tick_start": tick_start,
                    "tick_end": tick_end,
                    "glyph_count": len(glyphs),
                    "entangled_link_count": len(entangled_links or []),
                },
            )

        # 🛰️ Broadcast replay event over WebSocket (debounced, event-loop safe)
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

            sig = self._sig(container_id, glyphs, tick_start, tick_end)
            if not self._recent_drop(sig):
                self._safe_broadcast(broadcast_payload)
            else:
                if ENABLE_GLYPH_LOGGING:
                    safe_ghx_log(
                        ghx=None,
                        evt={
                            "event": "broadcast_dropped_duplicate",
                            "container_id": container_id,
                            "snapshot_id": snapshot_id,
                            "sig": sig[:12],
                        },
                    )
        except Exception as e:
            print(f"[⚠️] Failed to broadcast glyph replay: {e}")

        # 🎞️ Auto-load replay into renderer (best-effort)
        try:
            print(f"[🎞️ Replay Auto-Load] Initiating frame render for {len(glyphs)} glyphs.")
            # If your renderer exposes a different API, wire it here.
            if hasattr(self.replay_renderer, "load_and_play"):
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
        tick_end = tick_start + (len(glyphs) * 10)
        return self.add_glyph_replay(glyphs, container_id, tick_start, tick_end, entangled_links)

    # ──────────────────────────────
    # ✅ NEW: KG proof node publisher
    # ──────────────────────────────
    def _publish_kg_proof_node(self, replay_entry: Dict) -> None:
        """
        Create a KnowledgeGraph 'proof_replay' node for this replay and publish via
        the debounced bus (publish_kg_added). Idempotency is
        sha256(container_id|snapshot_id|tick_start|tick_end).
        """
        cid = replay_entry.get("container_id") or "unknown"
        snap = replay_entry.get("snapshot_id") or "none"
        t0 = replay_entry.get("tick_start")
        t1 = replay_entry.get("tick_end")

        # Stable external hash for idempotency
        ext_base = f"{cid}|{snap}|{t0}|{t1}"
        ext_hash = hashlib.sha256(ext_base.encode("utf-8")).hexdigest()

        iso_now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entry_id = str(uuid.uuid4())

        payload = {
            "container_id": cid,
            "entry": {
                "id": entry_id,
                "hash": ext_hash,
                "type": "proof_replay",
                "timestamp": iso_now,
                "tags": [
                    "replay",
                    "proof",
                    f"glyph_count:{len(replay_entry.get('glyphs') or [])}",
                    f"tick:{t0}-{t1}",
                ],
                "plugin": "glyph_replay_renderer",
                "meta": {
                    "snapshot_id": snap,
                    "tick_start": t0,
                    "tick_end": t1,
                    "entangled_link_count": len(replay_entry.get("entangled_links") or []),
                },
            },
        }

        published = publish_kg_added(payload)
        if published:
            print("🧠 KG: proof_replay node published")
        else:
            print("🧠 KG: proof_replay node deduped (already published)")


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