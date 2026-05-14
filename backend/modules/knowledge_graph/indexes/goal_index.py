# backend/modules/knowledge_graph/goal_index.py

from typing import List, Dict, Optional
from datetime import datetime
import hashlib


class GoalIndex:
    def __init__(self):
        self.goals: List[Dict] = []

    def add_goal(self, glyph: str, milestone: str, origin: str, status: str,
                 container_id: str, strategy_id: Optional[str] = None,
                 plugin: Optional[str] = None):
        goal = {
            "glyph": glyph,
            "milestone": milestone,
            "origin": origin,  # AION, DreamCore, User, etc.
            "status": status,  # pending | active | resolved | failed
            "container_id": container_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        if strategy_id:
            goal["strategy_id"] = strategy_id
        if plugin:
            goal["plugin"] = plugin

        # Deduplicate by glyph + milestone + origin
        goal["_hash"] = self._hash_goal(goal)
        if not any(g["_hash"] == goal["_hash"] for g in self.goals):
            self.goals.append(goal)

    def _hash_goal(self, g: Dict) -> str:
        base = f"{g['glyph']}|{g['milestone']}|{g['origin']}"
        return hashlib.sha256(base.encode()).hexdigest()

    def search_by_milestone(self, milestone: str) -> List[Dict]:
        return [g for g in self.goals if g["milestone"] == milestone]

    def unresolved_goals(self) -> List[Dict]:
        return [g for g in self.goals if g["status"] not in ("resolved", "failed")]

    def to_dict(self) -> Dict:
        return {
            "type": "GoalIndex",
            "total_goals": len(self.goals),
            "goals": self.goals
        }

    def summary(self) -> Dict:
        status_counts = {}
        for g in self.goals:
            status_counts[g["status"]] = status_counts.get(g["status"], 0) + 1
        return {
            "total": len(self.goals),
            "unresolved": len(self.unresolved_goals()),
            "by_status": status_counts,
            "origins": list(set(g["origin"] for g in self.goals))
        }


# Global instance
goal_index = GoalIndex()