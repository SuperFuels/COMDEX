from __future__ import annotations

import json
from pathlib import Path


RESULT = Path(__file__).resolve().parents[2] / "results/hexcore_closed_loop_physical_intelligence_v8.json"


def _result() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_pixel_action_outcome_loop_passes_sealed_gate() -> None:
    result = _result()
    gate = result["gate"]
    assert result["passed"] is True
    assert gate["sealed_worlds"] == 24
    assert gate["pixel_grounded_observations"] is True
    assert gate["prediction_before_action_commitments"] > 0
    assert gate["goal_success"] == 1.0
    assert gate["weakest_family_success"] == 1.0
    assert gate["authority_separation"] is True


def test_prior_is_induced_from_disjoint_outcomes_and_beats_cold_control() -> None:
    result = _result()
    evidence = result["development_prior_evidence"]
    assert evidence["development_worlds"] == 32
    assert evidence["source_disjoint_from_sealed"] is True
    assert evidence["parameter_labels_exposed_to_learner"] is False
    assert result["gate"]["probe_reduction_vs_cold"] >= 0.10
    assert result["gate"]["goal_success"] >= result["gate"]["cold_goal_success"]


def test_change_revision_and_out_of_family_abstention() -> None:
    result = _result()
    assert result["gate"]["changed_worlds"] == 4
    assert result["gate"]["changed_world_revision_rate"] >= 0.75
    assert result["gate"]["ood_abstention"] is True
    assert result["ood"]["goal"]["goal_reached"] is False
    assert result["gate"]["unsafe_physical_actions"] == 0


def test_physical_skill_survives_restart() -> None:
    result = _result()
    assert result["restart"] == {
        "champion_retained": True,
        "cohort_retained": True,
        "relearning_worlds": 0,
    }

