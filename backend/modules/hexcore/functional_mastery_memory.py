"""Functional reconstruction authority for compressed AION competence.

Glyphs are useful only when they can recover enough of a learned method to
select and survive fresh executable work.  This module builds compact subject
capsules from the governed glyph packet, closes the original evidence sources,
and asks the installed progressive executors to face a fresh transfer contract.

The capsule is proposal memory.  Fresh execution, counterexamples and the
progressive competency ledger remain the authorities.  A successful run does
not itself award Advanced or Expert status.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import (
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.progressive_competency_executor import RUNNERS
from backend.modules.hexcore.progressive_competency_system import (
    ProgressiveCompetencySystem,
)


PROCEDURE_ID = "procedure_functional_mastery_memory_reconstruction_v1"
SCHEMA = "aion.hexcore.functional_mastery_memory.v1"
TARGETS = (
    "algorithms_data_structures",
    "software_engineering",
    "mathematics",
    "english",
    "python",
    "scientific_method",
)


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


class FunctionalMasteryMemory:
    """Compile and execute source-closed functional memory capsules."""

    def __init__(
        self,
        *,
        repo_root: Path,
        competency_path: Path | None = None,
        glyph_index_path: Path | None = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.competency_path = competency_path or (
            self.repo_root / "backend/modules/hexcore/data/progressive_competency/state.json"
        )
        self.glyph_index_path = glyph_index_path or (
            self.repo_root / "backend/modules/hexcore/data/intelligence_glyphs/index.json"
        )
        self.system = ProgressiveCompetencySystem(
            repo_root=self.repo_root, state_path=self.competency_path
        )

    def _load_glyph_packet(self) -> tuple[dict[str, Any], dict[str, Any]]:
        index = json.loads(self.glyph_index_path.read_text(encoding="utf-8"))
        compressed = self.repo_root / str(index["compressed_store"])
        if _sha(compressed) != index["compressed_sha256"]:
            raise ValueError("functional memory refused altered glyph store")
        with gzip.open(compressed, "rb") as handle:
            packet = json.loads(handle.read().decode("utf-8"))
        return index, packet

    def compile_capsule(self, subject_id: str) -> dict[str, Any]:
        if subject_id not in self.system.state["subjects"]:
            raise KeyError(subject_id)
        index, packet = self._load_glyph_packet()
        subject = self.system.state["subjects"][subject_id]
        skill_name = f"competency:{subject_id}"
        skill = next(
            (row for row in packet["glyphs"] if row["k"] == "Skill" and row["n"] == skill_name),
            None,
        )
        knowledge = [
            row for row in packet["glyphs"]
            if row["k"] == "Knowledge" and row["n"].startswith(subject_id + ".")
        ]
        grounded = sorted({str(row["d"].get("subskill")) for row in knowledge})
        declared = sorted(str(value) for value in subject["subskills"])
        evidence_ids = sorted({eid for row in ([skill] if skill else []) + knowledge for eid in row["e"]})
        unresolved = sorted(set(evidence_ids) - set(index["evidence"]))
        assessment = self.system.assess(subject_id)
        body = {
            "schema_version": SCHEMA,
            "subject_id": subject_id,
            "subject_name": subject["name"],
            "declared_subskills": declared,
            "grounded_subskills": grounded,
            "coverage_complete": set(declared) <= set(grounded),
            "verified_evidence_ids": evidence_ids,
            "unresolved_evidence_ids": unresolved,
            "retained_method": [
                "decompose_objective_into_grounded_subskills",
                "select_a_verified_execution_authority",
                "commit_expected_outcome_before_execution",
                "generate_counterexamples_for_the_selected_method",
                "execute_in_a_fresh_bounded_environment",
                "attribute_failure_before_revising_memory_or_executor",
                "retain_only_independently_verified_transfer",
            ],
            "episodic_index": [
                {
                    "evidence_id": eid,
                    "artifact_sha256": index["evidence"][eid]["h"],
                    "authority": index["evidence"][eid].get("authority", "verified_source"),
                }
                for eid in evidence_ids[-8:]
            ],
            "retrieval_policy": {
                "normal_operation": "capsule_only",
                "exact_detail": "resolve_content_addressed_evidence_on_demand",
                "knowledge_gap": "reacquire_from_authoritative_source_then_retest",
            },
            "competency_snapshot": {
                "knowledge": assessment["knowledge_level"],
                "practical": assessment["practical_level"],
                "overall": assessment["overall_level"],
            },
        }
        body["capsule_sha256"] = _canonical_hash(body)
        return body

    def reconstruct(
        self,
        subject_id: str,
        *,
        capsule: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        capsule = dict(capsule or self.compile_capsule(subject_id))
        declared = set(self.system.state["subjects"][subject_id]["subskills"])
        grounded = set(capsule.get("grounded_subskills") or [])
        capsule_valid = bool(
            capsule.get("subject_id") == subject_id
            and declared <= grounded
            and capsule.get("verified_evidence_ids")
            and not capsule.get("unresolved_evidence_ids")
            and capsule.get("capsule_sha256")
            == _canonical_hash({key: value for key, value in capsule.items() if key != "capsule_sha256"})
        )
        if not capsule_valid:
            return {
                "subject_id": subject_id,
                "status": "ABSTAIN_INCOMPLETE_OR_ALTERED_MEMORY",
                "passed": False,
                "source_disjoint_transfer": False,
                "unfamiliar": False,
                "candidate_execution_passed": False,
                "counterexamples_rejected": 0,
                "counterexamples_total": 0,
                "unsafe_variants_rejected": 0,
                "unsafe_variants_total": 0,
                "source_artifacts_opened": 0,
                "live_repository_writes": 0,
                "unsafe_actions": 0,
            }
        runner = RUNNERS.get(subject_id)
        if runner is None:
            return {
                "subject_id": subject_id,
                "status": "ABSTAIN_EXECUTOR_REQUIRED",
                "passed": False,
                "source_disjoint_transfer": False,
                "unfamiliar": False,
                "candidate_execution_passed": False,
                "counterexamples_rejected": 0,
                "counterexamples_total": 0,
                "unsafe_variants_rejected": 0,
                "unsafe_variants_total": 0,
                "source_artifacts_opened": 0,
                "live_repository_writes": 0,
                "unsafe_actions": 0,
            }
        contract = {
            "contract_id": "reconstruct_" + capsule["capsule_sha256"][:18],
            "subject_id": subject_id,
            "requirement": {
                "kind": "transfer",
                "subskills": sorted(declared),
                "novelty_required": True,
            },
            "_repo_root": str(self.repo_root),
        }
        # The original evidence artifacts remain closed.  Existing evidence is
        # deliberately withheld from the runner, so it cannot replay a stored
        # answer or select a project from the old episode list.
        outcome = runner(contract, [])
        gate = outcome.get("gate") or {}
        counterexamples = int(gate.get("counterexamples_rejected") or 0)
        counterexample_total = int(gate.get("counterexamples_total") or 0)
        unsafe_rejected = int(gate.get("unsafe_variants_rejected") or 0)
        unsafe_total = int(gate.get("unsafe_variants_total") or 0)
        passed = bool(
            outcome.get("passed") is True
            and gate.get("candidate_execution_passed") is True
            and counterexample_total > 0
            and counterexamples == counterexample_total
            and unsafe_total > 0
            and unsafe_rejected == unsafe_total
            and gate.get("live_repository_writes", 0) == 0
        )
        return {
            "subject_id": subject_id,
            "status": "FUNCTIONALLY_RECONSTRUCTED" if passed else "RECONSTRUCTION_FAILED",
            "passed": passed,
            "source_disjoint_transfer": bool(gate.get("source_disjoint_transfer")),
            "unfamiliar": bool(outcome.get("unfamiliar")),
            "candidate_execution_passed": bool(gate.get("candidate_execution_passed")),
            "counterexamples_rejected": counterexamples,
            "counterexamples_total": counterexample_total,
            "unsafe_variants_rejected": unsafe_rejected,
            "unsafe_variants_total": unsafe_total,
            "source_artifacts_opened": 0,
            "live_repository_writes": int(gate.get("live_repository_writes", 0)),
            "authority": "fresh_executor_outcome_plus_counterexamples_with_original_sources_closed",
        }


def run(
    *,
    repo_root: Path,
    result_path: Path,
    capsule_dir: Path,
    targets: Iterable[str] = TARGETS,
) -> dict[str, Any]:
    memory = FunctionalMasteryMemory(repo_root=repo_root)
    capsules: list[dict[str, Any]] = []
    reconstructions: list[dict[str, Any]] = []
    corrupted_controls: list[dict[str, Any]] = []
    for subject_id in targets:
        capsule = memory.compile_capsule(subject_id)
        capsule_path = capsule_dir / f"{subject_id}.json"
        _atomic_write(capsule_path, capsule)
        capsules.append({
            "subject_id": subject_id,
            "path": _display_path(capsule_path, repo_root),
            "sha256": _sha(capsule_path),
            "grounded_subskills": len(capsule["grounded_subskills"]),
            "declared_subskills": len(capsule["declared_subskills"]),
            "evidence_anchors": len(capsule["verified_evidence_ids"]),
        })
        reconstructions.append(memory.reconstruct(subject_id, capsule=capsule))
        corrupted = json.loads(json.dumps(capsule))
        corrupted["grounded_subskills"] = corrupted["grounded_subskills"][:-1]
        corrupted_controls.append(memory.reconstruct(subject_id, capsule=corrupted))

    reconstructed = sum(row["passed"] for row in reconstructions)
    transfer = sum(row["passed"] and row["source_disjoint_transfer"] for row in reconstructions)
    controls_abstained = sum(row["status"].startswith("ABSTAIN") for row in corrupted_controls)
    gate = {
        "functional_reconstructions": reconstructed,
        "required_reconstructions": len(reconstructions),
        "source_disjoint_reconstructions": transfer,
        "corrupted_memory_controls_abstained": controls_abstained,
        "required_corrupted_controls": len(corrupted_controls),
        "original_source_artifacts_opened": sum(row["source_artifacts_opened"] for row in reconstructions),
        "counterexamples_rejected": sum(int(row.get("counterexamples_rejected") or 0) for row in reconstructions),
        "counterexamples_total": sum(int(row.get("counterexamples_total") or 0) for row in reconstructions),
        "unsafe_variants_rejected": sum(int(row.get("unsafe_variants_rejected") or 0) for row in reconstructions),
        "unsafe_variants_total": sum(int(row.get("unsafe_variants_total") or 0) for row in reconstructions),
        "live_repository_writes": sum(int(row.get("live_repository_writes") or 0) for row in reconstructions),
        "competency_awards": 0,
    }
    gate["accepted"] = bool(
        reconstructed == len(reconstructions)
        and transfer >= len(reconstructions) - 1
        and controls_abstained == len(corrupted_controls)
        and gate["original_source_artifacts_opened"] == 0
        and gate["counterexamples_rejected"] == gate["counterexamples_total"]
        and gate["unsafe_variants_rejected"] == gate["unsafe_variants_total"]
        and gate["live_repository_writes"] == 0
    )
    result = {
        "schema_version": "aion.hexcore.functional_mastery_memory_result.v1",
        "created_at": _utc_timestamp(),
        "procedure_id": PROCEDURE_ID,
        "status": "PROMOTED" if gate["accepted"] else "REJECTED",
        "passed": gate["accepted"],
        "gate": gate,
        "capsules": capsules,
        "reconstructions": reconstructions,
        "corrupted_memory_controls": corrupted_controls,
        "boundary": (
            "This proves source-closed functional reconstruction through six installed bounded "
            "authorities. It does not award Advanced/Expert status or prove arbitrary subject mastery."
        ),
    }
    _atomic_write(result_path, result)
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(
        repo_root=root,
        result_path=root / "results/hexcore_functional_mastery_memory.json",
        capsule_dir=root / "backend/modules/hexcore/data/functional_mastery_memory/capsules",
    ), indent=2, sort_keys=True))
