from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


MEMORY_RECORD_SCHEMA_VERSION = "aion.goal_engine.memory_record.v1"
MEMORY_POLICY_SCHEMA_VERSION = "aion.goal_engine.memory_policy.v1"

SUPPORTED_MEMORY_TIERS = {
    "working",
    "session",
    "goal",
    "episodic_run",
    "semantic_glyph",
    "long_term_advisory",
}

SUPPORTED_RETENTION_POLICIES = {
    "ephemeral",
    "session_only",
    "goal_lifetime",
    "timeboxed",
    "long_term",
    "manual_review",
}

SUPPORTED_GUARD_DECISIONS = {
    "allow",
    "deny",
    "human_review",
}


@dataclass
class MemoryRecordContract:
    memory_id: str
    tier: str
    content_ref: str
    source_ref: str
    provenance: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    created_at: str | None = None
    expires_at: str | None = None
    goal_id: str | None = None
    glyph_code: str | None = None
    run_id: str | None = None
    tags: list[str] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not str(self.memory_id or "").strip():
            errors.append("memory_id_required")

        if self.tier not in SUPPORTED_MEMORY_TIERS:
            errors.append("unsupported_memory_tier")

        if not str(self.content_ref or "").strip():
            errors.append("content_ref_required")

        if not str(self.source_ref or "").strip():
            errors.append("source_ref_required")

        if not isinstance(self.provenance, dict):
            errors.append("provenance_required")

        try:
            confidence = float(self.confidence)
        except Exception:
            confidence = -1.0

        if confidence < 0.0 or confidence > 1.0:
            errors.append("confidence_out_of_range")

        return errors


@dataclass
class MemoryPolicyContract:
    policy_id: str
    tier: str
    retention_policy: str
    write_guard: str = "human_review"
    read_guard: str = "allow"
    allow_forgetting: bool = True
    allow_consolidation: bool = False
    max_records: int = 100
    expiry_required: bool = False
    provenance_required: bool = True

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not str(self.policy_id or "").strip():
            errors.append("policy_id_required")

        if self.tier not in SUPPORTED_MEMORY_TIERS:
            errors.append("unsupported_memory_tier")

        if self.retention_policy not in SUPPORTED_RETENTION_POLICIES:
            errors.append("unsupported_retention_policy")

        if self.write_guard not in SUPPORTED_GUARD_DECISIONS:
            errors.append("unsupported_write_guard")

        if self.read_guard not in SUPPORTED_GUARD_DECISIONS:
            errors.append("unsupported_read_guard")

        if int(self.max_records or 0) <= 0:
            errors.append("max_records_required")

        if self.retention_policy == "long_term" and self.write_guard != "human_review":
            errors.append("long_term_memory_requires_human_review_write_guard")

        if self.expiry_required and self.retention_policy not in {"ephemeral", "session_only", "timeboxed"}:
            errors.append("expiry_required_policy_mismatch")

        return errors


def build_memory_record_preview(record: MemoryRecordContract | dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, MemoryRecordContract):
        record = MemoryRecordContract(
            memory_id=str(record.get("memory_id", "")),
            tier=str(record.get("tier", "")),
            content_ref=str(record.get("content_ref", "")),
            source_ref=str(record.get("source_ref", "")),
            provenance=dict(record.get("provenance") or {}),
            confidence=float(record.get("confidence") or 0.0),
            created_at=record.get("created_at"),
            expires_at=record.get("expires_at"),
            goal_id=record.get("goal_id"),
            glyph_code=record.get("glyph_code"),
            run_id=record.get("run_id"),
            tags=list(record.get("tags") or []),
        )

    errors = record.validate()

    return {
        "schema_version": MEMORY_RECORD_SCHEMA_VERSION,
        "trace_type": "memory_record_preview",
        "memory_id": record.memory_id,
        "tier": record.tier,
        "content_ref": record.content_ref,
        "source_ref": record.source_ref,
        "provenance": dict(record.provenance),
        "confidence": float(record.confidence or 0.0),
        "created_at": record.created_at,
        "expires_at": record.expires_at,
        "goal_id": record.goal_id,
        "glyph_code": record.glyph_code,
        "run_id": record.run_id,
        "tags": list(record.tags or []),
        "valid": not errors,
        "blocked_reasons": errors,
        "would_write_memory": False,
        "dry_run_only": True,
    }


def build_memory_policy_preview(policy: MemoryPolicyContract | dict[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, MemoryPolicyContract):
        policy = MemoryPolicyContract(
            policy_id=str(policy.get("policy_id", "")),
            tier=str(policy.get("tier", "")),
            retention_policy=str(policy.get("retention_policy", "")),
            write_guard=str(policy.get("write_guard", "human_review")),
            read_guard=str(policy.get("read_guard", "allow")),
            allow_forgetting=bool(policy.get("allow_forgetting", True)),
            allow_consolidation=bool(policy.get("allow_consolidation", False)),
            max_records=int(policy.get("max_records") or 100),
            expiry_required=bool(policy.get("expiry_required", False)),
            provenance_required=bool(policy.get("provenance_required", True)),
        )

    errors = policy.validate()

    return {
        "schema_version": MEMORY_POLICY_SCHEMA_VERSION,
        "trace_type": "memory_policy_preview",
        "policy_id": policy.policy_id,
        "tier": policy.tier,
        "retention_policy": policy.retention_policy,
        "write_guard": policy.write_guard,
        "read_guard": policy.read_guard,
        "allow_forgetting": policy.allow_forgetting,
        "allow_consolidation": policy.allow_consolidation,
        "max_records": int(policy.max_records or 0),
        "expiry_required": policy.expiry_required,
        "provenance_required": policy.provenance_required,
        "valid": not errors,
        "blocked_reasons": errors,
        "would_write_memory": False,
        "dry_run_only": True,
    }
