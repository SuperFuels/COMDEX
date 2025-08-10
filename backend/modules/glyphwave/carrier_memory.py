"""
In-memory carrier for dev/canary. Replace with network/optical driver later.
"""
from typing import Dict, Any, Optional, Deque
from collections import deque
from .interfaces import IGlyphWaveCarrier

class MemoryCarrier(IGlyphWaveCarrier):
    def __init__(self, capacity: int = 1024):
        self._q: Deque[Dict[str, Any]] = deque(maxlen=capacity)
        self._dropped = 0

    def emit(self, gwip: Dict[str, Any]) -> None:
        if len(self._q) == self._q.maxlen:
            self._q.popleft()
            self._dropped += 1
        self._q.append(gwip)

    def capture(self) -> Optional[Dict[str, Any]]:
        return self._q.popleft() if self._q else None

    def stats(self) -> Dict[str, Any]:
        return {"size": len(self._q), "capacity": self._q.maxlen, "dropped": self._dropped}

    def close(self) -> None:
        self._q.clear()