from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "results" / "hexcore_predictive_pose_franka_tournament.json"


def test_first_predictive_pose_lift_is_retained_without_false_promotion() -> None:
    result = json.loads(RESULT.read_text())
    tournament = result["fresh_physx_tournament"]
    assert tournament["predictive_pose"]["strict_lifts"] == 1
    assert tournament["protected_v13"]["strict_lifts"] == 0
    assert tournament["predictive_pose"]["successful_episode_ids"] == [5]
    assert result["status"] == "challenger_rejected"
    assert result["procedure_id"] is None
    assert result["promotion_gate"]["passed"] is False
    assert result["protected_champion_before"] == result["protected_champion_after"]


def test_predictive_pose_tournament_is_safe_and_teacher_removed() -> None:
    result = json.loads(RESULT.read_text())
    tournament = result["fresh_physx_tournament"]
    assert result["offline_gate"]["passed"]
    assert tournament["teacher_present"] is False
    assert tournament["privileged_runtime_inputs"] == 0
    assert result["unsafe_actions"] == 0
    assert tournament["cold"] is None
    assert "absolute >2/12 promotion gate already failed" in tournament["cold_omission_reason"]
