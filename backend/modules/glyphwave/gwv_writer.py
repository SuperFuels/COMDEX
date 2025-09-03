import os
import json
from datetime import datetime
from collections import deque

class SnapshotRingBuffer:
    def __init__(self, maxlen=60):
        self.buffer = deque(maxlen=maxlen)

    def add_snapshot(self, collapse_rate, decoherence_rate, timestamp=None):
        snapshot = {
            "timestamp": timestamp or datetime.utcnow().isoformat(),
            "collapse_rate": collapse_rate,
            "decoherence_rate": decoherence_rate
        }
        self.buffer.append(snapshot)

    def export_to_gwv(self, container_id="unknown", output_dir="snapshots/gwv/"):
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{container_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.gwv"
        path = os.path.join(output_dir, filename)
        with open(path, "w") as f:
            json.dump(list(self.buffer), f, indent=2)
        return path