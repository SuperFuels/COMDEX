"""
🟢 GWV Writer — SRK-19 Task 3
Graphical Wave Visualization Writer.
Persists real-time holographic QFC frames into timestamped `.gwv` playback files.

Features:
 • Maintains circular buffer of visual frames (SnapshotRingBuffer)
 • Supports QFC/GHX hybrid frame input
 • Exports coherent time-series playback data
 • Computes frame stability metrics for analysis
"""

import os
import json
from datetime import datetime
from collections import deque
from typing import Dict, Any, List, Optional


class SnapshotRingBuffer:
    """Ring buffer for recent QFC / GHX visual frames."""
    def __init__(self, maxlen: int = 120):
        self.buffer = deque(maxlen=maxlen)

    def add_snapshot(self, *args, **kwargs) -> None:
        """
        Append a visual snapshot to the ring buffer.

        Accepts both:
          • add_snapshot(frame_data, collapse_rate, decoherence_rate)
          • add_snapshot(collapse_rate, decoherence_rate, frame_data)
        """

        frame_data = None
        collapse_rate = 0.0
        decoherence_rate = 0.0
        timestamp = kwargs.get("timestamp")

        # handle both old/new call orders
        if len(args) == 3:
            if isinstance(args[0], (int, float)) and isinstance(args[2], dict):
                # old call style: (collapse_rate, decoherence_rate, frame_data)
                collapse_rate, decoherence_rate, frame_data = args
            else:
                # new call style: (frame_data, collapse_rate, decoherence_rate)
                frame_data, collapse_rate, decoherence_rate = args
        elif len(args) == 4:
            # support timestamped call
            frame_data, collapse_rate, decoherence_rate, timestamp = args
        elif len(args) == 1 and isinstance(args[0], dict):
            frame_data = args[0]

        ts = timestamp or datetime.utcnow().isoformat()
        entry = {
            "timestamp": ts,
            "collapse_rate": float(collapse_rate),
            "decoherence_rate": float(decoherence_rate),
            "frame": frame_data or {},
        }
        self.buffer.append(entry)

    def compute_stability_metric(self) -> float:
        """
        Compute a rolling stability metric from collapse/decoherence rates.
        Returns a value in [0, 1], where 1 = stable.
        """
        if not self.buffer:
            return 1.0
        collapse_vals = [s["collapse_rate"] for s in self.buffer]
        deco_vals = [s["decoherence_rate"] for s in self.buffer]
        avg_c = sum(collapse_vals) / len(collapse_vals)
        avg_d = sum(deco_vals) / len(deco_vals)
        stability = max(0.0, 1.0 - (avg_c + avg_d) / 2.0)
        return round(stability, 4)

    def export_to_gwv(
        self,
        container_id: str = "unknown",
        output_dir: str = "snapshots/gwv/",
        legacy_format: bool = True,
    ) -> str:
        """
        Serialize the current buffer into a timestamped .gwv file.

        Args:
            container_id: Unique ID for the data stream.
            output_dir: Target directory.
            legacy_format: If True, output only the frame list (for backward compatibility).

        Returns:
            The full path to the written .gwv file.
        """
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{container_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.gwv"
        path = os.path.join(output_dir, filename)

        if legacy_format:
            # old-style .gwv output (list only)
            payload = list(self.buffer)
        else:
            # full structured payload
            payload = {
                "container_id": container_id,
                "snapshot_count": len(self.buffer),
                "stability": self.compute_stability_metric(),
                "frames": list(self.buffer),
            }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return path


class GWVWriter:
    """Manages multiple buffers per visualization channel or container."""
    def __init__(self, output_dir: str = "snapshots/gwv/"):
        self.output_dir = output_dir
        self._buffers: Dict[str, SnapshotRingBuffer] = {}

    def get_buffer(self, container_id: str) -> SnapshotRingBuffer:
        """Get (or create) the ring buffer for a container."""
        if container_id not in self._buffers:
            self._buffers[container_id] = SnapshotRingBuffer()
        return self._buffers[container_id]

    def record_frame(
        self,
        container_id: str,
        frame_data: Dict[str, Any],
        collapse_rate: float = 0.0,
        decoherence_rate: float = 0.0,
    ) -> None:
        """
        Record a live QFC or GHX frame into the container’s buffer.
        """
        buffer = self.get_buffer(container_id)
        buffer.add_snapshot(frame_data, collapse_rate, decoherence_rate)

    def flush_to_disk(self, container_id: str) -> Optional[str]:
        """
        Persist a container’s ring buffer to disk as a .gwv file.
        Returns the file path, or None if no buffer exists.
        """
        if container_id not in self._buffers:
            return None
        return self._buffers[container_id].export_to_gwv(container_id, self.output_dir)