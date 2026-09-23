import json
from pathlib import Path

from backend.modules.hexcore.autonomous_mastery_curriculum_supervisor import (
    AutonomousMasteryCurriculumSupervisor,
    SUPERVISOR_OBJECTIVE,
)


def _registry(path: Path) -> None:
    payload = {
        "constitutional_purpose": "beneficial evidence-backed intelligence",
        "purpose_hash": "purpose-1",
        "subjects": {
            "python": {"name": "Python", "group": "programming", "level": "operational_bounded",
                       "level_index": 2, "target_level": "proficient_bounded",
                       "missing_subskills": ["concurrency"], "coverage": 0.7,
                       "mastery_claim_authorized": False},
            "biology": {"name": "Biology", "group": "science", "level": "unassessed",
                        "level_index": 0, "target_level": "operational_bounded",
                        "missing_subskills": ["cell_biology"], "coverage": 0.0,
                        "mastery_claim_authorized": False},
        },
        "strategic_goal_portfolio": [
            {"subject_id": "biology", "priority": 3.0},
            {"subject_id": "python", "priority": 1.0},
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_supervisor_selects_north_star_gap_and_requests_missing_executor(tmp_path):
    registry = tmp_path / "registry.json"
    _registry(registry)
    supervisor = AutonomousMasteryCurriculumSupervisor(
        repo_root=tmp_path, state_path=tmp_path / "state.json", registry_path=registry,
        teacher_cache_path=tmp_path / "teacher.json",
    )
    result = supervisor.step(live_teacher=False, now=1000.0)
    assert result["cycle"]["action"]["subject_id"] == "biology"
    assert result["cycle"]["action"]["status"] == "executor_acquisition_required"
    assert result["state_summary"]["open_executor_requests"] == 1
    assert result["state_summary"]["owner_lesson_steps"] == 0


def test_supervisor_continues_to_depth_then_cross_subject_transfer(tmp_path):
    registry = tmp_path / "registry.json"
    _registry(registry)
    supervisor = AutonomousMasteryCurriculumSupervisor(
        repo_root=tmp_path, state_path=tmp_path / "state.json", registry_path=registry,
        teacher_cache_path=tmp_path / "teacher.json",
    )
    first = supervisor.step(live_teacher=False, now=1000.0)
    second = supervisor.step(live_teacher=False, now=1001.0)
    third = supervisor.step(live_teacher=False, now=1002.0)
    assert first["cycle"]["action"]["subject_id"] == "biology"
    assert second["cycle"]["action"]["subject_id"] == "python"
    assert second["cycle"]["action"]["status"] == "ready_to_execute"
    assert third["cycle"]["action"]["status"] == "cross_subject_transfer_planning"
    assert third["state_summary"]["cross_subject_transfer_proposals"] == 1
    assert supervisor.state["objective"] == SUPERVISOR_OBJECTIVE


def test_existing_certificate_creates_delayed_retest_not_mastery(tmp_path):
    registry = tmp_path / "registry.json"
    _registry(registry)
    result_dir = tmp_path / "results"
    result_dir.mkdir()
    (result_dir / "hexcore_governed_teacher_python_core_cycle.json").write_text(json.dumps({
        "passed": True,
        "certificate": {"certificate_id": "python-cert", "level": "operational_bounded"},
    }), encoding="utf-8")
    supervisor = AutonomousMasteryCurriculumSupervisor(
        repo_root=tmp_path, state_path=tmp_path / "state.json", registry_path=registry,
        teacher_cache_path=tmp_path / "teacher.json",
    )
    supervisor.step(live_teacher=False, now=1000.0)
    assert supervisor.state["completed_certificates"]["python-cert"]["mastery_claim_authorized"] is False
    assert supervisor.state["retention_schedule"][0]["requires_fresh_tasks"] is True
    assert supervisor.state["retention_schedule"][0]["solution_replay_forbidden"] is True
