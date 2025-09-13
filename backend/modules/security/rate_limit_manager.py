# File: backend/modules/security/rate_limit_manager.py
from __future__ import annotations

import os
import time
import threading
import hashlib
from typing import Dict, Tuple, Optional

try:
    import redis  # type: ignore
except Exception:
    redis = None  # type: ignore

# ------------------------- Config / Defaults -------------------------

DEFAULT_LIMITS: Dict[str, Dict[str, int]] = {
    "guest":   {"rate": 3,  "burst": 5},
    "trusted": {"rate": 10, "burst": 15},
    "system":  {"rate": 50, "burst": 100},
}

# Allow env overrides but keep your old defaults
REDIS_URI = os.getenv("REDIS_URL", "redis://localhost:6379/2")
REDIS_PREFIX = os.getenv("RATE_LIMIT_PREFIX", "ratelimit:")

# Set RATE_LIMIT_BACKEND=memory to force memory mode
FORCE_BACKEND = os.getenv("RATE_LIMIT_BACKEND", "").strip().lower()

# --------------------------- Exceptions -----------------------------

class RateLimitError(Exception):
    """Raised when a rate limit is exceeded."""
    pass

# ----------------------- In-memory TokenBucket ----------------------

class TokenBucket:
    """
    Fixed-window-ish token bucket with continuous refill.
    Thread-safe; suitable for tests/dev or single-process.
    """
    def __init__(self, rate: int, burst: int):
        self.rate = float(rate)
        self.burst = float(burst)
        self.tokens = float(burst)
        self.last = time.time()
        self.lock = threading.Lock()

    def _refill(self, now: Optional[float] = None) -> float:
        if now is None:
            now = time.time()
        delta = now - self.last
        if delta > 0:
            self.tokens = min(self.burst, self.tokens + delta * self.rate)
            self.last = now
        return self.tokens

    def allow(self) -> bool:
        with self.lock:
            self._refill()
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False

    def peek(self) -> Tuple[int, int]:
        """
        Non-mutating view: (remaining_tokens_int, seconds_until_reset_one_token)
        """
        with self.lock:
            now = time.time()
            # simulate refill without writing
            delta = now - self.last
            tokens = min(self.burst, self.tokens + delta * self.rate)
            remaining = int(tokens) if tokens >= 0 else 0
            reset_in = 0 if tokens >= 1.0 else max(0, int((1.0 - tokens) / self.rate))
            return remaining, reset_in

# ---------------------------- Manager -------------------------------

class RateLimitManager:
    """
    Facade using Redis if available/reachable, otherwise in-memory.
    Preserves original behavior and key hashing; adds get_remaining/enforce.
    """
    def __init__(self):
        self.use_redis = False
        self._buckets: Dict[str, TokenBucket] = {}

        if FORCE_BACKEND == "memory":
            print("🟡 RateLimitManager: forced memory backend (RATE_LIMIT_BACKEND=memory).")
            return

        if redis is None:
            print("🟡 RateLimitManager: redis package not installed; using memory backend.")
            return

        try:
            self.redis = redis.Redis.from_url(REDIS_URI, decode_responses=True)
            self.redis.ping()
            self.use_redis = True
            print("✅ RateLimitManager using Redis backend")
        except Exception as e:
            print(f"⚠️ Redis unavailable, falling back to memory: {e}")
            self.use_redis = False

    # ----------------------- Helpers -----------------------

    def _limits_for_role(self, role: str) -> Tuple[int, int]:
        limits = DEFAULT_LIMITS.get(role, DEFAULT_LIMITS["guest"])
        return int(limits["rate"]), int(limits["burst"])

    def _key(self, sender_id: str) -> str:
        hashed = hashlib.sha256(sender_id.encode("utf-8")).hexdigest()
        return f"{REDIS_PREFIX}{hashed}"

    # ------------------- Public Interface -------------------

    def allow(self, sender_id: str, role: str = "guest") -> bool:
        rate, burst = self._limits_for_role(role)

        if self.use_redis:
            key = self._key(sender_id)
            now = time.time()

            try:
                # Read current state
                tokens_str, last_str = self.redis.hmget(key, "tokens", "last")
                tokens = float(tokens_str) if tokens_str is not None else float(burst)
                last = float(last_str) if last_str is not None else now

                # Refill
                delta = max(0.0, now - last)
                tokens = min(float(burst), tokens + delta * float(rate))

                if tokens >= 1.0:
                    tokens -= 1.0
                    # Persist new state + TTL; (hmset deprecated → hset(mapping=...))
                    pipe = self.redis.pipeline()
                    pipe.hset(key, mapping={"tokens": tokens, "last": now})
                    pipe.expire(key, 60)
                    pipe.execute()
                    return True

                # (Preserve your original semantics: don't write back on deny)
                return False

            except Exception:
                # On any Redis error, don't block requests: allow (or choose to deny)
                return True

        # Memory backend
        bucket = self._buckets.setdefault(sender_id, TokenBucket(rate, burst))
        return bucket.allow()

    def get_remaining(self, sender_id: str, role: str = "guest") -> Tuple[int, int]:
        """
        Returns (remaining, reset_in_seconds) best-effort.
        """
        rate, burst = self._limits_for_role(role)

        if self.use_redis:
            key = self._key(sender_id)
            now = time.time()
            try:
                tokens_str, last_str = self.redis.hmget(key, "tokens", "last")
                tokens = float(tokens_str) if tokens_str is not None else float(burst)
                last = float(last_str) if last_str is not None else now
                delta = max(0.0, now - last)
                tokens = min(float(burst), tokens + delta * float(rate))
                remaining = int(tokens) if tokens >= 0 else 0
                reset_in = 0 if tokens >= 1.0 else max(0, int((1.0 - tokens) / float(rate)))

                # Optional: TTL snapshot (not strictly the refill reset)
                try:
                    ttl = self.redis.ttl(key)
                    if isinstance(ttl, int) and ttl >= 0:
                        # choose the smaller informative reset
                        reset_in = min(reset_in, ttl) if reset_in else ttl
                except Exception:
                    pass

                return remaining, reset_in
            except Exception:
                # If Redis hiccups, provide a safe default
                return max(0, burst - 1), 1

        # Memory backend
        bucket = self._buckets.setdefault(sender_id, TokenBucket(rate, burst))
        return bucket.peek()

    def enforce(self, sender_id: str, role: str = "guest") -> None:
        """Raise RateLimitError if not allowed."""
        if not self.allow(sender_id, role=role):
            rate, burst = self._limits_for_role(role)
            raise RateLimitError(f"Rate limit exceeded for {sender_id} ({burst} burst @ {rate}/s)")

# ------------------------- Singleton export -------------------------

rate_limit_manager = RateLimitManager()