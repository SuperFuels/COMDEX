"""
📦 In-memory GlyphWave carrier.
Used for local development, testing, and canary pipelines.
This implementation simulates a basic transmission buffer.

Replace with network/optical/quantum driver for production.
"""

from typing import Dict, Any, Optional, Deque
from collections import deque
from threading import Lock
from time import time

from .interfaces import IGlyphWaveCarrier


class MemoryCarrier(IGlyphWaveCarrier):
    """
    A memory-based carrier buffer for GWIP packets.
    Emulates a bounded transmission medium.
    """

    def __init__(self, capacity: int = 1024):
        self._q: Deque[Dict[str, Any]] = deque(maxlen=capacity)
        self._dropped = 0
        self._lock = Lock()
        self._capacity = capacity

    def emit(self, gwip: Dict[str, Any]) -> None:
        """Push a GWIP packet into the buffer."""
        with self._lock:
            if len(self._q) >= self._capacity:
                self._q.popleft()  # Drop oldest packet
                self._dropped += 1
            gwip.setdefault("envelope", {})["emitted_at"] = time()
            self._q.append(gwip)

    def capture(self) -> Optional[Dict[str, Any]]:
        """Pull the next available GWIP packet."""
        with self._lock:
            return self._q.popleft() if self._q else None

    def stats(self) -> Dict[str, Any]:
        """Report current buffer status."""
        with self._lock:
            return {
                "size": len(self._q),
                "capacity": self._capacity,
                "dropped": self._dropped,
            }

    def flush(self) -> None:
        """Clear the entire buffer."""
        with self._lock:
            self._q.clear()
            self._dropped = 0

    def close(self) -> None:
        """Shutdown the carrier (alias for flush)."""
        self.flush()