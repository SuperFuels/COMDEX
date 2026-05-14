from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from backend.modules.aion_learning.contracts import LearningEvent


class LearningStore:
    """
    Append-only JSONL learning store (Phase D Sprint 1).
    """

    def __init__(self, path: str) -> None:
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def append(self, event: LearningEvent) -> LearningEvent:
        ev = event.validate()
        if not ev.timestamp:
            ev.timestamp = datetime.now(timezone.utc).isoformat()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev.to_dict(), ensure_ascii=False) + "\n")
        return ev

    def read_all(self, limit: Optional[int] = None) -> List[LearningEvent]:
        if not os.path.exists(self.path):
            return []
        rows: List[LearningEvent] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(LearningEvent.from_dict(json.loads(line)))
                except Exception:
                    continue
        if limit is not None and limit > 0:
            return rows[-limit:]
        return rows

    def summary(self, limit: int = 500) -> Dict[str, object]:
        events = self.read_all(limit=limit)
        total = len(events)
        by_type: Dict[str, int] = {}
        by_skill: Dict[str, Dict[str, int]] = {}

        for e in events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
            if e.skill_id:
                row = by_skill.setdefault(e.skill_id, {"total": 0, "ok": 0, "fail": 0})
                row["total"] += 1
                if e.ok is True:
                    row["ok"] += 1
                elif e.ok is False:
                    row["fail"] += 1

        return {
            "total_events": total,
            "by_type": by_type,
            "by_skill": by_skill,
            "window": limit,
        }