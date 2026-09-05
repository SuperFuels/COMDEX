from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.comprehensive_expertise_curriculum import build_curriculum
from backend.modules.hexcore.expertise_container_curriculum_runtime import (
    activate_expertise_curriculum,
    build_container_projection,
)


def test_projection_creates_namespaced_typed_academies(tmp_path: Path) -> None:
    curriculum = build_curriculum()
    index = build_container_projection(curriculum=curriculum, container_root=tmp_path / "containers")
    assert index["container_count"] == len(curriculum["subjects"]) + 3
    drone = json.loads((tmp_path / "containers/aion__academy_uncrewed_aerial_systems.json").read_text())
    assert drone["meta"]["graph"] == "work"
    assert drone["meta"]["ownerWA"] == "aion@wave.tp"
    assert drone["competence_awarded"] is False
    assert all(node["id"].startswith("work:aion@wave.tp:") for node in drone["knowledge_graph"]["nodes"])
    bridges = json.loads((tmp_path / "containers/aion__cross_domain_bridges.json").read_text())
    assert len(bridges["knowledge_graph"]["edges"]) == len(curriculum["cross_domain_bridges"])
    assert bridges["typed_edges"] is True
    assert bridges["entanglement_used_only_for_container_association"] is True


def test_activation_registers_curriculum_without_awarding_evidence(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    curriculum_path = tmp_path / "curriculum.json"
    curriculum_path.write_text(json.dumps(build_curriculum()), encoding="utf-8")
    result = activate_expertise_curriculum(
        repo_root=repo_root,
        curriculum_path=curriculum_path,
        container_root=tmp_path / "containers",
        competency_state_path=tmp_path / "competency.json",
        runtime_state_path=tmp_path / "runtime.json",
        result_path=tmp_path / "result.json",
    )
    assert result["passed"] is True
    expected_subjects = len(build_curriculum()["subjects"])
    assert result["gate"]["academy_containers"] == expected_subjects
    assert result["gate"]["live_registry_capabilities_installed"] == 18
    assert result["gate"]["live_registry_subjects_installed"] == expected_subjects
    assert result["gate"]["evidence_records_added"] == 0
    assert result["gate"]["competence_awarded"] is False
    assert result["runtime_state"]["status"] == "active"
    assert result["runtime_state"]["current_subject_id"] == "capability_learning_strategy"
