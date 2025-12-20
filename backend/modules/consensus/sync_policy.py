# backend/modules/consensus/sync_policy.py
from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except Exception:
        return int(default)


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
        self.base_ms = _env_int("P2P_SYNC_BACKOFF_BASE_MS", 200)      # initial backoff
        self.max_ms = _env_int("P2P_SYNC_BACKOFF_MAX_MS", 5000)       # cap
        self.jitter_pct = _env_int("P2P_SYNC_BACKOFF_JITTER_PCT", 20) # +/- %

        # Per-peer lane rate bound
        self.min_spacing_ms = _env_int("P2P_SYNC_LANE_MIN_SPACING_MS", 75)

        # Per-peer inflight cap (per lane)
        self.max_inflight = _env_int("P2P_SYNC_LANE_MAX_INFLIGHT", 1)

        self._lock = Lock()
        self._st: Dict[str, _LanePeerState] = {}

    def _key(self, peer_key: str, lane: str) -> str:
        return f"{lane}|{peer_key}"

    def allow(self, peer_key: str, lane: str) -> bool:
        now = _now_ms()
        k = self._key(peer_key, lane)
        with self._lock:
            st = self._st.get(k) or _LanePeerState()
            self._st[k] = st

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
            st = self._st.get(k) or _LanePeerState()
            st.last_attempt_ms = now
            st.inflight += 1
            self._st[k] = st

    def on_success(self, peer_key: str, lane: str) -> None:
        k = self._key(peer_key, lane)
        with self._lock:
            st = self._st.get(k) or _LanePeerState()
            st.fails = 0
            st.next_ok_ms = 0
            st.last_err = ""
            st.inflight = max(0, st.inflight - 1)
            self._st[k] = st

    def on_failure(self, peer_key: str, lane: str, err: str = "") -> int:
        """
        Returns backoff_ms applied.
        """
        now = _now_ms()
        k = self._key(peer_key, lane)

        with self._lock:
            st = self._st.get(k) or _LanePeerState()
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
            self._st[k] = st

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