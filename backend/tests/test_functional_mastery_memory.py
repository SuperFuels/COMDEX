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
        assert set(capsule["declared_subskills"]) <= set(capsule["grounded_subskills"])
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


def test_six_domain_functional_reconstruction(tmp_path: Path) -> None:
    result = run(
        repo_root=ROOT,
        result_path=tmp_path / "result.json",
        capsule_dir=tmp_path / "capsules",
    )
    assert result["passed"] is True
    assert result["gate"]["functional_reconstructions"] == 6
    assert result["gate"]["source_disjoint_reconstructions"] >= 5
    assert result["gate"]["corrupted_memory_controls_abstained"] == 6
    assert result["gate"]["original_source_artifacts_opened"] == 0
    assert result["gate"]["live_repository_writes"] == 0
    assert json.loads((tmp_path / "result.json").read_text())["procedure_id"] == result["procedure_id"]
