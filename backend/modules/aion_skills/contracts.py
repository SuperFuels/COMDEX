from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Skill contract enums / allowed values
# ---------------------------------------------------------------------------

ALLOWED_SAFETY_CLASSES = {
    # Newer normalized labels (preferred)
    "safe_read",
    "safe_transform",
    "internal_state",
    "external_side_effect",
    # Backward-compatible labels (already used in repo/tests)
    "internal_safe",
    "read_only",
    "external_network",
    "side_effecting",
    "restricted",
}

ALLOWED_STAGES = {"experimental", "verified", "core"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _dict_any(v: Any) -> Dict[str, Any]:
    return dict(v) if isinstance(v, dict) else {}


def _list_str(v: Any) -> List[str]:
    if not isinstance(v, list):
        return []
    out: List[str] = []
    for x in v:
        s = str(x).strip()
        if s:
            out.append(s)
    return out


def _validate_required_nonempty_str(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


# ---------------------------------------------------------------------------
# Phase C metadata/policy layer (new, additive)
# ---------------------------------------------------------------------------

@dataclass
class SkillValidationPolicy:
    """
    Validation policy used by registry/promotion workflows.
    Additive contract (does not replace SkillValidationCase/Result).
    """
    schema_version: str = "aion.skill_validation_policy.v1"

    min_success_rate: float = 0.80
    max_avg_latency_ms: int = 2000
    required_output_keys: List[str] = field(default_factory=list)
    min_sample_size: int = 3

    def validate(self) -> "SkillValidationPolicy":
        self.min_success_rate = max(0.0, min(1.0, _safe_float(self.min_success_rate, 0.8)))

        self.max_avg_latency_ms = _safe_int(self.max_avg_latency_ms, 2000)
        if self.max_avg_latency_ms < 1:
            self.max_avg_latency_ms = 2000

        self.min_sample_size = _safe_int(self.min_sample_size, 3)
        if self.min_sample_size < 1:
            self.min_sample_size = 1

        self.required_output_keys = _list_str(self.required_output_keys)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "min_success_rate": float(self.min_success_rate),
            "max_avg_latency_ms": int(self.max_avg_latency_ms),
            "required_output_keys": list(self.required_output_keys or []),
            "min_sample_size": int(self.min_sample_size),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SkillValidationPolicy":
        d = _dict_any(data)
        return cls(
            schema_version=str(d.get("schema_version") or "aion.skill_validation_policy.v1"),
            min_success_rate=d.get("min_success_rate", 0.80),
            max_avg_latency_ms=d.get("max_avg_latency_ms", 2000),
            required_output_keys=_list_str(d.get("required_output_keys")),
            min_sample_size=d.get("min_sample_size", 3),
        ).validate()


@dataclass
class SkillMetadata:
    """
    Lightweight skill metadata record used by registry/promotion layers.
    This is additive and can coexist with SkillSpec.
    """
    schema_version: str = "aion.skill_metadata.v1"

    skill_id: str = ""
    title: str = ""
    description: str = ""

    # Preferred normalized names:
    #   safe_read | safe_transform | internal_state | external_side_effect
    # Backward-compat names are accepted and normalized/kept as-is if valid.
    safety_class: str = "safe_read"

    # experimental | verified | core
    stage: str = "experimental"

    tags: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    enabled: bool = True

    validation_policy: SkillValidationPolicy = field(default_factory=SkillValidationPolicy)
    extra: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "SkillMetadata":
        self.skill_id = str(self.skill_id or "").strip()
        self.title = str(self.title or self.skill_id).strip()
        self.description = str(self.description or "").strip()

        self.safety_class = str(self.safety_class or "safe_read").strip()
        if self.safety_class not in ALLOWED_SAFETY_CLASSES:
            self.safety_class = "safe_read"

        self.stage = str(self.stage or "experimental").strip()
        if self.stage not in ALLOWED_STAGES:
            self.stage = "experimental"

        self.tags = _list_str(self.tags)
        self.topics = _list_str(self.topics)
        self.enabled = bool(self.enabled)

        if not isinstance(self.validation_policy, SkillValidationPolicy):
            if isinstance(self.validation_policy, dict):
                self.validation_policy = SkillValidationPolicy.from_dict(self.validation_policy)
            elif self.validation_policy is None:
                self.validation_policy = SkillValidationPolicy()
            else:
                # tolerate objects with to_dict()
                try:
                    self.validation_policy = SkillValidationPolicy.from_dict(self.validation_policy.to_dict())
                except Exception:
                    self.validation_policy = SkillValidationPolicy()
        self.validation_policy.validate()

        self.extra = _dict_any(self.extra)

        if not self.skill_id:
            raise ValueError("skill_id is required")

        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "skill_id": self.skill_id,
            "title": self.title,
            "description": self.description,
            "safety_class": self.safety_class,
            "stage": self.stage,
            "tags": list(self.tags or []),
            "topics": list(self.topics or []),
            "enabled": bool(self.enabled),
            "validation_policy": self.validation_policy.to_dict(),
            "extra": dict(self.extra or {}),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SkillMetadata":
        d = _dict_any(data)
        return cls(
            schema_version=str(d.get("schema_version") or "aion.skill_metadata.v1"),
            skill_id=str(d.get("skill_id") or ""),
            title=str(d.get("title") or d.get("skill_id") or ""),
            description=str(d.get("description") or ""),
            safety_class=str(d.get("safety_class") or "safe_read"),
            stage=str(d.get("stage") or "experimental"),
            tags=_list_str(d.get("tags")),
            topics=_list_str(d.get("topics")),
            enabled=bool(d.get("enabled", True)),
            validation_policy=SkillValidationPolicy.from_dict(d.get("validation_policy")),
            extra=_dict_any(d.get("extra")),
        ).validate()


# ---------------------------------------------------------------------------
# Phase C core registry/execution contracts (existing + extended safely)
# ---------------------------------------------------------------------------

@dataclass
class SkillSpec:
    """
    Registry contract for a skill.
    Backward-compatible with existing runtime code, with additive policy/meta fields.
    """
    schema_version: str = "aion.skill_spec.v1"

    skill_id: str = ""
    name: str = ""
    version: str = "0.1.0"
    description: str = ""

    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)

    # Backward-compatible values still accepted:
    # internal_safe | read_only | external_network | side_effecting | restricted
    # Also accepts normalized values:
    # safe_read | safe_transform | internal_state | external_side_effect
    safety_class: str = "internal_safe"
    timeout_ms: int = 5000
    retry_policy: Dict[str, Any] = field(default_factory=lambda: {"max_retries": 0})

    # experimental | verified | core
    status: str = "experimental"

    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Additive fields for promotion/validation workflow
    topics: List[str] = field(default_factory=list)
    enabled: bool = True
    validation_policy: SkillValidationPolicy = field(default_factory=SkillValidationPolicy)

    def validate(self) -> "SkillSpec":
        _validate_required_nonempty_str("skill_id", self.skill_id)
        _validate_required_nonempty_str("name", self.name)
        _validate_required_nonempty_str("version", self.version)

        if self.timeout_ms < 1:
            raise ValueError("timeout_ms must be >= 1")

        if self.status not in ALLOWED_STAGES:
            raise ValueError("status must be one of: experimental, verified, core")

        if self.safety_class not in ALLOWED_SAFETY_CLASSES:
            raise ValueError(f"safety_class must be one of: {sorted(ALLOWED_SAFETY_CLASSES)}")

        self.tags = _list_str(self.tags)
        self.topics = _list_str(self.topics)
        self.enabled = bool(self.enabled)

        if not isinstance(self.validation_policy, SkillValidationPolicy):
            if isinstance(self.validation_policy, dict):
                self.validation_policy = SkillValidationPolicy.from_dict(self.validation_policy)
            else:
                try:
                    self.validation_policy = SkillValidationPolicy.from_dict(self.validation_policy.to_dict())
                except Exception:
                    self.validation_policy = SkillValidationPolicy()
        self.validation_policy.validate()

        self.input_schema = _dict_any(self.input_schema)
        self.output_schema = _dict_any(self.output_schema)
        self.retry_policy = _dict_any(self.retry_policy) or {"max_retries": 0}
        self.metadata = _dict_any(self.metadata)

        return self

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "schema_version": self.schema_version,
            "skill_id": self.skill_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "input_schema": dict(self.input_schema or {}),
            "output_schema": dict(self.output_schema or {}),
            "safety_class": self.safety_class,
            "timeout_ms": int(self.timeout_ms),
            "retry_policy": dict(self.retry_policy or {}),
            "status": self.status,
            "tags": list(self.tags or []),
            "metadata": dict(self.metadata or {}),
            "topics": list(self.topics or []),
            "enabled": bool(self.enabled),
            "validation_policy": self.validation_policy.to_dict(),
        }
        return out

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SkillSpec":
        d = dict(data or {})
        return cls(
            schema_version=str(d.get("schema_version") or "aion.skill_spec.v1"),
            skill_id=str(d.get("skill_id") or ""),
            name=str(d.get("name") or ""),
            version=str(d.get("version") or "0.1.0"),
            description=str(d.get("description") or ""),
            input_schema=_dict_any(d.get("input_schema")),
            output_schema=_dict_any(d.get("output_schema")),
            safety_class=str(d.get("safety_class") or "internal_safe"),
            timeout_ms=_safe_int(d.get("timeout_ms"), 5000),
            retry_policy=_dict_any(d.get("retry_policy")) or {"max_retries": 0},
            status=str(d.get("status") or "experimental"),
            tags=_list_str(d.get("tags")),
            metadata=_dict_any(d.get("metadata")),
            topics=_list_str(d.get("topics")),
            enabled=bool(d.get("enabled", True)),
            validation_policy=SkillValidationPolicy.from_dict(d.get("validation_policy")),
        )


