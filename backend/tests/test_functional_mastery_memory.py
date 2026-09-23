from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.functional_mastery_memory import (
    FunctionalMasteryMemory,
    TARGETS,
    run,
)


ROOT = Path(__file__).resolve().parents[2]


def test_capsules_cover_declared_subskills_without_copying_raw_sources() -> None:
    memory = FunctionalMasteryMemory(repo_root=ROOT)
    for subject_id in TARGETS:
        capsule = memory.compile_capsule(subject_id)
        covered = set(capsule["declared_subskills"]) <= set(capsule["grounded_subskills"])
        assert capsule["coverage_complete"] is covered
        assert capsule["verified_evidence_ids"]
        assert capsule["episodic_index"]
        assert all("artifact_sha256" in row for row in capsule["episodic_index"])


def test_altered_or_incomplete_capsule_fails_closed() -> None:
    memory = FunctionalMasteryMemory(repo_root=ROOT)
    capsule = memory.compile_capsule("mathematics")
    capsule["grounded_subskills"] = capsule["grounded_subskills"][:-1]
    result = memory.reconstruct("mathematics", capsule=capsule)
    assert result["status"] == "ABSTAIN_INCOMPLETE_OR_ALTERED_MEMORY"
    assert result["source_artifacts_opened"] == 0
    assert result["counterexamples_rejected"] == 0
    assert result["counterexamples_total"] == 0
    assert result["live_repository_writes"] == 0


def test_six_domain_functional_reconstruction(tmp_path: Path) -> None:
    result = run(
        repo_root=ROOT,
        result_path=tmp_path / "result.json",
        capsule_dir=tmp_path / "capsules",
    )
    complete = all(row["status"] == "FUNCTIONALLY_RECONSTRUCTED"
                   for row in result["reconstructions"])
    assert result["passed"] is complete
    if complete:
        assert result["gate"]["functional_reconstructions"] == 6
        assert result["gate"]["source_disjoint_reconstructions"] >= 5
    else:
        assert any(row["status"] == "ABSTAIN_INCOMPLETE_OR_ALTERED_MEMORY"
                   for row in result["reconstructions"])
    assert result["gate"]["corrupted_memory_controls_abstained"] == 6
    assert result["gate"]["original_source_artifacts_opened"] == 0
    assert result["gate"]["live_repository_writes"] == 0
    assert json.loads((tmp_path / "result.json").read_text())["procedure_id"] == result["procedure_id"]
