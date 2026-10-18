# backend/modules/consensus/sync_policy.py
from __future__ import annotations

import os
import random
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except Exception:
        return int(default)


def _bounded_env(name: str, default: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(_env_int(name, default), maximum))


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class _LanePeerState:
    # backoff
    fails: int = 0
    next_ok_ms: int = 0
    last_err: str = ""
    # rate limiting
    last_attempt_ms: int = 0
    # inflight cap
    inflight: int = 0


class SyncPolicy:
    """
    Per-peer + per-lane:
      - min spacing (rate bound)
      - inflight cap
      - exponential backoff with jitter on failure
      - success clears failures + allows immediate reuse
    """

    def __init__(self) -> None:
        # Backoff knobs
        self.base_ms = _bounded_env("P2P_SYNC_BACKOFF_BASE_MS", 200, 0, 60_000)
        self.max_ms = _bounded_env("P2P_SYNC_BACKOFF_MAX_MS", 5000, self.base_ms, 600_000)
        self.jitter_pct = _bounded_env("P2P_SYNC_BACKOFF_JITTER_PCT", 20, 0, 100)

        # Per-peer lane rate bound
        self.min_spacing_ms = _bounded_env("P2P_SYNC_LANE_MIN_SPACING_MS", 75, 0, 60_000)

        # Per-peer inflight cap (per lane)
        self.max_inflight = _bounded_env("P2P_SYNC_LANE_MAX_INFLIGHT", 1, 1, 64)
        self.max_states = _bounded_env("P2P_SYNC_POLICY_MAX_STATES", 10_000, 256, 100_000)

        self._lock = Lock()
        self._st: OrderedDict[str, _LanePeerState] = OrderedDict()

    def _state(self, key: str, *, create: bool) -> _LanePeerState | None:
        value = self._st.get(key)
        if value is not None:
            self._st.move_to_end(key)
            return value
        if not create:
            return None
        while len(self._st) >= self.max_states:
            evict = next((name for name, item in self._st.items() if item.inflight <= 0), None)
            if evict is None:
                return None
            self._st.pop(evict, None)
        value = _LanePeerState()
        self._st[key] = value
        return value

    def _key(self, peer_key: str, lane: str) -> str:
        return f"{lane}|{peer_key}"

    def allow(self, peer_key: str, lane: str) -> bool:
        now = _now_ms()
        k = self._key(peer_key, lane)
        with self._lock:
            st = self._state(k, create=True)
            if st is None:
                return False

            if st.inflight >= self.max_inflight:
                return False
            if now < st.next_ok_ms:
                return False
            if (now - st.last_attempt_ms) < self.min_spacing_ms:
                return False
            return True

    def on_attempt(self, peer_key: str, lane: str) -> None:
        now = _now_ms()
        k = self._key(peer_key, lane)
        with self._lock:
            st = self._state(k, create=True)
            if st is None:
                return
            st.last_attempt_ms = now
            st.inflight += 1
            self._st.move_to_end(k)

    def on_success(self, peer_key: str, lane: str) -> None:
        k = self._key(peer_key, lane)
        with self._lock:
            st = self._state(k, create=False)
            if st is None:
                return
            st.fails = 0
            st.next_ok_ms = 0
            st.last_err = ""
            st.inflight = max(0, st.inflight - 1)
            self._st.move_to_end(k)

    def on_failure(self, peer_key: str, lane: str, err: str = "") -> int:
        """
        Returns backoff_ms applied.
        """
        now = _now_ms()
        k = self._key(peer_key, lane)

        with self._lock:
            st = self._state(k, create=False)
            if st is None:
                return 0
            st.fails += 1
            st.last_err = (err or "")[:400]

            backoff = int(self.base_ms * (2 ** max(0, st.fails - 1)))
            backoff = min(backoff, self.max_ms)

            # jitter: +/- jitter_pct
            j = max(0, int(self.jitter_pct))
            if j > 0:
                delta = int(backoff * (j / 100.0))
                backoff = backoff + random.randint(-delta, delta)

            st.next_ok_ms = now + max(0, int(backoff))
            st.inflight = max(0, st.inflight - 1)
            self._st.move_to_end(k)

            return max(0, int(backoff))

    def debug_state(self, peer_key: str, lane: str) -> Optional[dict]:
        k = self._key(peer_key, lane)
        with self._lock:
            st = self._st.get(k)
            if not st:
                return None
            return {
                "fails": st.fails,
                "next_ok_ms": st.next_ok_ms,
                "last_attempt_ms": st.last_attempt_ms,
                "inflight": st.inflight,
                "last_err": st.last_err,
            }