@dataclass
class SkillRunRequest:
    """
    Standardized execution request from orchestrator -> skill adapter.
    """
    schema_version: str = "aion.skill_run_request.v1"

    skill_id: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)

    # tracing / linkage
    session_id: Optional[str] = None
    turn_id: Optional[str] = None
    request_id: Optional[str] = None

    # execution flags
    dry_run: bool = False
    timeout_ms_override: Optional[int] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "SkillRunRequest":
        _validate_required_nonempty_str("skill_id", self.skill_id)
        if self.timeout_ms_override is not None and int(self.timeout_ms_override) < 1:
            raise ValueError("timeout_ms_override must be >= 1 when provided")
        self.inputs = _dict_any(self.inputs)
        self.metadata = _dict_any(self.metadata)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "skill_id": self.skill_id,
            "inputs": dict(self.inputs or {}),
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "request_id": self.request_id,
            "dry_run": bool(self.dry_run),
            "timeout_ms_override": self.timeout_ms_override,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SkillRunRequest":
        d = dict(data or {})
        return cls(
            schema_version=str(d.get("schema_version") or "aion.skill_run_request.v1"),
            skill_id=str(d.get("skill_id") or ""),
            inputs=_dict_any(d.get("inputs")),
            session_id=(str(d.get("session_id")) if d.get("session_id") is not None else None),
            turn_id=(str(d.get("turn_id")) if d.get("turn_id") is not None else None),
            request_id=(str(d.get("request_id")) if d.get("request_id") is not None else None),
            dry_run=bool(d.get("dry_run", False)),
            timeout_ms_override=(_safe_int(d.get("timeout_ms_override")) if d.get("timeout_ms_override") is not None else None),
            metadata=_dict_any(d.get("metadata")),
        )


