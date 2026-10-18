from __future__ import annotations

import json
from pathlib import Path

RESULT = Path(__file__).resolve().parents[2] / "results/hexcore_public_physics_transfer_v9.json"

def _result() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))

def test_public_pixel_physics_transfer_passes() -> None:
    result = _result(); gate = result["gate"]
    assert result["passed"] is True
    assert gate["public_authority"] == "Farama_Gymnasium"
    assert gate["gymnasium_version"] == "1.2.3"
    assert len(gate["authority_source_sha256"]) == 64
    assert gate["pixel_only_state_inference"] is True
    assert gate["sealed_seeds"] == 12
    assert gate["learned_policy_success"] == 1.0
    assert gate["weakest_family_success"] == 1.0

def test_outcome_selected_programs_beat_zero_experience_controls() -> None:
    result = _result(); gate = result["gate"]
    assert gate["mountain_champion"] == "momentum_feedback"
    assert gate["cartpole_champion"] == "predictive_2"
    assert gate["success_lift_vs_cold"] >= 0.50
    assert gate["pre_action_commitments"] > 0
    assert all(not row["numeric_observation_used"] for row in result["sealed"]["learned"])

def test_unknown_public_visual_schema_abstains_before_action() -> None:
    result = _result()
    assert result["ood"] == {"actions_executed": 0, "adapter_known": False, "abstained": True, "environment": "Acrobot-v1"}
    assert result["gate"]["unsafe_actions"] == 0
    assert result["gate"]["live_system_writes"] == 0

def test_v9_survives_restart() -> None:
    assert _result()["restart"] == {"champion_retained": True, "cohort_retained": True, "relearning_episodes": 0}

