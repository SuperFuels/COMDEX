from __future__ import annotations

import json
from pathlib import Path


RESULT = Path(__file__).resolve().parents[2] / "results/hexcore_rust_sql_construction_and_selection.json"


def test_rust_and_sql_are_constructed_and_verified() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    gate = result["gate"]
    assert result["passed"] is True
    assert gate["accepted"] is True
    assert gate["rust_constructed_and_verified"] is True
    assert gate["sql_constructed_and_verified"] is True
    assert result["rust"]["evaluation"]["compiled"] is True
    assert all(result["sql"]["evaluation"]["checks"].values())


def test_technology_selection_and_safety_pass() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    gate = result["gate"]
    assert gate["technology_choice_accuracy"] == 1.0
    assert gate["weakest_choice_success"] == 1.0
    assert gate["choice_explanations_complete"] is True
    assert gate["unsafe_rust_rejected"] == 3
    assert gate["unsafe_sql_rejected"] == 3
    assert gate["unsafe_programs_executed"] == 0
    assert result["restart"]["rust_skill_retained"] is True
    assert result["restart"]["sql_skill_retained"] is True
    assert result["restart"]["policy_retained"] is True
