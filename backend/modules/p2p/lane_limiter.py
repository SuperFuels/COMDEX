# backend/modules/p2p/lane_limiter.py
from __future__ import annotations

import asyncio
import os
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple


def _now_ms() -> float:
    return float(time.time() * 1000.0)


@dataclass
class LaneCfg:
    name: str
    max_inflight: int
    max_queue: int
    drop_policy: str  # "drop_new" | "drop_old"
    dup_lru: int
    yield_every: int


class _LRU:
    def __init__(self, cap: int) -> None:
        self.cap = max(0, int(cap))
        self._d: "OrderedDict[str, None]" = OrderedDict()

    def seen(self, k: str) -> bool:
        if self.cap <= 0:
            return False
        kk = str(k or "")
        if not kk:
            return False
        if kk in self._d:
            # refresh
            self._d.move_to_end(kk, last=True)
            return True
        self._d[kk] = None
        if len(self._d) > self.cap:
            self._d.popitem(last=False)
        return False


class LaneLimiter:
    """
    PR5 ingress hardening:
      - per-lane bounded queue + inflight semaphore
      - drop_new or drop_old
      - dup LRU per lane (drop early)
      - counters: enqueued, dropped_full, dropped_dup, processed
    """

    def __init__(self, cfgs: Dict[str, LaneCfg]) -> None:
        self._cfgs = dict(cfgs)
        self._qs: Dict[str, asyncio.Queue[Tuple[str, Callable[[], Awaitable[Any]]]]] = {}
        self._sem: Dict[str, asyncio.Semaphore] = {}
        self._lru: Dict[str, _LRU] = {}

        self._workers_started = False
        self._workers_lock = asyncio.Lock()

        self._counters: Dict[str, Dict[str, int]] = {}
        self._last_ok_ms: Dict[str, float] = {}

        for lane, cfg in self._cfgs.items():
            self._qs[lane] = asyncio.Queue(maxsize=max(1, int(cfg.max_queue)))
            self._sem[lane] = asyncio.Semaphore(max(1, int(cfg.max_inflight)))
            self._lru[lane] = _LRU(int(cfg.dup_lru))
            self._counters[lane] = {
                "enqueued": 0,
                "dropped_full": 0,
                "dropped_dup": 0,
                "processed": 0,
            }
            self._last_ok_ms[lane] = 0.0

    @staticmethod
    def from_env() -> "LaneLimiter":
        """
        Tweak via env vars (sane defaults):
          P2P_LANE_MAX_QUEUE_PROPOSAL, _VOTE, _SYNC, _BLOCK
          P2P_LANE_MAX_INFLIGHT_PROPOSAL, ...
          P2P_LANE_DUP_LRU_PROPOSAL, ...
          P2P_LANE_DROP_POLICY (drop_new|drop_old) default drop_new
        """
        dp = (os.getenv("P2P_LANE_DROP_POLICY", "") or "drop_new").strip().lower()
        if dp not in ("drop_new", "drop_old"):
            dp = "drop_new"

        def gi(name: str, default: int) -> int:
            try:
                return int(os.getenv(name, str(default)) or str(default))
            except Exception:
                return int(default)

        cfgs = {
            "proposal": LaneCfg(
                name="proposal",
                max_inflight=gi("P2P_LANE_MAX_INFLIGHT_PROPOSAL", 2),
                max_queue=gi("P2P_LANE_MAX_QUEUE_PROPOSAL", 256),
                drop_policy=dp,
                dup_lru=gi("P2P_LANE_DUP_LRU_PROPOSAL", 2048),
                yield_every=gi("P2P_LANE_YIELD_EVERY_PROPOSAL", 64),
            ),
            "vote": LaneCfg(
                name="vote",
                max_inflight=gi("P2P_LANE_MAX_INFLIGHT_VOTE", 4),
                max_queue=gi("P2P_LANE_MAX_QUEUE_VOTE", 2048),
                drop_policy=dp,
                dup_lru=gi("P2P_LANE_DUP_LRU_VOTE", 8192),
                yield_every=gi("P2P_LANE_YIELD_EVERY_VOTE", 256),
            ),
            "sync": LaneCfg(
                name="sync",
                max_inflight=gi("P2P_LANE_MAX_INFLIGHT_SYNC", 1),
                max_queue=gi("P2P_LANE_MAX_QUEUE_SYNC", 64),
                drop_policy=dp,
                dup_lru=gi("P2P_LANE_DUP_LRU_SYNC", 256),
                yield_every=gi("P2P_LANE_YIELD_EVERY_SYNC", 32),
            ),
            "block": LaneCfg(
                name="block",
                max_inflight=gi("P2P_LANE_MAX_INFLIGHT_BLOCK", 2),
                max_queue=gi("P2P_LANE_MAX_QUEUE_BLOCK", 256),
                drop_policy=dp,
                dup_lru=gi("P2P_LANE_DUP_LRU_BLOCK", 1024),
                yield_every=gi("P2P_LANE_YIELD_EVERY_BLOCK", 32),
            ),
        }
        return LaneLimiter(cfgs)

    def snapshot(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"lanes": {}}
        for lane in self._cfgs.keys():
            q = self._qs[lane]
            out["lanes"][lane] = {
                "queue_len": int(q.qsize()),
                "queue_max": int(self._cfgs[lane].max_queue),
                "inflight_max": int(self._cfgs[lane].max_inflight),
                "drop_policy": self._cfgs[lane].drop_policy,
                "dup_lru": int(self._cfgs[lane].dup_lru),
                "counters": dict(self._counters[lane]),
                "last_ok_ms": float(self._last_ok_ms.get(lane, 0.0) or 0.0),
            }
        return out

    async def ensure_workers(self) -> None:
        if self._workers_started:
            return
        async with self._workers_lock:
            if self._workers_started:
                return
            loop = asyncio.get_running_loop()
            for lane in self._cfgs.keys():
                loop.create_task(self._worker(lane), name=f"p2p-ingress-{lane}")
            self._workers_started = True

    async def enqueue(
        self,
        *,
        lane: str,
        msg_id: str,
        job: Callable[[], Awaitable[Any]],
    ) -> Dict[str, Any]:
        if lane not in self._cfgs:
            return {"ok": False, "enqueued": False, "dropped": True, "reason": "unknown lane"}

        await self.ensure_workers()

        # dup drop
        if self._lru[lane].seen(msg_id):
            self._counters[lane]["dropped_dup"] += 1
            return {"ok": True, "enqueued": False, "dropped": True, "reason": "duplicate"}

        q = self._qs[lane]
        cfg = self._cfgs[lane]

        if q.full():
            if cfg.drop_policy == "drop_old":
                try:
                    _ = q.get_nowait()
                    q.task_done()
                except Exception:
                    pass
                # if still full after drop_old attempt, drop_new anyway
                if q.full():
                    self._counters[lane]["dropped_full"] += 1
                    return {"ok": True, "enqueued": False, "dropped": True, "reason": "queue full"}
            else:
                self._counters[lane]["dropped_full"] += 1
                return {"ok": True, "enqueued": False, "dropped": True, "reason": "queue full"}

        try:
            q.put_nowait((msg_id, job))
            self._counters[lane]["enqueued"] += 1
            return {"ok": True, "enqueued": True, "dropped": False}
        except Exception:
            self._counters[lane]["dropped_full"] += 1
            return {"ok": True, "enqueued": False, "dropped": True, "reason": "queue full"}

    async def _worker(self, lane: str) -> None:
        q = self._qs[lane]
        sem = self._sem[lane]
        cfg = self._cfgs[lane]

        n = 0
        while True:
            msg_id, job = await q.get()
            try:
                async with sem:
                    # never monopolize the loop under flood
                    try:
                        await job()
                    except Exception:
                        pass
                    self._counters[lane]["processed"] += 1
                    self._last_ok_ms[lane] = _now_ms()
            finally:
                q.task_done()

            n += 1
            if cfg.yield_every > 0 and (n % int(cfg.yield_every)) == 0:
                await asyncio.sleep(0)