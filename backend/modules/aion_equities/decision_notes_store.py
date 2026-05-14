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
    return Path(__file__).resolve().parent / "data" / "decision_notes"


def decision_notes_storage_path(
    decision_notes_id: str,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / f"{_safe_segment(decision_notes_id)}.json"


def build_decision_notes_payload(
    *,
    decision_notes_id: str,
    company_ref: str,
    proposal_id: str,
    decision_notes: Dict[str, Any],
    review_id: Optional[str] = None,
    thesis_ref: Optional[str] = None,
    generated_by: str = "aion_equities.decision_notes_store",
    created_at: Optional[str] = None,
    payload_patch: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    now = created_at or _utc_now_iso()
    payload: Dict[str, Any] = {
        "decision_notes_id": str(decision_notes_id),
        "review_id": str(review_id) if review_id is not None else None,
        "company_ref": str(company_ref),
        "proposal_id": str(proposal_id),
        "thesis_ref": str(thesis_ref) if thesis_ref is not None else None,
        "created_at": now,
        "generated_by": str(generated_by),
        "decision_notes": deepcopy(decision_notes or {}),
    }
    if payload_patch:
        payload.update(deepcopy(payload_patch))
    return payload


def save_decision_notes_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    path = decision_notes_storage_path(payload["decision_notes_id"], base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_decision_notes_payload(
    decision_notes_id: str,
    *,
    base_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    path = decision_notes_storage_path(decision_notes_id, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Decision notes not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


class DecisionNotesStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "decision_notes"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, decision_notes_id: str) -> Path:
        return decision_notes_storage_path(decision_notes_id, base_dir=self.base_dir)

    def save_decision_notes(
        self,
        *,
        company_ref: str,
        proposal_id: Optional[str] = None,
        proposal_ref: Optional[str] = None,
        review_id: Optional[str] = None,
        thesis_ref: Optional[str] = None,
        decision_notes: Optional[Dict[str, Any]] = None,
        notes: Optional[Dict[str, Any]] = None,
        generated_by: str = "aion_equities.decision_notes_store",
        decision_notes_id: Optional[str] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        proposal_id = proposal_id or proposal_ref
        if not proposal_id:
            raise TypeError("save_decision_notes() requires proposal_id or proposal_ref")

        final_notes = decision_notes if decision_notes is not None else notes
        if final_notes is None:
            final_notes = {}

        decision_notes_id = (
            decision_notes_id
            or f"decision_notes/{company_ref}/{proposal_id}"
        )

        payload = build_decision_notes_payload(
            decision_notes_id=decision_notes_id,
            review_id=review_id,
            company_ref=company_ref,
            proposal_id=proposal_id,
            thesis_ref=thesis_ref,
            decision_notes=final_notes,
            generated_by=generated_by,
            payload_patch=payload_patch,
        )
        save_decision_notes_payload(payload, base_dir=self.base_dir)
        return payload

    def load_decision_notes(self, decision_notes_id: str) -> Dict[str, Any]:
        return load_decision_notes_payload(decision_notes_id, base_dir=self.base_dir)

    def decision_notes_exists(self, decision_notes_id: str) -> bool:
        return self.storage_path(decision_notes_id).exists()

    def list_decision_notes_ids(self) -> List[str]:
        out: List[str] = []
        for path in sorted(self.base_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            did = payload.get("decision_notes_id")
            if isinstance(did, str) and did.strip():
                out.append(did.strip())
            else:
                out.append(path.stem.replace("_", "/"))
        return out


__all__ = [
    "DecisionNotesStore",
    "build_decision_notes_payload",
    "save_decision_notes_payload",
    "load_decision_notes_payload",
]