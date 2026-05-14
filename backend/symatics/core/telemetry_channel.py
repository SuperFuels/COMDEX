# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v1.1 - Δ-Telemetry Channel
# Real-time feedback bus for λ(t), ψ(t), and symbolic resonance metrics
# Author: Tessaris Core Systems / Codex Intelligence Group
# Version: v1.1.0 - October 2025
# ──────────────────────────────────────────────────────────────

from __future__ import annotations
import time, json, threading
from collections import deque
from typing import Dict, Any, List, Optional

# ──────────────────────────────────────────────────────────────
# Global Telemetry Buffer
# ──────────────────────────────────────────────────────────────
class TelemetryChannel:
    """
    A lightweight asynchronous channel for live Δ-Telemetry packets.

    Each record includes timestamped metrics emitted from adaptive engines.
    Buffers retain the most recent N samples for rolling analytics.
    """

    def __init__(self, maxlen: int = 2048):
        self.buffer: deque[Dict[str, Any]] = deque(maxlen=maxlen)
        self.lock = threading.Lock()
        self.enabled: bool = True

    # ──────────────────────────────────────────────────────────
    def record(
        self,
        source: str,
        metrics: Dict[str, float],
        ctx_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """Append a new telemetry event."""
        if not self.enabled:
            return
        record = {
            "timestamp": time.time(),
            "source": source,
            "metrics": metrics,
            "ctx": ctx_id,
            "tags": tags or [],
        }
        with self.lock:
            self.buffer.append(record)

    # ──────────────────────────────────────────────────────────
    def latest(self, n: int = 1) -> List[Dict[str, Any]]:
        """Return the most recent n telemetry packets."""
        with self.lock:
            return list(self.buffer)[-n:]

    def summary(self) -> Dict[str, float]:
        """Compute rolling averages of primary metrics."""
        if not self.buffer:
            return {}
        sums, count = {}, 0
        with self.lock:
            for rec in self.buffer:
                for k, v in rec["metrics"].items():
                    sums[k] = sums.get(k, 0.0) + v
                count += 1
        return {k: v / count for k, v in sums.items()}

    def export_json(self, path: str):
        """Dump buffer contents to JSON file."""
        with self.lock:
            data = list(self.buffer)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def clear(self):
        with self.lock:
            self.buffer.clear()

# ──────────────────────────────────────────────────────────────
# Singleton Accessor (used by engines)
# ──────────────────────────────────────────────────────────────
_global_channel: Optional[TelemetryChannel] = None

def get_channel() -> TelemetryChannel:
    global _global_channel
    if _global_channel is None:
        _global_channel = TelemetryChannel()
    return _global_channel

def record_event(source: str, metrics: Dict[str, float], **kw):
    """Public helper for quick emission."""
    chan = get_channel()
    chan.record(source, metrics, **kw)