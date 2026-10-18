from __future__ import annotations

import json
from pathlib import Path

import pytest

from integrations.isaac_lab.run_fresh_world_physx_authority import (
    aggregate, execution_plan, validate_child,
)
from integrations.isaac_lab.verify_fresh_world_physx import verify


def child(arm: str, seed: int, marker: str = "a") -> dict:
    return {
        "failure": None, "arm_id": arm, "seed": seed,
        "comparison_arm": None, "matched_same_process": False,
        "outcomes": [{"arm_id": arm, "episode": 0, "success": False}],
        "policy_summary": {arm: {
            "episode_initial_observation_sha256": [marker * 64],
            "episode_initial_component_sha256": [{
                "rgb": marker * 64, "proprioception": marker * 64,
                "fingertip_touch": marker * 64,
            }],
        }},
        "logs": {
            "observation_chain_sha256": marker + "o", "action_chain_sha256": marker + "a",
            "outcome_chain_sha256": marker + "r",
        },
        "audit": {"completed_without_failure": True,
                  "deterministic_execution_requested": True},
        "determinism": {"physx_enhanced_determinism": True,
                        "rtx_deterministic_requested": True},
    }


def test_plan_counterbalances_and_never_combines_arms() -> None:
    plan = execution_plan(["aion_retained", "aion_distilled"], 2, 700)
    assert [(row["episode"], row["arm_id"]) for row in plan] == [
        (0, "aion_retained"), (0, "aion_distilled"),
        (1, "aion_distilled"), (1, "aion_retained"),
    ]
    assert [row["seed"] for row in plan] == [700, 700, 701, 701]


def test_child_must_be_one_isolated_deterministic_episode() -> None:
    expected = {"arm_id": "aion_retained", "episode": 0, "seed": 700}
    assert validate_child(child("aion_retained", 700), expected) == {
        "rgb": "a" * 64, "proprioception": "a" * 64, "fingertip_touch": "a" * 64,
    }
    bad = child("aion_retained", 700)
    bad["matched_same_process"] = True
    with pytest.raises(ValueError, match="sequential_comparison_forbidden"):
        validate_child(bad, expected)


def test_aggregate_and_replay_verifier_fail_closed(tmp_path: Path) -> None:
    expected = {"arm_id": "aion_retained", "episode": 0, "seed": 700,
                "launch_index_within_episode": 0}
    receipt_path = tmp_path / "child.json"
    receipt_path.write_text(json.dumps(child("aion_retained", 700)))
    authority = aggregate([(expected, receipt_path, child("aion_retained", 700))])
    assert verify(authority, authority)["policy_tournament_authorized"]
    changed = json.loads(json.dumps(authority))
    changed["children"][0]["action_chain_sha256"] = "changed"
    assert not verify(authority, changed)["passed"]
