"""
📡 Carrier Memory - SRK-12 Task E3
Caches photonic carrier fields for persistence and recovery.
"""

import json
import os
import time
from typing import Dict, Any


class CarrierMemory:
    def __init__(self, memory_dir: str = "carrier_memory"):
        self.memory_dir = memory_dir
        os.makedirs(memory_dir, exist_ok=True)

    def store(self, channel_id: str, field_state: Dict[str, Any]):
        """Store a coherence field snapshot."""
        path = os.path.join(self.memory_dir, f"{channel_id}.cmf")
        with open(path, "w") as f:
            json.dump({"timestamp": time.time(), "field": field_state}, f, indent=2)

    def load(self, channel_id: str) -> Dict[str, Any]:
        """Restore field snapshot."""
        path = os.path.join(self.memory_dir, f"{channel_id}.cmf")
        if not os.path.exists(path):
            return {}
        with open(path, "r") as f:
            return json.load(f)

    def list_channels(self):
        return [f.replace(".cmf", "") for f in os.listdir(self.memory_dir) if f.endswith(".cmf")]