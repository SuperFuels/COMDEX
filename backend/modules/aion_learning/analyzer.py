from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from backend.modules.aion_learning.contracts import LearningEvent


@dataclass
class WeaknessFlag:
    skill_id: str
    issue: str
    severity: str = "medium"  # low | medium | high
    evidence_count: int = 0
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "skill_id": self.skill_id,
            "issue": self.issue,
            "severity": self.severity,
            "evidence_count": int(self.evidence_count),
            "metadata": dict(self.metadata or {}),
        }


class LearningAnalyzer:
    """
    Phase D Sprint 1: simple failure clustering + weakness detection.
    """

    def analyze_skill_events(self, events: List[LearningEvent]) -> Dict[str, object]:
        skill_events = [e for e in events if e.event_type == "skill_run" and e.skill_id]
        by_skill: Dict[str, List[LearningEvent]] = {}
        for e in skill_events:
            by_skill.setdefault(str(e.skill_id), []).append(e)

        weakness_flags: List[WeaknessFlag] = []
        error_clusters: Dict[str, Dict[str, int]] = {}

        for skill_id, rows in by_skill.items():
            fails = [e for e in rows if e.ok is False]
            oks = [e for e in rows if e.ok is True]

            # failure rate
            total = len(rows)
            fail_rate = (len(fails) / total) if total else 0.0

            if total >= 3 and fail_rate >= 0.5:
                weakness_flags.append(
                    WeaknessFlag(
                        skill_id=skill_id,
                        issue="high_failure_rate",
                        severity="high" if fail_rate >= 0.75 else "medium",
                        evidence_count=len(fails),
                        metadata={"total_runs": total, "fail_rate": round(fail_rate, 3)},
                    )
                )

            # repeated same error_code cluster
            ec: Dict[str, int] = {}
            for f in fails:
                code = str(f.error_code or "unknown_error")
                ec[code] = ec.get(code, 0) + 1
            error_clusters[skill_id] = ec

            for code, count in ec.items():
                if count >= 2:
                    weakness_flags.append(
                        WeaknessFlag(
                            skill_id=skill_id,
                            issue="repeated_error_code",
                            severity="medium",
                            evidence_count=count,
                            metadata={"error_code": code},
                        )
                    )

            # latency regression heuristic
            latencies = [int(e.latency_ms or 0) for e in oks if e.latency_ms is not None]
            if len(latencies) >= 3:
                avg_latency = sum(latencies) / max(1, len(latencies))
                if avg_latency > 1500:
                    weakness_flags.append(
                        WeaknessFlag(
                            skill_id=skill_id,
                            issue="high_avg_latency",
                            severity="medium",
                            evidence_count=len(latencies),
                            metadata={"avg_latency_ms": int(avg_latency)},
                        )
                    )

        # Dedup similar flags
        dedup: Dict[str, WeaknessFlag] = {}
        for wf in weakness_flags:
            k = f"{wf.skill_id}|{wf.issue}|{wf.metadata.get('error_code', '')}"
            prev = dedup.get(k)
            if prev is None or wf.evidence_count > prev.evidence_count:
                dedup[k] = wf

        return {
            "skill_event_count": len(skill_events),
            "skills_seen": sorted(by_skill.keys()),
            "error_clusters": error_clusters,
            "weakness_flags": [w.to_dict() for w in dedup.values()],
        }