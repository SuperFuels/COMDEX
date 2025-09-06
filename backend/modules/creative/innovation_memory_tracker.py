import time
import json
import os
import logging
from typing import Dict, Any, Optional, List
from threading import Lock
from fastapi.websockets import WebSocket
from datetime import datetime

INNOVATION_HISTORY_LIMIT = 1000
MEMORY_SAVE_PATH = "data/innovation_history/innovation_log.jsonl"

# WebSocket clients for live broadcast
WEBSOCKET_CLIENTS: List[WebSocket] = []

logger = logging.getLogger("innovation_tracker")

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
        timestamp = datetime.utcnow().isoformat()
        event = {
            "timestamp": timestamp,
            "container_id": container_id,
            "beam_id": beam_id,
            "mutation_cause": mutation_cause,
            "scores": innovation_scores,
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

        logger.info(f"🧠 Innovation Event | container={container_id} cause={mutation_cause} score={innovation_scores.get('innovation_score', 0.0):.4f}")

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

def log_event(
    container_id: str,
    beam_id: str,
    mutation_cause: Optional[str],
    innovation_scores: Dict[str, float],
    symbolic_snapshot: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
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