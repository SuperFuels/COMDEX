# File: backend/modules/gip/gip_log.py

import datetime
from typing import Dict, List

class GIPLog:
    def __init__(self):
        self.history: List[Dict] = []

    def log_packet(self, packet: Dict, node: str):
        entry = {
            "node": node,
            "glyph": packet.get("glyph") or packet.get("id"),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
        self.history.append(entry)
        if len(self.history) > 500:
            self.history = self.history[-500:]  # Limit memory use

    def get_logs(self) -> List[Dict]:
        return list(reversed(self.history))

# Singleton instance
gip_log = GIPLog()