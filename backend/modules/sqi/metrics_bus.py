# backend/modules/sqi/metrics_bus.py

from typing import Callable, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class MetricsBus:
    """
    Lightweight in-process pub/sub system for SQI or CodexHUD metrics.
    Subscribers can register functions to be called when data is pushed.
    """
    def __init__(self):
        self.subscribers: List[Callable[[Dict[str, Any]], None]] = []

    def push(self, data: Dict[str, Any]) -> None:
        """
        Send data to all subscribers.

        Args:
            data (dict): The event or metric payload.
        """
        for sub in self.subscribers:
            try:
                sub(data)
            except Exception as e:
                logger.warning(f"[MetricsBus] Subscriber error: {e}")

    def subscribe(self, fn: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a subscriber function.

        Args:
            fn (callable): Function that accepts a single dict argument.
        """
        self.subscribers.append(fn)

    def unsubscribe(self, fn: Callable[[Dict[str, Any]], None]) -> None:
        """
        Remove a subscriber function.

        Args:
            fn (callable): Function previously registered.
        """
        self.subscribers = [s for s in self.subscribers if s != fn]


# Global instance
metrics_bus = MetricsBus()