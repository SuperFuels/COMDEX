from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import json
import hashlib


DEFAULT_TRACE_PATH = Path(".runtime/workflow_capsules/runs/workflow_execution_log.jsonl")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def _stable_hash(payload: Dict[str, Any]) -> str:
    return hashlib.sha3_256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


class WorkflowCapsuleTraceWriter:
    """
    Append-only WorkflowLog writer.

    This is intentionally separate from execution so dry-runs, approvals,
    live runs, failures, and later feedback/reinforcement can all write the
    same stable audit stream.

    This does not update capsule resonance/habit memory by itself.
    Feedback remains CAU-gated in a later layer.
    """

    def __init__(self, path: Path | str = DEFAULT_TRACE_PATH) -> None:
        self.path = Path(path)

    def append(
        self,
        *,
        event_type: str,
        capsule: Any,
        run_result: Any = None,
        policy_result: Any = None,
        expansion_result: Any = None,
        cau_state: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cau_state = dict(cau_state or {})
        extra = dict(extra or {})

        capsule_key = getattr(capsule, "canonical_key", None)
        display_name = getattr(capsule, "display_name", None)
        capsule_checksum = None

        meta = getattr(capsule, "meta", {}) or {}
        if isinstance(meta, dict):
            capsule_checksum = meta.get("checksum")

        run_payload = _jsonable(run_result) if run_result is not None else None
        policy_payload = _jsonable(policy_result) if policy_result is not None else None
        expansion_payload = _jsonable(expansion_result) if expansion_result is not None else None

        run_id = None
        if isinstance(run_payload, dict):
            run_id = run_payload.get("run_id")

        record: Dict[str, Any] = {
            "schema_version": "aion.workflow_execution_log.v1",
            "ts": _utc_now_iso(),
            "event_type": event_type,
            "canonical_key": capsule_key,
            "display_name": display_name,
            "capsule_checksum": capsule_checksum,
            "run_id": run_id,
            "cau": {
                "allow_learn": cau_state.get("allow_learn"),
                "adr_active": cau_state.get("adr_active"),
                "deny_reason": cau_state.get("deny_reason"),
            },
            "policy": policy_payload,
            "expansion": expansion_payload,
            "run": run_payload,
            "extra": extra,
        }

        record["trace_hash"] = _stable_hash({
            k: v for k, v in record.items() if k != "trace_hash"
        })

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

        return {
            "ok": True,
            "path": str(self.path),
            "event_type": event_type,
            "canonical_key": capsule_key,
            "run_id": run_id,
            "trace_hash": record["trace_hash"],
        }