@dataclass
class SkillRunResult:
    """
    Standardized execution result from skill adapter -> orchestrator.
    """
    schema_version: str = "aion.skill_run_result.v1"

    ok: bool = False
    skill_id: str = ""
    skill_run_id: str = ""

    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    error_code: Optional[str] = None

    latency_ms: int = 0
    safety_class: str = "internal_safe"
    status: str = "experimental"

    trace: Dict[str, Any] = field(default_factory=dict)
    telemetry_ref: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "SkillRunResult":
        _validate_required_nonempty_str("skill_id", self.skill_id)
        _validate_required_nonempty_str("skill_run_id", self.skill_run_id)

        if self.latency_ms < 0:
            raise ValueError("latency_ms must be >= 0")

        if self.status not in ALLOWED_STAGES:
            raise ValueError("status must be one of: experimental, verified, core")

        if self.safety_class not in ALLOWED_SAFETY_CLASSES:
            raise ValueError(f"safety_class must be one of: {sorted(ALLOWED_SAFETY_CLASSES)}")

        # normalize containers
        self.output = _dict_any(self.output)
        self.trace = _dict_any(self.trace)
        self.metadata = _dict_any(self.metadata)

        # ok + error is allowed (soft inconsistency) for backwards compatibility
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "ok": bool(self.ok),
            "skill_id": self.skill_id,
            "skill_run_id": self.skill_run_id,
            "output": dict(self.output or {}),
            "error": self.error,
            "error_code": self.error_code,
            "latency_ms": int(self.latency_ms),
            "safety_class": self.safety_class,
            "status": self.status,
            "trace": dict(self.trace or {}),
            "telemetry_ref": self.telemetry_ref,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SkillRunResult":
        d = dict(data or {})
        return cls(
            schema_version=str(d.get("schema_version") or "aion.skill_run_result.v1"),
            ok=bool(d.get("ok", False)),
            skill_id=str(d.get("skill_id") or ""),
            skill_run_id=str(d.get("skill_run_id") or ""),
            output=_dict_any(d.get("output")),
            error=(str(d.get("error")) if d.get("error") is not None else None),
            error_code=(str(d.get("error_code")) if d.get("error_code") is not None else None),
            latency_ms=_safe_int(d.get("latency_ms"), 0),
            safety_class=str(d.get("safety_class") or "internal_safe"),
            status=str(d.get("status") or "experimental"),
            trace=_dict_any(d.get("trace")),
            telemetry_ref=(str(d.get("telemetry_ref")) if d.get("telemetry_ref") is not None else None),
            metadata=_dict_any(d.get("metadata")),
        )


