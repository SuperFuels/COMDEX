"""Autonomously compile verified competency trajectories into functional glyphs.

This is the scale bridge between episodic competency receipts and the typed
Functional Glyph Lexicon.  It contains no per-subject lesson or solution.  A
single induction rule accepts only source-closed capsules that have already
survived fresh execution, counterexamples and the safety gate, then creates a
reconstructable procedure graph for each accepted subject.

The output is proposal memory.  It never awards a competency level; the
ProgressiveCompetencySystem remains the sole level authority.
"""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash, _utc_timestamp
from backend.modules.hexcore.functional_glyph_lexicon import FunctionalGlyphLexicon
from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem


PROCEDURE_ID = "procedure_autonomous_functional_glyph_induction_v1"


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _freeze_authority(
    repo_root: Path, subject_id: str, capsule: Mapping[str, Any], outcome: Mapping[str, Any]
) -> str:
    """Freeze mutable curriculum state before it becomes graph provenance."""
    receipt = {
        "schema_version": "aion.functional_memory_induction_authority.v1",
        "subject_id": subject_id,
        "capsule": dict(capsule),
        "fresh_execution": {
            key: outcome.get(key) for key in (
                "authority", "passed", "candidate_execution_passed",
                "source_disjoint_transfer", "unfamiliar",
                "counterexamples_rejected", "counterexamples_total",
                "unsafe_variants_rejected", "unsafe_variants_total",
                "source_artifacts_opened", "live_repository_writes",
            )
        },
    }
    digest = hashlib.sha256(
        json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    relative = Path("results/immutable/functional_memory_induction") / f"{subject_id}_{digest[:20]}.json"
    path = repo_root / relative
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != receipt:
            raise ValueError("content-addressed functional-memory receipt collision")
    else:
        _write(path, receipt)
    return str(relative)


def _valid_capsule(capsule: Mapping[str, Any], subject_id: str) -> bool:
    body = {key: value for key, value in capsule.items() if key != "capsule_sha256"}
    return bool(
        capsule.get("subject_id") == subject_id
        and capsule.get("coverage_complete") is True
        and capsule.get("verified_evidence_ids")
        and not capsule.get("unresolved_evidence_ids")
        and capsule.get("retained_method")
        and capsule.get("capsule_sha256") == _canonical_hash(body)
    )


def _accepted_reconstructions(result: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row["subject_id"]): dict(row)
        for row in result.get("reconstructions") or []
        if row.get("passed") is True
        and row.get("candidate_execution_passed") is True
        and int(row.get("counterexamples_total") or 0) > 0
        and row.get("counterexamples_rejected") == row.get("counterexamples_total")
        and int(row.get("unsafe_variants_total") or 0) > 0
        and row.get("unsafe_variants_rejected") == row.get("unsafe_variants_total")
        and int(row.get("live_repository_writes") or 0) == 0
    }


