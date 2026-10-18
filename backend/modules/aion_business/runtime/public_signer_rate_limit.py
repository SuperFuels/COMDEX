"""Bounded in-process abuse control for the public Legal signer surface."""

from __future__ import annotations

from collections import OrderedDict, deque
from hashlib import sha256
import threading
import time
from typing import Callable


class PublicSignerRateLimiter:
    """Limit work per network source and opaque signing token.

    The table is LRU bounded so attempts cannot turn the rate limiter itself
    into an unbounded-memory target.  Only hashes of tokens are retained.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        window_seconds: int = 60,
        read_per_source: int = 60,
        write_per_source: int = 20,
        read_per_token: int = 20,
        write_per_token: int = 8,
        max_buckets: int = 10_000,
    ) -> None:
        self.clock = clock
        self.window_seconds = max(1, min(int(window_seconds), 3600))
        self.read_per_source = max(1, min(int(read_per_source), 10_000))
        self.write_per_source = max(1, min(int(write_per_source), 10_000))
        self.read_per_token = max(1, min(int(read_per_token), 10_000))
        self.write_per_token = max(1, min(int(write_per_token), 10_000))
        self.max_buckets = max(256, min(int(max_buckets), 100_000))
        self._buckets: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    def allow(self, *, source: str, token: str, write: bool) -> tuple[bool, int]:
        now = float(self.clock())
        token_digest = sha256(str(token).encode("utf-8")).hexdigest()
        kind = "write" if write else "read"
        limits = (
            (f"source:{kind}:{str(source or 'unknown')[:240]}", self.write_per_source if write else self.read_per_source),
            (f"token:{kind}:{token_digest}", self.write_per_token if write else self.read_per_token),
        )
        with self._lock:
            retry_after = 1
            for key, limit in limits:
                bucket = self._bucket(key)
                self._prune(bucket, now)
                if len(bucket) >= limit:
                    retry_after = max(
                        retry_after,
                        int(max(1.0, self.window_seconds - (now - bucket[0]))),
                    )
                    return False, retry_after
            for key, _ in limits:
                self._buckets[key].append(now)
                self._buckets.move_to_end(key)
            return True, 0

    def _bucket(self, key: str) -> deque[float]:
        bucket = self._buckets.get(key)
        if bucket is None:
            while len(self._buckets) >= self.max_buckets:
                self._buckets.popitem(last=False)
            bucket = deque()
            self._buckets[key] = bucket
        self._buckets.move_to_end(key)
        return bucket

    def _prune(self, bucket: deque[float], now: float) -> None:
        threshold = now - self.window_seconds
        while bucket and bucket[0] <= threshold:
            bucket.popleft()

    @property
    def bucket_count(self) -> int:
        with self._lock:
            return len(self._buckets)
