# File: backend/modules/sci/sci_crdt_sync_bridge.py

from typing import Dict, Any, Optional
import uuid
import time
import threading

class SessionCRDTState:
    """
    CRDT-compatible session state for collaborative field editing.
    """

    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.links: Dict[str, Dict[str, Any]] = {}
        self.glyphs: Dict[str, Dict[str, Any]] = {}
        self.scrolls: Dict[str, Dict[str, Any]] = {}
        self.version = 0
        self.lock = threading.Lock()

    def apply_update(self, update: Dict[str, Any]) -> bool:
        """
        Applies a remote update to the CRDT session state.
        Returns True if the update was accepted.
        """
        with self.lock:
            try:
                update_type = update["type"]
                payload = update["payload"]
                item_id = payload.get("id", str(uuid.uuid4()))

                if update_type == "node":
                    self.nodes[item_id] = payload
                elif update_type == "link":
                    self.links[item_id] = payload
                elif update_type == "glyph":
                    self.glyphs[item_id] = payload
                elif update_type == "scroll":
                    self.scrolls[item_id] = payload
                else:
                    return False

                self.version += 1
                return True
            except Exception as e:
                print(f"❌ CRDT update failed: {e}")
                return False

    def get_state(self) -> Dict[str, Any]:
        """
        Returns a snapshot of the current state.
        """
        with self.lock:
            return {
                "nodes": list(self.nodes.values()),
                "links": list(self.links.values()),
                "glyphs": list(self.glyphs.values()),
                "scrolls": list(self.scrolls.values()),
                "version": self.version,
                "timestamp": time.time(),
            }