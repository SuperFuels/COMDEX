from __future__ import annotations

import threading
import time
from typing import Dict, Tuple

_LOCK = threading.Lock()

# peer_key -> (msg_tokens, byte_tokens, last_ts)
_BUCKETS: Dict[str, Tuple[float, float, float]] = {}


def allow(
    peer_key: str,
    *,
    cost_msgs: float = 1.0,
    cost_bytes: float = 0.0,
    msg_rate_per_sec: float = 20.0,
    msg_burst: float = 40.0,
    bytes_rate_per_sec: float = 512_000.0,   # 512KB/s default
    bytes_burst: float = 1_048_576.0,        # 1MB burst default
) -> bool:
    """
    Tiny dual token bucket (msgs + bytes). Good enough for dev.

    Uses ONE shared timestamp for both buckets to keep it simple and stable.

    - cost_msgs: usually 1 per request
    - cost_bytes: approximate payload size in bytes
    """
    now = time.time()
    k = (peer_key or "unknown").strip() or "unknown"

    with _LOCK:
        msg_tokens, byte_tokens, last = _BUCKETS.get(k, (msg_burst, bytes_burst, now))
        dt = max(0.0, now - last)

        # refill
        msg_tokens = min(msg_burst, msg_tokens + dt * msg_rate_per_sec)
        byte_tokens = min(bytes_burst, byte_tokens + dt * bytes_rate_per_sec)

        # check capacity
        if msg_tokens < cost_msgs or byte_tokens < cost_bytes:
            _BUCKETS[k] = (msg_tokens, byte_tokens, now)
            return False

        # spend
        msg_tokens -= cost_msgs
        byte_tokens -= cost_bytes
        _BUCKETS[k] = (msg_tokens, byte_tokens, now)
        return True