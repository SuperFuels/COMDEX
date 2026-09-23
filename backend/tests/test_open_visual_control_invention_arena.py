from __future__ import annotations
import json
from pathlib import Path

RESULT = Path(__file__).resolve().parents[2] / "results/hexcore_open_visual_control_invention_v10.json"
def _result() -> dict: return json.loads(RESULT.read_text(encoding="utf-8"))

def test_visual_state_and_controller_are_invented_from_outcomes() -> None:
    r = _result(); g = r["gate"]
    assert r["passed"] is True
    assert g["task_specific_color_supplied"] is False
    assert g["visual_components_considered"] >= 20
    assert g["programs_composed"] >= 7
    assert g["selected_program"] == "sign(dx)"
    assert g["numeric_observation_used"] is False

def test_program_lifts_across_action_topologies_and_beats_cold() -> None:
    g = _result()["gate"]
    assert g["action_topologies"] == 2
    assert g["discrete_success"] == 1.0
    assert g["continuous_transfer_success"] == 1.0
    assert g["success_lift_vs_cold"] >= 0.50
    assert g["pre_action_commitments"] > 0

def test_unknown_visual_schema_abstains_and_persists() -> None:
    r = _result()
    assert r["gate"]["unknown_schema_abstention"] is True
    assert r["gate"]["unsafe_actions"] == 0
    assert r["restart"] == {"champion_retained": True, "cohort_retained": True, "relearning_episodes": 0}

