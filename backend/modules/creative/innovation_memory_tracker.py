import time
import json
import os
import logging
from typing import Dict, Any, Optional, List
from threading import Lock
from fastapi.websockets import WebSocket
from datetime import datetime, timezone

INNOVATION_HISTORY_LIMIT = 1000
MEMORY_SAVE_PATH = "data/innovation_history/innovation_log.jsonl"

# WebSocket clients for live broadcast
WEBSOCKET_CLIENTS: List[WebSocket] = []

logger = logging.getLogger("innovation_tracker")


def _utc_now() -> str:
    # RFC 3339 / ISO 8601, timezone-aware
    return datetime.now(timezone.utc).isoformat()


def _wid(wave: Any) -> Optional[str]:
    """Best-effort wave identifier (wave_id preferred; then id)."""
    return getattr(wave, "wave_id", getattr(wave, "id", None))


def _safe_broadcast_global(tag: str, payload: Dict[str, Any]) -> None:
    """
    Fire-and-forget global WS broadcast through websocket_manager if available.
    Keeps original per-client streaming intact; this is additive and safe.
    """
    try:
        from backend.modules.websocket_manager import broadcast_event
    except Exception:
        return
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(broadcast_event(tag, payload))
        else:
            loop.run_until_complete(broadcast_event(tag, payload))
    except Exception:
        # Never break callers on telemetry
        pass


