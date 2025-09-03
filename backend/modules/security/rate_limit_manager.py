# backend/modules/security/rate_limit_manager.py

import time
import threading
import redis
import hashlib
from typing import Dict

DEFAULT_LIMITS = {
    "guest": {"rate": 3, "burst": 5},
    "trusted": {"rate": 10, "burst": 15},
    "system": {"rate": 50, "burst": 100},
}

REDIS_URI = "redis://localhost:6379/2"
REDIS_PREFIX = "ratelimit:"

class RateLimitError(Exception):
    pass

class TokenBucket:
    def __init__(self, rate: int, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last = time.time()
        self.lock = threading.Lock()

    def allow(self) -> bool:
        with self.lock:
            now = time.time()
            delta = now - self.last
            self.last = now
            self.tokens = min(self.burst, self.tokens + delta * self.rate)
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False

class RateLimitManager:
    def __init__(self):
        try:
            self.redis = redis.Redis.from_url(REDIS_URI)
            self.redis.ping()
            self.use_redis = True
            print("✅ RateLimitManager using Redis backend")
        except Exception as e:
            print(f"⚠️ Redis unavailable, falling back to memory: {e}")
            self.use_redis = False
            self.buckets: Dict[str, TokenBucket] = {}

    def _get_key(self, sender_id: str) -> str:
        hashed = hashlib.sha256(sender_id.encode()).hexdigest()
        return REDIS_PREFIX + hashed

    def allow(self, sender_id: str, role: str = "guest") -> bool:
        limits = DEFAULT_LIMITS.get(role, DEFAULT_LIMITS["guest"])
        rate, burst = limits["rate"], limits["burst"]

        if self.use_redis:
            key = self._get_key(sender_id)
            now = time.time()
            pipeline = self.redis.pipeline()
            pipeline.hmget(key, "tokens", "last")
            result = pipeline.execute()[0]
            tokens = float(result[0]) if result[0] else burst
            last = float(result[1]) if result[1] else now
            delta = now - last
            tokens = min(burst, tokens + delta * rate)

            if tokens >= 1:
                tokens -= 1
                pipeline = self.redis.pipeline()
                pipeline.hmset(key, {"tokens": tokens, "last": now})
                pipeline.expire(key, 60)
                pipeline.execute()
                return True
            return False

        else:
            bucket = self.buckets.setdefault(sender_id, TokenBucket(rate, burst))
            return bucket.allow()

# Singleton instance
rate_limit_manager = RateLimitManager()