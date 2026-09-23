from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.autonomous_problem_apprenticeship_pilot import (
    run_autonomous_problem_apprenticeship_pilot,
)


def test_problem_drives_closed_book_subject_apprenticeship(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    result_path = tmp_path / "result.json"
    result = run_autonomous_problem_apprenticeship_pilot(
        state_path=state_path,
        result_path=result_path,
    )

    assert result["passed"] is True
    assert result["diagnosis"]["selected_subject"] == "drone_energy_reserve_planning"
    assert result["gate"]["minimum_curriculum_selected"] is True
    assert result["gate"]["repair_triggered_by_failure"] is True
    assert result["gate"]["practice_passed_after_repair"] is True
    assert result["gate"]["source_closed_before_exam"] is True
    assert result["hidden_exam"]["source_accessed"] is False
    assert result["hidden_exam"]["relearning_actions"] == 0
    assert result["hidden_exam"]["source_disjoint"] is True
    assert result["hidden_exam"]["passed"] is True
    assert result["original_resolution"]["passed"] is True
    assert result["restart_transfer"]["passed"] is True
    assert result["restart_transfer"]["relearning_actions"] == 0
    assert result["gate"]["all_controls_failed"] is True
    assert result["gate"]["network_calls"] == 0
    assert result["gate"]["paid_api_calls"] == 0
    assert result["gate"]["unsafe_actions"] == 0
    assert json.loads(result_path.read_text(encoding="utf-8"))["result_digest"]


def test_corrupt_retained_capsule_fails_closed(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    run_autonomous_problem_apprenticeship_pilot(state_path=state_path)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["capsule"]["procedure"]["procedure_version"] = 99
    state_path.write_text(json.dumps(state), encoding="utf-8")

    from backend.modules.hexcore.autonomous_problem_apprenticeship_pilot import (
        _load_capsule,
    )

    assert _load_capsule(state_path) is None
