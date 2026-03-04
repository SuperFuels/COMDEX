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


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def _default_storage_dir() -> Path:
    return Path(__file__).resolve().parent / "data" / "openai_review_artifacts"


def review_artifact_storage_path(
    review_artifact_id: str,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / f"{_safe_segment(review_artifact_id)}.json"


def save_review_artifact_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    path = review_artifact_storage_path(payload["review_artifact_id"], base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def build_review_artifact_payload(
    *,
    review_artifact_id: str,
    review_id: str,
    company_ref: str,
    proposal_id: str,
    context_packet: Dict[str, Any],
    raw_response: Dict[str, Any],
    decision_notes_payload: Dict[str, Any],
    execution_instruction_payload: Dict[str, Any],
    thesis_ref: Optional[str] = None,
    generated_by: str = "aion_equities.openai_review_artifact_store",
    payload_patch: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    now = _utc_now_iso()

    payload: Dict[str, Any] = {
        "review_artifact_id": str(review_artifact_id),
        "review_id": str(review_id),
        "company_ref": str(company_ref),
        "proposal_id": str(proposal_id),
        "thesis_ref": thesis_ref,
        "generated_by": str(generated_by),
        "created_at": now,
        "updated_at": now,
        "context_packet": deepcopy(context_packet or {}),
        "raw_response": deepcopy(raw_response or {}),
        "decision_notes_payload": deepcopy(decision_notes_payload or {}),
        "execution_instruction_payload": deepcopy(execution_instruction_payload or {}),
    }

    if payload_patch:
        payload = _deep_merge(payload, payload_patch)

    payload["updated_at"] = _utc_now_iso()
    return payload


def load_review_artifact_payload(
    review_artifact_id: str,
    *,
    base_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    path = review_artifact_storage_path(review_artifact_id, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"OpenAI review artifact not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


class OpenAIReviewArtifactStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "openai_review_artifacts"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, review_artifact_id: str) -> Path:
        return review_artifact_storage_path(review_artifact_id, base_dir=self.base_dir)

    def save_review_artifact(
        self,
        *,
        review_id: str,
        company_ref: str,
        proposal_id: str,
        context_packet: Dict[str, Any],
        raw_response: Dict[str, Any],
        decision_notes_payload: Dict[str, Any],
        execution_instruction_payload: Dict[str, Any],
        thesis_ref: Optional[str] = None,
        review_artifact_id: Optional[str] = None,
        generated_by: str = "aion_equities.openai_review_artifact_store",
        payload_patch: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        review_artifact_id = review_artifact_id or f"review_artifact/{company_ref}/{proposal_id}"

        payload = build_review_artifact_payload(
            review_artifact_id=review_artifact_id,
            review_id=review_id,
            company_ref=company_ref,
            proposal_id=proposal_id,
            thesis_ref=thesis_ref,
            context_packet=context_packet,
            raw_response=raw_response,
            decision_notes_payload=decision_notes_payload,
            execution_instruction_payload=execution_instruction_payload,
            generated_by=generated_by,
            payload_patch=payload_patch,
        )
        save_review_artifact_payload(payload, base_dir=self.base_dir)
        return payload

    def load_review_artifact(self, review_artifact_id: str) -> Dict[str, Any]:
        return load_review_artifact_payload(review_artifact_id, base_dir=self.base_dir)

    def review_artifact_exists(self, review_artifact_id: str) -> bool:
        return self.storage_path(review_artifact_id).exists()

    def list_review_artifact_ids(self) -> List[str]:
        out: List[str] = []
        for path in sorted(self.base_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            rid = payload.get("review_artifact_id")
            if isinstance(rid, str) and rid.strip():
                out.append(rid.strip())
            else:
                out.append(path.stem.replace("_", "/"))
        return out


__all__ = [
    "OpenAIReviewArtifactStore",
    "build_review_artifact_payload",
    "save_review_artifact_payload",
    "load_review_artifact_payload",
]