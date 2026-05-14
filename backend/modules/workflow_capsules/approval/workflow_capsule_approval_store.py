"""
Workflow Capsule Approval Store - AION Workflow Glyph Capsules v1
────────────────────────────────────────────────────────────────
Local append-only approval gate for capsule-native workflow glyph dry-runs.

Purpose:
  dry-run result
    -> pending approval request
    -> human approve/reject
    -> resume gate checks approval + vault requirements

This does not send emails or perform live external writes.
It only records approval state and allows the runner to prove that an approved
workflow is ready for a connector execution layer later.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import hashlib
import json
import uuid


SCHEMA_VERSION = "aion.workflow_capsule_approval.v1"
LOG_SCHEMA_VERSION = "aion.workflow_capsule_approval_log.v1"

DEFAULT_APPROVAL_DIR = Path(".runtime/workflow_capsules/approvals/items")
DEFAULT_APPROVAL_LOG = Path(".runtime/workflow_capsules/approvals/workflow_approvals.jsonl")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _hash_dict(value: Dict[str, Any]) -> str:
    return hashlib.sha3_256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _safe_id(value: str, fallback: str = "approval") -> str:
    raw = str(value or fallback).strip() or fallback
    out = []
    for ch in raw:
        if ch.isalnum() or ch in {"_", "-", "."}:
            out.append(ch)
        else:
            out.append("_")
    return "".join(out).strip("_") or fallback


@dataclass
class WorkflowApprovalRequest:
    approval_id: str
    run_id: str
    canonical_key: str
    display_name: str

    status: str = "pending"
    approval_type: str = "human"
    reason: str = "Workflow requires approval."

    external_write_step_id: Optional[str] = None
    approval_ref: Optional[str] = None

    requested_by: str = "aion.workflow_capsule.runner"
    created_at: str = field(default_factory=_utc_now_iso)

    decided_at: Optional[str] = None
    decision: Optional[str] = None
    decided_by: Optional[str] = None
    decision_reason: Optional[str] = None

    payload: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["schema_version"] = SCHEMA_VERSION
        data["approval_hash"] = _hash_dict(
            {k: v for k, v in data.items() if k != "approval_hash"}
        )
        return data


class WorkflowCapsuleApprovalStore:
    def __init__(
        self,
        *,
        approval_dir: Path | str = DEFAULT_APPROVAL_DIR,
        approval_log: Path | str = DEFAULT_APPROVAL_LOG,
    ) -> None:
        self.approval_dir = Path(approval_dir)
        self.approval_log = Path(approval_log)

    def approval_path(self, approval_id: str) -> Path:
        return self.approval_dir / f"{_safe_id(approval_id)}.json"

    def create(
        self,
        *,
        run_id: str,
        canonical_key: str,
        display_name: str,
        reason: str,
        external_write_step_id: Optional[str] = None,
        approval_ref: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        approval_id = f"wf_appr_{uuid.uuid4().hex[:12]}"

        req = WorkflowApprovalRequest(
            approval_id=approval_id,
            run_id=run_id,
            canonical_key=canonical_key,
            display_name=display_name,
            reason=reason,
            external_write_step_id=external_write_step_id,
            approval_ref=approval_ref,
            payload=payload or {},
            meta=meta or {},
        )

        data = req.to_dict()
        self._write_item(data)
        self._append_log("approval_created", data)

        return {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "approval_id": approval_id,
            "run_id": run_id,
            "canonical_key": canonical_key,
            "status": "pending",
            "path": str(self.approval_path(approval_id)),
        }

    def get(self, approval_id: str) -> Optional[Dict[str, Any]]:
        path = self.approval_path(approval_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list(
        self,
        *,
        status: Optional[str] = None,
        canonical_key: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        status_norm = str(status or "").strip().lower()
        key_norm = str(canonical_key or "").strip()
        limit = max(1, min(int(limit or 100), 500))

        if not self.approval_dir.exists():
            return []

        items: List[Dict[str, Any]] = []
        for path in sorted(self.approval_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue

            if status_norm and str(data.get("status") or "").strip().lower() != status_norm:
                continue

            if key_norm and str(data.get("canonical_key") or "").strip() != key_norm:
                continue

            items.append(data)
            if len(items) >= limit:
                break

        return items

    def decide(
        self,
        approval_id: str,
        *,
        decision: str,
        decided_by: str = "human",
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        decision_norm = str(decision or "").strip().lower()
        if decision_norm not in {"approved", "rejected"}:
            return {
                "ok": False,
                "approval_id": approval_id,
                "error": "decision_must_be_approved_or_rejected",
            }

        data = self.get(approval_id)
        if not data:
            return {
                "ok": False,
                "approval_id": approval_id,
                "error": "approval_not_found",
            }

        if data.get("status") != "pending":
            return {
                "ok": False,
                "approval_id": approval_id,
                "status": data.get("status"),
                "error": "approval_already_decided",
            }

        data["status"] = decision_norm
        data["decision"] = decision_norm
        data["decided_by"] = decided_by
        data["decision_reason"] = reason
        data["decided_at"] = _utc_now_iso()
        data["approval_hash"] = _hash_dict(
            {k: v for k, v in data.items() if k != "approval_hash"}
        )

        self._write_item(data)
        self._append_log(f"approval_{decision_norm}", data)

        return {
            "ok": True,
            "approval_id": approval_id,
            "run_id": data.get("run_id"),
            "canonical_key": data.get("canonical_key"),
            "status": decision_norm,
            "decision": decision_norm,
        }

    def _write_item(self, data: Dict[str, Any]) -> None:
        self.approval_dir.mkdir(parents=True, exist_ok=True)
        path = self.approval_path(str(data["approval_id"]))
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        tmp.replace(path)

    def _append_log(self, event_type: str, data: Dict[str, Any]) -> None:
        self.approval_log.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "schema_version": LOG_SCHEMA_VERSION,
            "ts": _utc_now_iso(),
            "event_type": event_type,
            "approval": data,
        }
        with self.approval_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
