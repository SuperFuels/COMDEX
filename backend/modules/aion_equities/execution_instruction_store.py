from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


def _default_storage_dir() -> Path:
    return Path(__file__).resolve().parent / "data" / "execution_instructions"


def execution_instruction_storage_path(
    execution_instruction_id: str,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / f"{_safe_segment(execution_instruction_id)}.json"


def build_execution_instruction_payload(
    *,
    execution_instruction_id: str,
    company_ref: str,
    proposal_id: str,
    execution_instruction: Dict[str, Any],
    review_id: Optional[str] = None,
    thesis_ref: Optional[str] = None,
    approval_state: str = "pending_human_approval",
    instruction_status: str = "pending_guardrail_review",
    generated_by: str = "aion_equities.execution_instruction_store",
    created_at: Optional[str] = None,
    payload_patch: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    now = created_at or _utc_now_iso()
    payload: Dict[str, Any] = {
        "execution_instruction_id": str(execution_instruction_id),
        "review_id": str(review_id) if review_id is not None else None,
        "company_ref": str(company_ref),
        "proposal_id": str(proposal_id),
        "thesis_ref": str(thesis_ref) if thesis_ref is not None else None,
        "created_at": now,
        "generated_by": str(generated_by),
        "approval_state": str(approval_state),
        "instruction_status": str(instruction_status),
        "execution_instruction": deepcopy(execution_instruction or {}),
    }
    if payload_patch:
        payload.update(deepcopy(payload_patch))
    return payload


def save_execution_instruction_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    path = execution_instruction_storage_path(payload["execution_instruction_id"], base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_execution_instruction_payload(
    execution_instruction_id: str,
    *,
    base_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    path = execution_instruction_storage_path(execution_instruction_id, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Execution instruction not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


class ExecutionInstructionStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "execution_instructions"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, execution_instruction_id: str) -> Path:
        return execution_instruction_storage_path(execution_instruction_id, base_dir=self.base_dir)

    def save_execution_instruction(
        self,
        *,
        company_ref: str,
        proposal_id: Optional[str] = None,
        proposal_ref: Optional[str] = None,
        review_id: Optional[str] = None,
        thesis_ref: Optional[str] = None,
        execution_instruction: Optional[Dict[str, Any]] = None,
        instruction: Optional[Dict[str, Any]] = None,
        approval_state: str = "pending_human_approval",
        instruction_status: str = "pending_guardrail_review",
        generated_by: str = "aion_equities.execution_instruction_store",
        execution_instruction_id: Optional[str] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        proposal_id = proposal_id or proposal_ref
        if not proposal_id:
            raise TypeError("save_execution_instruction() requires proposal_id or proposal_ref")

        final_instruction = execution_instruction if execution_instruction is not None else instruction
        if final_instruction is None:
            final_instruction = {}

        execution_instruction_id = (
            execution_instruction_id
            or f"execution_instruction/{company_ref}/{proposal_id}"
        )

        payload = build_execution_instruction_payload(
            execution_instruction_id=execution_instruction_id,
            review_id=review_id,
            company_ref=company_ref,
            proposal_id=proposal_id,
            thesis_ref=thesis_ref,
            execution_instruction=final_instruction,
            approval_state=approval_state,
            instruction_status=instruction_status,
            generated_by=generated_by,
            payload_patch=payload_patch,
        )
        save_execution_instruction_payload(payload, base_dir=self.base_dir)
        return payload

    def load_execution_instruction(self, execution_instruction_id: str) -> Dict[str, Any]:
        return load_execution_instruction_payload(execution_instruction_id, base_dir=self.base_dir)

    def execution_instruction_exists(self, execution_instruction_id: str) -> bool:
        return self.storage_path(execution_instruction_id).exists()

    def list_execution_instruction_ids(self) -> List[str]:
        out: List[str] = []
        for path in sorted(self.base_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            iid = payload.get("execution_instruction_id")
            if isinstance(iid, str) and iid.strip():
                out.append(iid.strip())
            else:
                out.append(path.stem.replace("_", "/"))
        return out


__all__ = [
    "ExecutionInstructionStore",
    "build_execution_instruction_payload",
    "save_execution_instruction_payload",
    "load_execution_instruction_payload",
]