class InnovationMemoryTracker:
    """
    Tracks symbolic innovations, mutations, and fork scoring over time.
    Provides high-resolution symbolic replay support for SQI, GHX, and Drift HUDs.
    Broadcasts innovation events to HUD overlays.
    """

    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.lock = Lock()
        self._load_memory()

    def log_event(
        self,
        container_id: str,
        beam_id: str,
        mutation_cause: Optional[str],
        innovation_scores: Dict[str, float],
        symbolic_snapshot: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Log a new innovation event into memory, disk, and HUD overlays.
        """
        timestamp = _utc_now()
        event: Dict[str, Any] = {
            "timestamp": timestamp,
            "container_id": container_id,
            "beam_id": beam_id,
            "mutation_cause": mutation_cause,
            "scores": innovation_scores or {},
            "metadata": metadata or {},
        }

        if symbolic_snapshot:
            event["snapshot"] = symbolic_snapshot

        with self.lock:
            self.history.append(event)
            if len(self.history) > INNOVATION_HISTORY_LIMIT:
                self.history.pop(0)

        self._save_event_to_disk(event)
        self._broadcast_to_websockets(event)
        # Also broadcast globally (non-breaking, optional)
        _safe_broadcast_global("innovation.event", {"type": "innovation_event", "payload": event})

        logger.info(
            "🧠 Innovation Event | container=%s cause=%s score=%.4f",
            container_id,
            mutation_cause,
            event["scores"].get("innovation_score", 0.0),
        )

    def get_top_innovations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Return top N most innovative mutations by `innovation_score`.
        """
        with self.lock:
            sorted_events = sorted(
                self.history,
                key=lambda e: e["scores"].get("innovation_score", 0.0),
                reverse=True
            )
            return sorted_events[:limit]

    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self.lock:
            return self.history[-limit:]

    def attach_websocket(self, client: WebSocket):
        """
        Attach a live WebSocket client to stream innovation events.
        """
        WEBSOCKET_CLIENTS.append(client)

    def detach_websocket(self, client: WebSocket):
        """
        Detach a WebSocket client.
        """
        try:
            WEBSOCKET_CLIENTS.remove(client)
        except ValueError:
            pass

    def _broadcast_to_websockets(self, event: Dict[str, Any]):
        for client in WEBSOCKET_CLIENTS:
            try:
                if client.client_state.name == "CONNECTED":
                    import asyncio
                    asyncio.create_task(client.send_json({
                        "type": "innovation_event",
                        "payload": event
                    }))
            except Exception as e:
                logger.debug(f"WebSocket broadcast failed: {e}")

    def _save_event_to_disk(self, event: Dict[str, Any]):
        """
        Save single innovation event to persistent disk log.
        """
        try:
            os.makedirs(os.path.dirname(MEMORY_SAVE_PATH), exist_ok=True)
            with open(MEMORY_SAVE_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.warning(f"⚠️ Failed to write innovation event to disk: {e}")

    def _load_memory(self):
        """
        Load recent innovation log history from disk.
        """
        if not os.path.exists(MEMORY_SAVE_PATH):
            return

        try:
            with open(MEMORY_SAVE_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()[-INNOVATION_HISTORY_LIMIT:]
                for line in lines:
                    try:
                        self.history.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning(f"⚠️ Failed to load innovation history: {e}")


# Global singleton for use
INNOVATION_TRACKER = InnovationMemoryTracker()


# -----------------------------------------------------------------------------
# Backward-compatible log_event wrapper
# - Supports your original structured signature, AND dict-style calls.
#   creative_core.py uses: log_event({...})
# -----------------------------------------------------------------------------
def log_event(
    *args,
    **kwargs,
):
    """
    Compatible wrapper:
      1) dict-style: log_event({"wave_id": ..., "parent_wave_id": ..., "score": ..., "container_id": ...})
      2) structured: log_event(container_id, beam_id, mutation_cause, innovation_scores, symbolic_snapshot=None, metadata=None)
    """
    # Case 1: dict-only usage
    if args and isinstance(args[0], dict) and not kwargs:
        evt = dict(args[0])  # shallow copy
        # Normalize fields for tracker API
        container_id = evt.get("container_id") or evt.get("workspace_id") or "unknown"
        beam_id = evt.get("wave_id") or evt.get("beam_id") or evt.get("id") or "unknown"
        mutation_cause = evt.get("mutation_cause") or evt.get("cause")
        if "scores" in evt and isinstance(evt["scores"], dict):
            scores = evt["scores"]
        else:
            score_val = evt.get("score")
            scores = {"innovation_score": float(score_val)} if score_val is not None else {}
        snapshot = (
            evt.get("snapshot")
            or evt.get("symbolic_snapshot")
            or evt.get("symbolic_tree")
        )

        # Preserve all extra keys into metadata to avoid losing information
        reserved = {
            "container_id", "workspace_id", "wave_id", "beam_id", "id",
            "mutation_cause", "cause", "scores", "score",
            "snapshot", "symbolic_snapshot", "symbolic_tree",
            "timestamp", "type",
        }
        extra_meta = {k: v for k, v in evt.items() if k not in reserved}

        INNOVATION_TRACKER.log_event(
            container_id=container_id,
            beam_id=beam_id,
            mutation_cause=mutation_cause,
            innovation_scores=scores,
            symbolic_snapshot=snapshot,
            metadata=extra_meta,
        )
        return

    # Case 2: structured signature (original behavior)
    # Expect: (container_id, beam_id, mutation_cause, innovation_scores, symbolic_snapshot=None, metadata=None)
    container_id = args[0] if len(args) > 0 else kwargs.get("container_id")
    beam_id = args[1] if len(args) > 1 else kwargs.get("beam_id")
    mutation_cause = args[2] if len(args) > 2 else kwargs.get("mutation_cause")
    innovation_scores = args[3] if len(args) > 3 else kwargs.get("innovation_scores")
    symbolic_snapshot = args[4] if len(args) > 4 else kwargs.get("symbolic_snapshot")
    metadata = args[5] if len(args) > 5 else kwargs.get("metadata")

    INNOVATION_TRACKER.log_event(
        container_id=container_id,
        beam_id=beam_id,
        mutation_cause=mutation_cause,
        innovation_scores=innovation_scores,
        symbolic_snapshot=symbolic_snapshot,
        metadata=metadata,
    )


def get_recent_events(limit: int = 20) -> List[Dict[str, Any]]:
    return INNOVATION_TRACKER.get_recent_events(limit=limit)


def get_top_innovations(limit: int = 10) -> List[Dict[str, Any]]:
    return INNOVATION_TRACKER.get_top_innovations(limit=limit)


def attach_websocket(client: WebSocket):
    INNOVATION_TRACKER.attach_websocket(client)


def detach_websocket(client: WebSocket):
    INNOVATION_TRACKER.detach_websocket(client)


# -----------------------------------------------------------------------------
# New helper used by creative_core.emit_creative_fork
# -----------------------------------------------------------------------------
def track_innovation(
    parent_wave: Any,
    fork_wave: Any,
    score: float,
    cause: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record a parent->fork lineage with innovation metrics.
    Compatible with creative_core.py expectations.
    """
    container_id = getattr(fork_wave, "container_id", None) or getattr(parent_wave, "container_id", None) or "unknown"
    record: Dict[str, Any] = {
        "type": "innovation_track",
        "timestamp": _utc_now(),
        "container_id": container_id,
        "parent_wave_id": _wid(parent_wave),
        "wave_id": _wid(fork_wave),
        "score": float(score) if score is not None else None,
        "glow": getattr(fork_wave, "glow_intensity", None),
        "pulse": getattr(fork_wave, "pulse_frequency", None),
        "mutation_cause": cause or getattr(fork_wave, "mutation_cause", None),
    }

    # Use the flexible log_event(dict) path
    log_event(record)
    return record