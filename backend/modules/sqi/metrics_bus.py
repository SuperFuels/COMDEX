from __future__ import annotations

from typing import Callable, Dict, List, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)


def _quiet_enabled() -> bool:
    return os.getenv("TESSARIS_TEST_QUIET") == "1" or os.getenv("TESSARIS_DETERMINISTIC_TIME") == "1"


class MetricsBus:
    """
    Lightweight in-process pub/sub system for SQI or CodexHUD metrics.
    Subscribers can register functions to be called when data is pushed.
    """
    def __init__(self):
        self.subscribers: List[Callable[[Dict[str, Any]], None]] = []

    def push(self, data: Dict[str, Any]) -> None:
        for sub in list(self.subscribers):
            try:
                sub(data)
            except Exception as e:
                logger.warning(f"[MetricsBus] Subscriber error: {e}")

    def subscribe(self, fn: Callable[[Dict[str, Any]], None]) -> None:
        self.subscribers.append(fn)

    def unsubscribe(self, fn: Callable[[Dict[str, Any]], None]) -> None:
        self.subscribers = [s for s in self.subscribers if s != fn]


_METRICS_BUS: Optional[MetricsBus] = None


def get_metrics_bus() -> MetricsBus:
    global _METRICS_BUS
    if _METRICS_BUS is None:
        _METRICS_BUS = MetricsBus()
        if not _quiet_enabled():
            print("[SQI] MetricsBus initialized (lazy)")
    return _METRICS_BUS


class _MetricsBusProxy:
    def __getattr__(self, name: str):
        return getattr(get_metrics_bus(), name)


# Back-compat: `from ... import metrics_bus`
metrics_bus = _MetricsBusProxy()
