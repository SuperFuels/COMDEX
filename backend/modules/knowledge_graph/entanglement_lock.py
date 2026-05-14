"""
🔒 Entanglement Lock Manager
Prevents conflicting edits in multi-agent KG sync (basic lock version).
"""

from typing import Dict, Optional
import time

class EntanglementLockManager:
    def __init__(self):
        self.locks: Dict[str, Dict] = {}  # glyph_id -> {agent_id, timestamp}

    def acquire_lock(self, glyph_id: str, agent_id: str, ttl: int = 10) -> bool:
        now = time.time()
        if glyph_id in self.locks and now - self.locks[glyph_id]["timestamp"] < ttl:
            return False  # lock still valid
        self.locks[glyph_id] = {"agent_id": agent_id, "timestamp": now}
        return True

    def release_lock(self, glyph_id: str, agent_id: str):
        if self.locks.get(glyph_id, {}).get("agent_id") == agent_id:
            del self.locks[glyph_id]

    def check_lock(self, glyph_id: str) -> Optional[str]:
        """Return agent_id holding lock, if any."""
        return self.locks.get(glyph_id, {}).get("agent_id")

# Singleton instance
entanglement_lock_manager = EntanglementLockManager()