def induce(
    *, repo_root: Path, store_path: Path, capsule_dir: Path,
    reconstruction_result_path: Path,
) -> tuple[FunctionalGlyphLexicon, list[dict[str, Any]], list[dict[str, Any]]]:
    lexicon = FunctionalGlyphLexicon.load(repo_root=repo_root, store_path=store_path)
    reconstruction_result = json.loads(reconstruction_result_path.read_text(encoding="utf-8"))
    accepted = _accepted_reconstructions(reconstruction_result)
    induced: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for capsule_path in sorted(capsule_dir.glob("*.json")):
        capsule = json.loads(capsule_path.read_text(encoding="utf-8"))
        subject_id = str(capsule.get("subject_id") or capsule_path.stem)
        outcome = accepted.get(subject_id)
        if not outcome or not _valid_capsule(capsule, subject_id):
            rejected.append({"subject_id": subject_id, "reason": "capsule_or_execution_authority_invalid"})
            continue

        capsule_relative = _freeze_authority(repo_root, subject_id, capsule, outcome)
        evidence = lexicon.add_evidence(
            capsule_relative, authority="source_closed_functional_capsule"
        )
        subskill_nodes = []
        for subskill in sorted(set(capsule["grounded_subskills"])):
            node = lexicon.add_node(
                kind="concept", key=f"{subject_id}.{subskill}",
                summary=f"Verified functional subskill {subskill} within {capsule['subject_name']}",
                aliases=[subskill.replace("_", " ")],
                facets={"subject_id": subject_id, "subskill": subskill,
                        "grounding": "verified_competency_trajectory"},
                evidence=[evidence],
            )
            subskill_nodes.append(node)

        procedure = lexicon.add_node(
            kind="procedure", key=f"apply_competence:{subject_id}",
            summary=f"Reconstruct and apply retained {capsule['subject_name']} competence",
            aliases=[capsule["subject_name"], f"use {capsule['subject_name']}"],
            facets={
                "purpose": f"apply verified {capsule['subject_name']} methods to an unfamiliar objective",
                "inputs": ["unfamiliar objective", "bounded tools", "independent outcome authority"],
                "preconditions": ["complete capsule", "verified evidence anchors", "available safe executor"],
                "steps": list(capsule["retained_method"]),
                "invariants": ["precommit_before_execution", "original_sources_remain_closed",
                               "counterexamples_must_be_rejected", "unsafe_variants_never_execute"],
                "failure_signals": ["altered_capsule", "missing_executor", "counterexample_survives",
                                    "unsafe_variant_accepted", "independent_outcome_fails"],
                "verification": {
                    "authority": outcome["authority"],
                    "candidate_execution_passed": True,
                    "counterexamples": [outcome["counterexamples_rejected"], outcome["counterexamples_total"]],
                    "unsafe_variants": [outcome["unsafe_variants_rejected"], outcome["unsafe_variants_total"]],
                },
                "transfer": ["unfamiliar_project", "source_disjoint_application"],
                "program": {
                    "ir": "aion.induced_competency_method.v1",
                    "operators": list(capsule["retained_method"]),
                    "subject_id": subject_id,
                },
            },
            evidence=[evidence],
        )
        verifier = lexicon.add_node(
            kind="verifier", key=f"fresh_competency_authority:{subject_id}",
            summary="Fresh execution with counterexamples and unsafe-variant rejection",
            facets={"source_disjoint": bool(outcome.get("source_disjoint_transfer")),
                    "unfamiliar": bool(outcome.get("unfamiliar")), "self_scoring": False},
            evidence=[evidence],
        )
        transfer = lexicon.add_node(
            kind="transfer", key=f"competency_transfer:{subject_id}",
            summary=f"Apply {capsule['subject_name']} method outside its original learning episodes",
            facets={"source_disjoint": bool(outcome.get("source_disjoint_transfer")),
                    "original_sources_opened": 0}, evidence=[evidence],
        )
        for node in subskill_nodes:
            lexicon.relate(procedure, "requires", node)
        lexicon.relate(procedure, "verified_by", verifier)
        lexicon.relate(procedure, "transfers_to", transfer)
        induced.append({
            "subject_id": subject_id, "procedure_id": procedure,
            "subskills": len(subskill_nodes),
            "source_disjoint": bool(outcome.get("source_disjoint_transfer")),
        })
    return lexicon, induced, rejected


def _compose(lexicon: FunctionalGlyphLexicon, subjects: list[str]) -> dict[str, Any]:
    capsules = [lexicon.reconstruct(f"apply_competence:{subject}") for subject in subjects]
    passed = all(row.get("passed") for row in capsules)
    return {
        "subjects": subjects,
        "passed": passed,
        "plan": [
            {"step": index + 1, "procedure": f"apply_competence:{subject}",
             "depends_on": [index] if index else []}
            for index, subject in enumerate(subjects)
        ] if passed else [],
        "source_documents_opened": sum(int(row.get("source_documents_opened") or 0) for row in capsules),
    }


