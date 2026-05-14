from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _safe_bool(v: Any, default: bool = False) -> bool:
    try:
        return bool(v)
    except Exception:
        return default


def _dict(v: Any) -> Dict[str, Any]:
    return dict(v) if isinstance(v, dict) else {}


def _list(v: Any) -> List[Any]:
    return list(v) if isinstance(v, list) else []


def _list_str(v: Any) -> List[str]:
    if not isinstance(v, list):
        return []
    out: List[str] = []
    for x in v:
        s = str(x).strip()
        if s:
            out.append(s)
    return out


def _require_nonempty_str(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


@dataclass
class AionRewardBreakdown:
    """
    Phase D Sprint 2 reward decomposition:
      - process_score: execution/process quality (latency, safety, policy, etc.)
      - outcome_score: success/failure quality
      - reward_score: weighted combined score
    """
    schema_version: str = "aion.learning_reward_breakdown.v1"

    process_score: float = 0.0
    outcome_score: float = 0.0
    reward_score: float = 0.0
    weighting: Dict[str, Any] = field(default_factory=lambda: {"process": 0.6, "outcome": 0.4})
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "AionRewardBreakdown":
        self.process_score = max(0.0, min(1.0, _safe_float(self.process_score, 0.0)))
        self.outcome_score = max(0.0, min(1.0, _safe_float(self.outcome_score, 0.0)))
        self.reward_score = max(0.0, min(1.0, _safe_float(self.reward_score, 0.0)))
        self.weighting = _dict(self.weighting) or {"process": 0.6, "outcome": 0.4}
        self.metadata = _dict(self.metadata)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "process_score": float(self.process_score),
            "outcome_score": float(self.outcome_score),
            "reward_score": float(self.reward_score),
            "weighting": dict(self.weighting),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "AionRewardBreakdown":
        d = _dict(data)
        return cls(
            schema_version=str(d.get("schema_version") or "aion.learning_reward_breakdown.v1"),
            process_score=d.get("process_score", 0.0),
            outcome_score=d.get("outcome_score", 0.0),
            reward_score=d.get("reward_score", 0.0),
            weighting=_dict(d.get("weighting")) or {"process": 0.6, "outcome": 0.4},
            metadata=_dict(d.get("metadata")),
        ).validate()


@dataclass
class AionLearningQuery:
    """
    Typed read-path query contract for learning events / weaknesses.
    """
    schema_version: str = "aion.learning_query.v1"

    skill_id: Optional[str] = None
    error_code: Optional[str] = None
    ok: Optional[bool] = None
    since_ts: Optional[float] = None
    limit: int = 100
    include_weaknesses: bool = True
    metadata_filters: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "AionLearningQuery":
        if self.skill_id is not None:
            self.skill_id = str(self.skill_id).strip() or None
        if self.error_code is not None:
            self.error_code = str(self.error_code).strip() or None
        if self.since_ts is not None:
            self.since_ts = _safe_float(self.since_ts, 0.0)
        self.limit = max(1, min(_safe_int(self.limit, 100), 5000))
        self.include_weaknesses = _safe_bool(self.include_weaknesses, True)
        self.metadata_filters = _dict(self.metadata_filters)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "skill_id": self.skill_id,
            "error_code": self.error_code,
            "ok": self.ok,
            "since_ts": self.since_ts,
            "limit": int(self.limit),
            "include_weaknesses": bool(self.include_weaknesses),
            "metadata_filters": dict(self.metadata_filters),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "AionLearningQuery":
        d = _dict(data)
        return cls(
            schema_version=str(d.get("schema_version") or "aion.learning_query.v1"),
            skill_id=(str(d.get("skill_id")) if d.get("skill_id") is not None else None),
            error_code=(str(d.get("error_code")) if d.get("error_code") is not None else None),
            ok=d.get("ok"),
            since_ts=d.get("since_ts"),
            limit=d.get("limit", 100),
            include_weaknesses=d.get("include_weaknesses", True),
            metadata_filters=_dict(d.get("metadata_filters")),
        ).validate()


@dataclass
class AionLearningSummary:
    """
    Aggregate summary over learning events (read-only runtime output).
    """
    schema_version: str = "aion.learning_summary.v1"

    total_events: int = 0
    ok_count: int = 0
    fail_count: int = 0

    avg_latency_ms: float = 0.0
    avg_process_score: float = 0.0
    avg_outcome_score: float = 0.0
    avg_reward_score: float = 0.0

    by_skill: Dict[str, Any] = field(default_factory=dict)
    by_error_code: Dict[str, int] = field(default_factory=dict)
    generated_at_ts: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "AionLearningSummary":
        self.total_events = max(0, _safe_int(self.total_events, 0))
        self.ok_count = max(0, _safe_int(self.ok_count, 0))
        self.fail_count = max(0, _safe_int(self.fail_count, 0))
        self.avg_latency_ms = max(0.0, _safe_float(self.avg_latency_ms, 0.0))
        self.avg_process_score = max(0.0, min(1.0, _safe_float(self.avg_process_score, 0.0)))
        self.avg_outcome_score = max(0.0, min(1.0, _safe_float(self.avg_outcome_score, 0.0)))
        self.avg_reward_score = max(0.0, min(1.0, _safe_float(self.avg_reward_score, 0.0)))
        self.by_skill = _dict(self.by_skill)
        self.by_error_code = {str(k): _safe_int(v, 0) for k, v in _dict(self.by_error_code).items()}
        self.generated_at_ts = _safe_float(self.generated_at_ts, 0.0)
        self.metadata = _dict(self.metadata)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "total_events": int(self.total_events),
            "ok_count": int(self.ok_count),
            "fail_count": int(self.fail_count),
            "avg_latency_ms": float(self.avg_latency_ms),
            "avg_process_score": float(self.avg_process_score),
            "avg_outcome_score": float(self.avg_outcome_score),
            "avg_reward_score": float(self.avg_reward_score),
            "by_skill": dict(self.by_skill),
            "by_error_code": dict(self.by_error_code),
            "generated_at_ts": float(self.generated_at_ts),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "AionLearningSummary":
        d = _dict(data)
        return cls(
            schema_version=str(d.get("schema_version") or "aion.learning_summary.v1"),
            total_events=d.get("total_events", 0),
            ok_count=d.get("ok_count", 0),
            fail_count=d.get("fail_count", 0),
            avg_latency_ms=d.get("avg_latency_ms", 0.0),
            avg_process_score=d.get("avg_process_score", 0.0),
            avg_outcome_score=d.get("avg_outcome_score", 0.0),
            avg_reward_score=d.get("avg_reward_score", 0.0),
            by_skill=_dict(d.get("by_skill")),
            by_error_code=_dict(d.get("by_error_code")),
            generated_at_ts=d.get("generated_at_ts", 0.0),
            metadata=_dict(d.get("metadata")),
        ).validate()


@dataclass
class AionLearningWeaknessSignal:
    """
    Typed weakness signal (failure clustering output).
    """
    schema_version: str = "aion.learning_weakness_signal.v1"

    weakness_id: str = ""
    kind: str = "skill_error_cluster"
    skill_id: str = ""
    error_code: str = ""
    count: int = 0
    fail_rate: float = 0.0
    avg_latency_ms: float = 0.0
    confidence: float = 0.0
    severity: str = "low"  # low | medium | high
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "AionLearningWeaknessSignal":
        _require_nonempty_str("weakness_id", self.weakness_id)
        _require_nonempty_str("kind", self.kind)
        self.skill_id = str(self.skill_id or "").strip()
        self.error_code = str(self.error_code or "").strip()
        self.count = max(0, _safe_int(self.count, 0))
        self.fail_rate = max(0.0, min(1.0, _safe_float(self.fail_rate, 0.0)))
        self.avg_latency_ms = max(0.0, _safe_float(self.avg_latency_ms, 0.0))
        self.confidence = max(0.0, min(1.0, _safe_float(self.confidence, 0.0)))
        self.severity = str(self.severity or "low").strip().lower()
        if self.severity not in {"low", "medium", "high"}:
            self.severity = "low"
        self.summary = str(self.summary or "").strip()
        self.metadata = _dict(self.metadata)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "weakness_id": self.weakness_id,
            "kind": self.kind,
            "skill_id": self.skill_id,
            "error_code": self.error_code,
            "count": int(self.count),
            "fail_rate": float(self.fail_rate),
            "avg_latency_ms": float(self.avg_latency_ms),
            "confidence": float(self.confidence),
            "severity": self.severity,
            "summary": self.summary,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "AionLearningWeaknessSignal":
        d = _dict(data)
        return cls(
            schema_version=str(d.get("schema_version") or "aion.learning_weakness_signal.v1"),
            weakness_id=str(d.get("weakness_id") or ""),
            kind=str(d.get("kind") or "skill_error_cluster"),
            skill_id=str(d.get("skill_id") or ""),
            error_code=str(d.get("error_code") or ""),
            count=d.get("count", 0),
            fail_rate=d.get("fail_rate", 0.0),
            avg_latency_ms=d.get("avg_latency_ms", 0.0),
            confidence=d.get("confidence", 0.0),
            severity=str(d.get("severity") or "low"),
            summary=str(d.get("summary") or ""),
            metadata=_dict(d.get("metadata")),
        ).validate()


@dataclass
class AionLearningReport:
    """
    Read-only learning report for orchestrator/admin diagnostics.
    """
    schema_version: str = "aion.learning_report.v1"

    report_id: str = ""
    query: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    top_weaknesses: List[Dict[str, Any]] = field(default_factory=list)
    recent_events: List[Dict[str, Any]] = field(default_factory=list)
    generated_at_ts: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "AionLearningReport":
        _require_nonempty_str("report_id", self.report_id)
        self.query = _dict(self.query)
        self.summary = _dict(self.summary)
        self.top_weaknesses = [dict(x) for x in _list(self.top_weaknesses) if isinstance(x, dict)]
        self.recent_events = [dict(x) for x in _list(self.recent_events) if isinstance(x, dict)]
        self.generated_at_ts = _safe_float(self.generated_at_ts, 0.0)
        self.metadata = _dict(self.metadata)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "report_id": self.report_id,
            "query": dict(self.query),
            "summary": dict(self.summary),
            "top_weaknesses": [dict(x) for x in self.top_weaknesses],
            "recent_events": [dict(x) for x in self.recent_events],
            "generated_at_ts": float(self.generated_at_ts),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "AionLearningReport":
        d = _dict(data)
        return cls(
            schema_version=str(d.get("schema_version") or "aion.learning_report.v1"),
            report_id=str(d.get("report_id") or ""),
            query=_dict(d.get("query")),
            summary=_dict(d.get("summary")),
            top_weaknesses=[dict(x) for x in _list(d.get("top_weaknesses")) if isinstance(x, dict)],
            recent_events=[dict(x) for x in _list(d.get("recent_events")) if isinstance(x, dict)],
            generated_at_ts=d.get("generated_at_ts", 0.0),
            metadata=_dict(d.get("metadata")),
        ).validate()


@dataclass
class AionLearningContextView:
    """
    Read-only context shape intended for orchestrator/planner injection.
    IMPORTANT: Keep this interface stable so Sprint 3+ can reuse it unchanged.
    """
    schema_version: str = "aion.learning_context_view.v1"

    topic: Optional[str] = None
    summary: Dict[str, Any] = field(default_factory=dict)
    weakness_hints: List[str] = field(default_factory=list)
    recommended_cautions: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    writable: bool = False  # always False in Sprint 2
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "AionLearningContextView":
        self.topic = (str(self.topic).strip() if self.topic is not None else None)
        self.summary = _dict(self.summary)
        self.weakness_hints = _list_str(self.weakness_hints)
        self.recommended_cautions = _list_str(self.recommended_cautions)
        self.evidence_refs = _list_str(self.evidence_refs)
        self.writable = False  # phase lock: read-only only
        self.metadata = _dict(self.metadata)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "topic": self.topic,
            "summary": dict(self.summary),
            "weakness_hints": list(self.weakness_hints),
            "recommended_cautions": list(self.recommended_cautions),
            "evidence_refs": list(self.evidence_refs),
            "writable": False,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "AionLearningContextView":
        d = _dict(data)
        return cls(
            schema_version=str(d.get("schema_version") or "aion.learning_context_view.v1"),
            topic=(str(d.get("topic")) if d.get("topic") is not None else None),
            summary=_dict(d.get("summary")),
            weakness_hints=_list_str(d.get("weakness_hints")),
            recommended_cautions=_list_str(d.get("recommended_cautions")),
            evidence_refs=_list_str(d.get("evidence_refs")),
            writable=False,
            metadata=_dict(d.get("metadata")),
        ).validate()