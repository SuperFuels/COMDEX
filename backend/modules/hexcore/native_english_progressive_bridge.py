"""Bridge independently verified native-English outcomes into the broad ledger.

The native English academy and the progressive curriculum have separate stores.
Without an explicit bridge, the broad ledger continued to report lexical,
syntax and reference skills as absent even after their model-free examinations
had passed.  This module imports a small, finite set of frozen receipts.  It
never converts dictionary size, teacher output or ordinary practice into
competence, and it never awards delayed retention.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Mapping

from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem


SCHEMA = "aion.hexcore.native_english_progressive_bridge.v1"


def _atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*, repo_root: Path, result_path: Path, maximum_snapshot_age_seconds: float = 7200.0) -> dict[str, Any]:
    snapshot_path = repo_root / "data/aion/native_english_teacher/progress_snapshot.json"
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        payload = {
            "schema_version": SCHEMA, "status": "snapshot_unavailable", "passed": False,
            "imported": [], "error": f"{type(exc).__name__}:{exc}",
        }
        _atomic(result_path, payload)
        return payload

    generated_epoch = float(snapshot.get("generated_epoch") or 0.0)
    age_seconds = max(0.0, time.time() - generated_epoch) if generated_epoch else float("inf")
    memory = snapshot.get("memory") or {}
    stages = {str(row.get("id")): row for row in snapshot.get("curriculum") or []}
    discourse = snapshot.get("discourse_dialogue") or {}
    conversation = snapshot.get("open_conversation_academy") or {}

    sentence_stage = stages.get("sentence_semantics") or {}
    lexical_checks = {
        "snapshot_fresh": age_seconds <= maximum_snapshot_age_seconds,
        "learning_healthy": snapshot.get("health") == "healthy",
        "acquired_senses": int(memory.get("acquired_senses") or 0) >= 1_000,
        "closed_book_accuracy": float(memory.get("practice_accuracy") or 0.0) >= 0.85,
    }
    syntax_checks = {
        "snapshot_fresh": age_seconds <= maximum_snapshot_age_seconds,
        "sentence_layer_completed": sentence_stage.get("status") == "completed",
        "sentence_accuracy": float(sentence_stage.get("accuracy") or 0.0) >= 0.88,
        "source_disjoint": int(sentence_stage.get("source_disjoint_attempts") or 0) > 0,
    }
    dialogue_checks = {
        "snapshot_fresh": age_seconds <= maximum_snapshot_age_seconds,
        "twenty_turn_exams": int(conversation.get("exams") or 0) >= 2,
        "conversation_accuracy": float(conversation.get("accuracy") or 0.0) >= 0.90,
        "evidence_supported": float(conversation.get("evidence_supported_rate") or 0.0) >= 0.95,
        "unsupported_claim_rate": float(
            conversation.get("unsupported_claim_rate")
            if conversation.get("unsupported_claim_rate") is not None else 1.0
        ) < 0.02,
        "discourse_accuracy": float(discourse.get("accuracy") or 0.0) >= 0.85,
        "student_model_absent": conversation.get("student_model_used") is False,
    }
    proofs = (
        {
            "family": "native_english_bridge_lexical_v1", "kind": "knowledge_test",
            "subskills": ["lexical_grounding", "semantic_relations"], "checks": lexical_checks,
            "score": float(memory.get("practice_accuracy") or 0.0), "trials": 1,
            "source_disjoint": False, "unfamiliar": False,
            "authority": ["native_lexical_sqlite", "withheld_answer_key", "model_free_exam"],
        },
        {
            "family": "native_english_bridge_sentence_v1", "kind": "exercise",
            "subskills": ["morphology", "syntax", "sentence_semantics"], "checks": syntax_checks,
            "score": float(sentence_stage.get("accuracy") or 0.0), "trials": 1,
            "source_disjoint": True, "unfamiliar": False,
            "authority": ["native_sentence_semantics_exam", "source_disjoint_tasks", "model_free_exam"],
        },
        {
            "family": "native_english_bridge_dialogue_v1", "kind": "transfer",
            "subskills": ["native_question_answering", "reference_resolution"], "checks": dialogue_checks,
            "score": float(conversation.get("accuracy") or 0.0),
            "trials": int(conversation.get("turns") or 1),
            "source_disjoint": True, "unfamiliar": True,
            "authority": ["source_disjoint_twenty_turn_exam", "evidence_map", "student_model_absent"],
        },
    )

    system = ProgressiveCompetencySystem(
        repo_root=repo_root,
        state_path=repo_root / "backend/modules/hexcore/data/progressive_competency/state.json",
    )
    existing = {str(row.get("project_family")) for row in system.evidence_for("english")}
    receipt_dir = result_path.parent / "native_english_bridge_receipts"
    imported: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    retained: list[str] = []
    for proof in proofs:
        family = str(proof["family"])
        if family in existing:
            retained.append(family)
            continue
        if not all((proof.get("checks") or {}).values()):
            rejected.append({"family": family, "checks": proof["checks"]})
            continue
        receipt = {
            "schema_version": SCHEMA, "family": family,
            "source_snapshot_generated_epoch": generated_epoch,
            "source_snapshot_sha256": _sha256(snapshot_path),
            "checks": proof["checks"], "score": proof["score"],
            "subskills": proof["subskills"], "kind": proof["kind"],
            "claim_boundary": (
                "This receipt imports named, model-free examination evidence only. It does not "
                "award broad English mastery or substitute for delayed retention."
            ),
        }
        receipt_path = receipt_dir / f"{family}.json"
        if not receipt_path.exists():
            _atomic(receipt_path, receipt)
        artifact_hash = _sha256(receipt_path)
        evidence = system.record_evidence(
            subject_id="english", kind=str(proof["kind"]), subskills=proof["subskills"],
            score=min(1.0, max(0.0, float(proof["score"]))),
            artifact=str(receipt_path.relative_to(repo_root)), artifact_hash=artifact_hash,
            verified=True, source_disjoint=bool(proof["source_disjoint"]), retained=False,
            independent_outcome=True, unfamiliar=bool(proof["unfamiliar"]), scaffolding=0.05,
            trials=max(1, int(proof["trials"])), authority=proof["authority"],
            project_family=family, experience_class="native_english_model_free_exam_bridge",
        )
        imported.append({"family": family, "evidence_id": evidence["evidence_id"]})
        existing.add(family)

    assessment = system.assess("english")
    payload = {
        "schema_version": SCHEMA,
        "status": "evidence_bridge_active" if not rejected else "partial_evidence_bridge",
        "passed": not rejected, "snapshot_age_seconds": age_seconds,
        "imported": imported, "retained": retained, "rejected": rejected,
        "english_assessment": {
            key: assessment[key] for key in (
                "knowledge_level", "practical_level", "overall_level", "target_level",
                "evidence_records", "transfer_cases", "retention_cases",
            )
        },
        "claim_boundary": (
            "Only frozen native-English examination receipts enter the general ledger. Dictionary "
            "volume, teacher drafts and practice counters do not grant competency."
        ),
    }
    _atomic(result_path, payload)
    return payload


__all__ = ["run"]