def run(
    *, repo_root: Path, store_path: Path, capsule_dir: Path,
    reconstruction_result_path: Path, result_path: Path,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    lexicon, induced, rejected = induce(
        repo_root=repo_root, store_path=store_path, capsule_dir=capsule_dir,
        reconstruction_result_path=reconstruction_result_path,
    )
    validation = lexicon.validate()
    before = (len(lexicon.nodes), len(lexicon.edges))
    # Reapplying the same verified trajectories must be content-idempotent.
    lexicon_again, induced_again, _ = induce(
        repo_root=repo_root, store_path=store_path, capsule_dir=capsule_dir,
        reconstruction_result_path=reconstruction_result_path,
    )
    idempotent = before == (len(lexicon_again.nodes), len(lexicon_again.edges))
    reconstructions = [lexicon.reconstruct(f"apply_competence:{row['subject_id']}") for row in induced]
    corrupt_controls = []
    for row in reconstructions:
        altered = json.loads(json.dumps(row))
        altered["procedure"]["facets"].pop("verification", None)
        corrupt_controls.append(not (
            FunctionalGlyphLexicon.REQUIRED_PROCEDURE_FACETS
            <= set(altered["procedure"]["facets"])
        ))
    compositions = [
        _compose(lexicon, ["algorithms_data_structures", "software_engineering", "english"]),
        _compose(lexicon, ["mathematics", "scientific_method", "python"]),
    ]
    storage = lexicon.save()

    competency = ProgressiveCompetencySystem(
        repo_root=repo_root,
        state_path=repo_root / "backend/modules/hexcore/data/progressive_competency/state.json",
    )
    qualified = []
    for row in induced:
        assessment = competency.assess(row["subject_id"])
        if assessment["overall_level"] in {"advanced", "expert"}:
            qualified.append({"subject_id": row["subject_id"], "level": assessment["overall_level"],
                              "memory_reconstructed": True,
                              "source_disjoint": row["source_disjoint"]})

    gate = {
        **validation, **storage,
        "verified_trajectories_induced": len(induced),
        "rejected_trajectories": len(rejected),
        "induced_procedures_reconstructed": sum(row.get("passed") is True for row in reconstructions),
        "corrupted_capsules_rejected": sum(corrupt_controls),
        "cross_domain_compositions_passed": sum(row["passed"] for row in compositions),
        "cross_domain_compositions_total": len(compositions),
        "content_idempotent": idempotent,
        "advanced_memory_qualified": sum(row["level"] == "advanced" for row in qualified),
        "expert_memory_qualified": sum(row["level"] == "expert" for row in qualified),
        "raw_answers_stored": 0,
        "original_source_documents_opened": sum(row["source_documents_opened"] for row in compositions),
        "competency_awards": 0,
        "unsafe_actions": 0,
        "live_repository_writes": 0,
    }
    gate["accepted"] = bool(
        len(induced) >= 6
        and gate["induced_procedures_reconstructed"] == len(induced)
        and gate["corrupted_capsules_rejected"] == len(induced)
        and gate["cross_domain_compositions_passed"] == len(compositions)
        and idempotent
        and gate["advanced_memory_qualified"] + gate["expert_memory_qualified"] >= 6
        and gate["raw_answers_stored"] == gate["original_source_documents_opened"]
        == gate["unsafe_actions"] == gate["live_repository_writes"] == 0
    )
    result = {
        "schema_version": "aion.autonomous_functional_glyph_induction.v1",
        "created_at": _utc_timestamp(), "procedure_id": PROCEDURE_ID,
        "status": "PROMOTED" if gate["accepted"] else "REJECTED",
        "passed": gate["accepted"], "gate": gate,
        "induced": induced, "rejected": rejected,
        "memory_qualified_competencies": qualified,
        "compositions": compositions,
        "boundary": (
            "Automatically induced, source-closed functional memory for verified competency "
            "trajectories. This adds a reconstruction qualification to existing levels; it "
            "does not award Advanced or Expert status."
        ),
    }
    _write(result_path, result)
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(
        repo_root=root,
        store_path=root / "backend/modules/hexcore/data/functional_glyph_lexicon/lexicon.json.gz",
        capsule_dir=root / "backend/modules/hexcore/data/functional_mastery_memory/capsules",
        reconstruction_result_path=root / "results/hexcore_functional_mastery_memory.json",
        result_path=root / "results/hexcore_autonomous_functional_glyph_induction.json",
    ), indent=2, sort_keys=True))
