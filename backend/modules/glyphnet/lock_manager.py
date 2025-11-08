from __future__ import annotations
import time
from typing import Dict, Optional, Callable

class LockManager:
    """
    In-memory floor control for half-duplex voice.
    resource -> { owner: str, until: float }
    """
    def __init__(self):
        self._locks: Dict[str, Dict[str, float]] = {}  # {"resource": {"owner": str, "until": epoch_sec}}
        self._on_change: Optional[Callable[[str, dict], None]] = None  # callback(topic, event)

    def set_callback(self, fn: Callable[[str, dict], None]):
        self._on_change = fn

    def _emit(self, topic: str, ev: dict):
        if self._on_change:
            try:
                self._on_change(topic, ev)
            except Exception:
                pass

    def _prune(self, now: Optional[float] = None):
        now = now or time.time()
        for res, row in list(self._locks.items()):
            if row.get("until", 0) <= now:
                self._locks.pop(res, None)

    def get(self, resource: str) -> Optional[dict]:
        row = self._locks.get(resource)
        if not row:
            return None
        return {"owner": row["owner"], "until": row["until"]}

    def apply(self, *, topic: str, op: str, resource: str, owner: str, ttl_ms: int = 3500) -> dict:
        """
        Normalized lock event:
        {
          "type": "entanglement_lock",
          "resource": "voice:<ucs://...>",
          "state": "held" | "free",
          "owner": "<id>",
          "until": <epoch_sec_optional>,
          "granted": true | false
        }
        """
        now = time.time()
        self._prune(now)
        ent = self._locks.get(resource)

        if op in ("acquire", "refresh"):
            # deny if another owner still holds it
            if ent and ent.get("until", 0) > now and ent.get("owner") != owner:
                ev = {
                    "type": "entanglement_lock",
                    "resource": resource,
                    "state": "held",
                    "owner": ent["owner"],
                    "until": ent["until"],
                    "granted": False,
                }
                self._emit(topic, ev)
                return ev

            # grant/extend to this owner
            until = now + (ttl_ms / 1000.0)
            self._locks[resource] = {"owner": owner, "until": until}
            ev = {
                "type": "entanglement_lock",
                "resource": resource,
                "state": "held",
                "owner": owner,
                "until": until,
                "granted": True,
            }
            self._emit(topic, ev)
            return ev

        if op == "release":
            if ent and ent.get("owner") == owner:
                self._locks.pop(resource, None)
                ev = {
                    "type": "entanglement_lock",
                    "resource": resource,
                    "state": "free",
                    "owner": owner,
                    "granted": True,
                }
            else:
                ev = {
                    "type": "entanglement_lock",
                    "resource": resource,
                    "state": "free",
                    "owner": (ent.get("owner") if ent else owner) if ent else owner,
                    "granted": False,
                }
            self._emit(topic, ev)
            return ev

        # unknown op -> echo a deny/free
        ev = {
            "type": "entanglement_lock",
            "resource": resource,
            "state": "free",
            "owner": (ent.get("owner") if ent else owner) if ent else owner,
            "granted": False,
        }
        self._emit(topic, ev)
        return ev

    def sweep(self):
        now = time.time()
        freed = []
        for res, row in list(self._locks.items()):
            if row.get("until", 0) <= now:   # ← was "expires_at"
                freed.append((res, row.get("owner")))
                del self._locks[res]
        return freed

LOCKS = LockManager()