@dataclass
class SkillValidationCase:
    schema_version: str = "aion.skill_validation_case.v1"
    case_id: str = ""
    skill_id: str = ""
    request: Dict[str, Any] = field(default_factory=dict)
    expected: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def validate(self) -> "SkillValidationCase":
        _validate_required_nonempty_str("case_id", self.case_id)
        _validate_required_nonempty_str("skill_id", self.skill_id)
        self.request = _dict_any(self.request)
        self.expected = _dict_any(self.expected)
        self.tags = _list_str(self.tags)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "skill_id": self.skill_id,
            "request": dict(self.request or {}),
            "expected": dict(self.expected or {}),
            "tags": list(self.tags or []),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SkillValidationCase":
        d = _dict_any(data)
        return cls(
            schema_version=str(d.get("schema_version") or "aion.skill_validation_case.v1"),
            case_id=str(d.get("case_id") or ""),
            skill_id=str(d.get("skill_id") or ""),
            request=_dict_any(d.get("request")),
            expected=_dict_any(d.get("expected")),
            tags=_list_str(d.get("tags")),
        )


@dataclass
class SkillValidationResult:
    schema_version: str = "aion.skill_validation_result.v1"
    ok: bool = False
    case_id: str = ""
    skill_id: str = ""
    pass_rate: float = 0.0
    checks: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "SkillValidationResult":
        _validate_required_nonempty_str("case_id", self.case_id)
        _validate_required_nonempty_str("skill_id", self.skill_id)
        self.pass_rate = max(0.0, min(1.0, _safe_float(self.pass_rate, 0.0)))
        self.checks = _dict_any(self.checks)
        self.details = _dict_any(self.details)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "ok": bool(self.ok),
            "case_id": self.case_id,
            "skill_id": self.skill_id,
            "pass_rate": float(self.pass_rate),
            "checks": dict(self.checks or {}),
            "details": dict(self.details or {}),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SkillValidationResult":
        d = _dict_any(data)
        return cls(
            schema_version=str(d.get("schema_version") or "aion.skill_validation_result.v1"),
            ok=bool(d.get("ok", False)),
            case_id=str(d.get("case_id") or ""),
            skill_id=str(d.get("skill_id") or ""),
            pass_rate=_safe_float(d.get("pass_rate"), 0.0),
            checks=_dict_any(d.get("checks")),
            details=_dict_any(d.get("details")),
        )