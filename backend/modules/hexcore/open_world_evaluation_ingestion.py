from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase53_54_external_ingestion_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_commitment(task_id: str, answer: Any, salt: str) -> str:
    return _canonical_hash(
        {"task_id": task_id, "answer": answer, "salt": salt}
    )


def freeze_phase53_protocol(
    *,
    state_path: Path,
    result_path: Path | None = None,
    code_commit: str,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    contract = {
        "schema_version": "aion.blind_external_evaluation.v1",
        "protocol_id": "phase53_blind_external_v1",
        "frozen_code_commit": code_commit,
        "accepted_families": [
            "reading",
            "research",
            "mathematics",
            "code",
            "science",
            "planning",
            "causal",
            "tool_use",
        ],
        "task_envelope_required": [
            "task_id",
            "family",
            "payload",
            "answer_commitment",
        ],
        "reveal_required": ["task_id", "answer", "salt"],
        "scoring_rules": {
            "labels_hidden_until_predictions_frozen": True,
            "commitment_must_match_reveal": True,
            "task_authors_must_be_external": True,
            "source_overlap_audit_required": True,
            "mean_and_worst_family_reported": True,
            "provider_and_tool_budgets_matched": True,
        },
        "promotion_authority": "external_evaluator_plus_CAU",
        "created_at": _utc_timestamp(),
    }
    runtime.store.state["blind_evaluation_protocols"][
        contract["protocol_id"]
    ] = contract
    runtime.store.commit(reason="phase53_blind_protocol_frozen")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    result = {
        "schema_version": "aion.hexcore.phase53_protocol.v1",
        "phase": 53,
        "infrastructure_complete": True,
        "capability_promoted": False,
        "protocol": contract,
        "restart": {
            "protocol_retained": contract["protocol_id"]
            in restarted.store.state["blind_evaluation_protocols"],
            "relearning_tasks": 0,
        },
        "blocked_gate": (
            "Final Phase 53 capability promotion requires sealed tasks and "
            "answer commitments supplied by an evaluator who did not develop "
            "the system. The developer process cannot self-certify independence."
        ),
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def score_blind_reveal(
    predictions: Mapping[str, Any],
    envelopes: Sequence[Mapping[str, Any]],
    reveals: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    reveal_by_id = {str(row["task_id"]): row for row in reveals}
    rows = []
    for envelope in envelopes:
        task_id = str(envelope["task_id"])
        reveal = reveal_by_id.get(task_id)
        if reveal is None:
            rows.append(
                {
                    "task_id": task_id,
                    "family": envelope["family"],
                    "valid_reveal": False,
                    "correct": False,
                }
            )
            continue
        expected = _canonical_commitment(
            task_id, reveal["answer"], str(reveal["salt"])
        )
        valid = expected == envelope["answer_commitment"]
        rows.append(
            {
                "task_id": task_id,
                "family": envelope["family"],
                "valid_reveal": valid,
                "correct": bool(valid and predictions.get(task_id) == reveal["answer"]),
            }
        )
    valid_rows = [row for row in rows if row["valid_reveal"]]
    families: Dict[str, List[bool]] = {}
    for row in valid_rows:
        families.setdefault(str(row["family"]), []).append(bool(row["correct"]))
    family_accuracy = {
        family: sum(values) / len(values) for family, values in families.items()
    }
    return {
        "tasks": len(rows),
        "valid_reveals": len(valid_rows),
        "invalid_reveals": len(rows) - len(valid_rows),
        "accuracy": sum(row["correct"] for row in valid_rows)
        / max(1, len(valid_rows)),
        "weakest_family_accuracy": min(family_accuracy.values(), default=0.0),
        "family_accuracy": family_accuracy,
        "rows": rows,
    }


def _pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader

        return "\n".join(page.extract_text() or "" for page in PdfReader(path))
    except Exception:
        return path.read_bytes().decode("utf-8", errors="ignore")


def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _pdf_text(path)
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        return json.dumps(payload, indent=2, sort_keys=True)
    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8", errors="ignore") as handle:
            return "\n".join(" | ".join(row) for row in csv.reader(handle))
    return path.read_text(encoding="utf-8", errors="ignore")


def _claim_candidates(text: str, maximum: int = 12) -> List[str]:
    candidates = []
    for line in text.splitlines():
        exact = line.strip()
        normalized = re.sub(r"\s+", " ", exact)
        if len(exact) < 18 or len(exact) > 280:
            continue
        if (
            re.search(r"\d", normalized)
            or "procedure_" in normalized
            or any(
                token in normalized.lower()
                for token in ("result", "accuracy", "phase", "status", "total")
            )
        ):
            candidates.append(exact)
        if len(candidates) >= maximum:
            break
    return candidates


def run_phase54_open_world_ingestion(
    *,
    state_path: Path,
    source_paths: Sequence[Path],
    result_path: Path | None = None,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    sources = []
    claims = []
    formats = set()
    for source_index, path in enumerate(source_paths):
        path = path.resolve()
        raw = path.read_bytes()
        text = _extract_text(path)
        source_id = f"source:{source_index:03d}:{_sha_bytes(raw)[:12]}"
        source = {
            "schema_version": "aion.open_world.source.v1",
            "source_id": source_id,
            "path": str(path),
            "format": path.suffix.lower().lstrip(".") or "text",
            "content_sha256": _sha_bytes(raw),
            "bytes": len(raw),
            "characters_extracted": len(text),
            "observed_at": _utc_timestamp(),
        }
        runtime.store.state["open_world_sources"][source_id] = source
        sources.append(source)
        formats.add(source["format"])
        for claim_index, claim_text in enumerate(_claim_candidates(text)):
            exact = claim_text in text
            claim_id = f"{source_id}:claim:{claim_index:02d}"
            claim = {
                "schema_version": "aion.open_world.claim.v1",
                "claim_id": claim_id,
                "source_id": source_id,
                "exact_evidence": claim_text,
                "evidence_location": {
                    "kind": "character_offset",
                    "start": text.find(claim_text),
                    "end": text.find(claim_text) + len(claim_text),
                },
                "source_sha256": source["content_sha256"],
                "reported_not_independently_verified": True,
                "evidence_exactly_recoverable": exact,
                "status": "reported",
            }
            runtime.store.state["open_world_claims"][claim_id] = claim
            claims.append(claim)
    gate = {
        "sources": len(sources),
        "formats": len(formats),
        "format_names": sorted(formats),
        "claims": len(claims),
        "source_hash_completeness": sum(
            len(source["content_sha256"]) == 64 for source in sources
        )
        / max(1, len(sources)),
        "evidence_recoverability": sum(
            claim["evidence_exactly_recoverable"] for claim in claims
        )
        / max(1, len(claims)),
        "provenance_completeness": sum(
            bool(claim["source_id"] and claim["source_sha256"])
            for claim in claims
        )
        / max(1, len(claims)),
        "reported_claims_mislabeled_as_verified": sum(
            claim["status"] == "verified" for claim in claims
        ),
    }
    errors = []
    if gate["sources"] < 8:
        errors.append("FEWER_THAN_EIGHT_REAL_SOURCES")
    if gate["formats"] < 5:
        errors.append("FEWER_THAN_FIVE_FORMATS")
    if gate["claims"] < 20:
        errors.append("INSUFFICIENT_RECOVERABLE_CLAIMS")
    if gate["source_hash_completeness"] < 1.0:
        errors.append("SOURCE_HASH_INCOMPLETE")
    if gate["evidence_recoverability"] < 1.0:
        errors.append("EVIDENCE_NOT_EXACTLY_RECOVERABLE")
    if gate["reported_claims_mislabeled_as_verified"]:
        errors.append("REPORTED_CLAIM_FALSELY_VERIFIED")
    gate["errors"] = errors
    gate["accepted"] = not errors
    candidate = ProcedureCandidate(
        procedure_id="procedure_open_world_ingestion_"
        + _canonical_hash(gate)[:12],
        goal="open_world_knowledge_ingestion",
        steps=[
            "detect_source_format",
            "extract_without_mutating_source",
            "hash_source_content",
            "locate_exact_claim_evidence",
            "separate_reported_from_verified",
            "persist_provenance_graph",
        ],
        score=gate["formats"] + gate["evidence_recoverability"],
        success=gate["accepted"],
        evidence={"gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.store.commit(reason="phase54_open_world_ingestion")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    restart = {
        "sources_retained": len(restarted.store.state["open_world_sources"])
        == len(sources),
        "claims_retained": len(restarted.store.state["open_world_claims"])
        == len(claims),
        "champion_retained": restarted.store.state["champions"].get(
            "open_world_knowledge_ingestion"
        )
        == candidate.procedure_id,
        "relearning_sources": 0,
    }
    result = {
        "schema_version": "aion.hexcore.open_world_ingestion.v1",
        "phase": 54,
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and all(
                (
                    restart["sources_retained"],
                    restart["claims_retained"],
                    restart["champion_retained"],
                )
            )
        ),
        "gate": gate,
        "sources": sources,
        "claims": claims,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "boundary": (
            "Phase 54 V1 ingests real multi-format files and preserves exact "
            "reported claims. It does not independently establish the truth "
            "of arbitrary claims or understand every media format."
        ),
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
