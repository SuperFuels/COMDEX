# File: backend/modules/glyphwave/performance/interference_cache.py

import time
from collections import OrderedDict
from typing import Tuple, Any, Dict

class InterferenceCache:
    """
    Memoization cache for repeated symbolic wave interference results.
    """

    def __init__(self, max_size: int = 5000, ttl: float = 10.0):
        self.cache: OrderedDict[Tuple[str, str], Tuple[Any, float]] = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl  # seconds

    def _normalize_key(self, id1: str, id2: str) -> Tuple[str, str]:
        return tuple(sorted([id1, id2]))

    def get(self, id1: str, id2: str) -> Any:
        key = self._normalize_key(id1, id2)
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                self.cache.move_to_end(key)  # Refresh LRU order
                return result
            else:
                del self.cache[key]  # Expired
        return None

    def set(self, id1: str, id2: str, result: Any):
        key = self._normalize_key(id1, id2)
        self.cache[key] = (result, time.time())
        self.cache.move_to_end(key)
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)  # Evict LRU

    def clear(self):
        self.cache.clear()

    def stats(self) -> Dict[str, int]:
        return {
            "entries": len(self.cache),
            "max_size": self.max_size,
        }