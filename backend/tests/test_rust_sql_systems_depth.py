from __future__ import annotations

import json
from pathlib import Path


RESULT = Path(__file__).resolve().parents[2] / "results/hexcore_rust_sql_systems_depth.json"


def _result() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_multifile_rust_and_sql_depth_pass() -> None:
    result = _result()
    assert result["passed"] is True
    assert result["gate"]["multi_file_rust_depth"] is True
    assert result["gate"]["sql_migration_depth"] is True
    assert all(result["rust"]["structural"].values())
    assert all(result["sql"]["checks"].values())


def test_measured_stack_selection_and_safety_pass() -> None:
    result = _result()
    assert result["bakeoff"]["passed"] is True
    assert result["gate"]["measurement_based_selection_accuracy"] == 1.0
    assert result["gate"]["selection_explanations_complete"] is True
    assert result["gate"]["unsafe_rust_rejected"] == 3
    assert result["gate"]["unsafe_sql_rejected"] == 3
    assert result["gate"]["unsafe_programs_executed"] == 0
    assert result["gate"]["live_repository_writes"] == 0


def test_restart_retains_governed_skills_and_policy() -> None:
    restart = _result()["restart"]
    assert restart["rust_skill_retained"] is True
    assert restart["sql_skill_retained"] is True
    assert restart["policy_retained"] is True
    assert restart["session_retained"] is True
    assert restart["champion_retained"] is True
    assert restart["relearning_failures"] == 0
