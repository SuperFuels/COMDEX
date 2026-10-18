from pathlib import Path

import pytest

from backend.modules.hexcore.dual_track_intelligence_portfolio import run as run_portfolio
from backend.modules.hexcore.simulator_neutral_embodied_apprenticeship import (
    DEVELOPMENT_WORLDS,
    MuJoCoLanderAuthority,
    run as run_embodied,
)
from backend.modules.hexcore.rgb_belief_state_mujoco_apprenticeship import (
    DEVELOPMENT as RGB_DEVELOPMENT,
    RGBMuJoCoAuthority,
)
from backend.modules.hexcore.rgb_contact_occlusion_skill_composition import (
    DEVELOPMENT as CONTACT_DEVELOPMENT,
    PARENT_PROCEDURE_ID,
    RGBContactAuthority,
    _canonical_hash as contact_hash,
    _load_parent,
)
from backend.modules.hexcore.rgb_articulated_sequence_skill import (
    DEVELOPMENT as ARM_DEVELOPMENT,
    PARENT_PROCEDURE_ID as ARM_PARENT_PROCEDURE_ID,
    RGBArticulatedAuthority,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_dual_track_portfolio_is_exact_and_idempotent(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    result = tmp_path / "result.json"
    first = run_portfolio(
        repo_root=REPO_ROOT, state_path=state, result_path=result, activate_learning=False
    )
    second = run_portfolio(
        repo_root=REPO_ROOT, state_path=state, result_path=result, activate_learning=False
    )
    assert first["passed"] is True
    assert first["gate"]["practical_objectives"] == 7
    assert first["gate"]["embodied_objectives"] == 3
    assert first["gate"]["ambient_authority_expansions"] == 0
    assert second["generation"] == first["generation"]
    assert len({row["precommitment_digest"] for row in first["portfolio"]}) == 10


@pytest.mark.parametrize(
    "action",
    [
        {"horizontal": float("nan"), "vertical": 0.0},
        {"horizontal": 0.0, "vertical": float("inf")},
        {"horizontal": 2.0, "vertical": 0.0},
        {"horizontal": 0.0},
        {"horizontal": 0.0, "vertical": 0.0, "shell": 1.0},
    ],
)
def test_mujoco_authority_rejects_malformed_actions(action: dict[str, float]) -> None:
    with pytest.raises((ValueError, TypeError)):
        MuJoCoLanderAuthority(DEVELOPMENT_WORLDS[0])._validated_action(action)


def test_commit_before_act_is_mandatory() -> None:
    authority = MuJoCoLanderAuthority(DEVELOPMENT_WORLDS[0])
    with pytest.raises(RuntimeError, match="commit_before_act_required"):
        authority.step({"horizontal": 0.0, "vertical": 0.0})


def test_embodied_method_transfers_and_beats_cold(tmp_path: Path) -> None:
    result = run_embodied(repo_root=REPO_ROOT, result_path=tmp_path / "physical.json")
    gate = result["gate"]
    assert result["passed"] is True
    assert gate["sealed_transfer_success"] == gate["sealed_transfer_worlds"] == 6
    assert gate["sealed_transfer_success"] > gate["cold_control_success"]
    assert gate["ood_impossible_world_abstained"] is True
    assert gate["unsafe_worlds"] == 0
    assert gate["malicious_actions_rejected"] == gate["malicious_actions_total"] == 5


def test_rgb_authority_exposes_images_but_not_numeric_state() -> None:
    authority = RGBMuJoCoAuthority(RGB_DEVELOPMENT[0])
    try:
        observation = authority.reset()
        assert set(observation) == {"rgb", "goal_rgb", "timestamp"}
        assert observation["rgb"].shape == (120, 160, 3)
        assert observation["goal_rgb"].shape == observation["rgb"].shape
        assert not {"x", "z", "vx", "vz", "gravity", "mass"} & set(observation)
        with pytest.raises(RuntimeError, match="commit_before_act_required"):
            authority.step({"horizontal": 0.0, "vertical": 0.5})
    finally:
        authority.close()


def test_rgb_promoted_result_is_fail_closed_and_persistent() -> None:
    result_path = REPO_ROOT / "results/hexcore_rgb_belief_state_mujoco_planning.json"
    if not result_path.exists():
        pytest.skip("RGB sealed campaign has not run")
    import json

    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["passed"] is True
    assert result["gate"]["sealed_success"] == result["gate"]["sealed_worlds"] == 4
    assert result["gate"]["cold_success"] == 0
    assert result["gate"]["unsafe_learned_worlds"] == 0
    assert result["gate"]["ood_ungroundable_abstained"] is True
    assert all(result["restart"].values())


def test_rgb_contact_authority_is_rgb_only_and_commit_gated() -> None:
    authority = RGBContactAuthority(CONTACT_DEVELOPMENT)
    try:
        observation = authority.reset()
        assert set(observation) == {"rgb", "timestamp"}
        assert observation["rgb"].shape == (112, 176, 3)
        assert not {"agent_x", "payload_x", "velocity", "mass"} & set(observation)
        with pytest.raises(RuntimeError, match="commit_before_act_required"):
            authority.step({"push": 0.2})
        for action in ({}, {"push": 2.0}, {"push": 0.2, "shell": 1.0}):
            with pytest.raises((ValueError, TypeError)):
                authority._validated(action)
    finally:
        authority.close()


def test_composed_physical_skill_is_persisted_and_parent_bound() -> None:
    import json

    result = json.loads((REPO_ROOT / "results/hexcore_rgb_contact_occlusion_skill_composition.json").read_text())
    capsule = json.loads((REPO_ROOT / "backend/modules/hexcore/data/physical_skill_capsules/rgb_contact_occlusion.json").read_text())
    parent_state = json.loads((REPO_ROOT / "backend/modules/hexcore/data/rgb_belief_state_mujoco/state.json").read_text())
    assert result["passed"] is True
    assert result["gate"]["sealed_success"] == result["gate"]["sealed_worlds"] == 4
    assert result["gate"]["cold_success"] == 0
    assert result["gate"]["occlusion_recovery"] is True
    assert capsule["parent_procedure_id"] == PARENT_PROCEDURE_ID
    assert parent_state["champions"]["rgb_belief_state_physical_planning"] == PARENT_PROCEDURE_ID
    expected = contact_hash({key: value for key, value in capsule.items() if key != "capsule_digest"})
    assert capsule["capsule_digest"] == expected
    assert all(result["restart"].values())


def test_composed_skill_rejects_missing_or_tampered_parent(tmp_path: Path) -> None:
    path = tmp_path / "backend/modules/hexcore/data/rgb_belief_state_mujoco/state.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"champions":{"rgb_belief_state_physical_planning":"untrusted"},"rgb_belief_state_physical_methods":{}}')
    with pytest.raises(RuntimeError, match="retained_rgb_parent_not_authorized"):
        _load_parent(tmp_path)


def test_articulated_authority_is_rgb_only_and_action_gated() -> None:
    authority = RGBArticulatedAuthority(ARM_DEVELOPMENT)
    try:
        observation = authority.reset()
        assert set(observation) == {"rgb", "timestamp"}
        assert observation["rgb"].shape == (128, 192, 3)
        assert not {"qpos", "qvel", "joint_angles", "target_stage"} & set(observation)
        with pytest.raises(RuntimeError, match="commit_before_act_required"):
            authority.step({"joint_a": 0.0, "joint_b": 0.0})
        for action in ({}, {"joint_a": 2, "joint_b": 0},
                       {"joint_a": 0, "joint_b": float("nan")},
                       {"joint_a": 0, "joint_b": 0, "shell": 1}):
            with pytest.raises((ValueError, TypeError)):
                authority.validate(action)
    finally:
        authority.close()


def test_articulated_sequence_skill_is_composed_persistent_and_fail_closed() -> None:
    import json

    result = json.loads((REPO_ROOT / "results/hexcore_rgb_articulated_sequence_skill.json").read_text())
    capsule = json.loads((REPO_ROOT / "backend/modules/hexcore/data/physical_skill_capsules/rgb_articulated_sequence.json").read_text())
    assert result["passed"] is True
    assert result["gate"]["sealed_success"] == result["gate"]["sealed_worlds"] == 4
    assert result["gate"]["cold_success"] == 0
    assert result["gate"]["sequential_targets_per_world"] == 3
    assert result["gate"]["occlusion_recovery"] is True
    assert capsule["parent_procedure_id"] == ARM_PARENT_PROCEDURE_ID
    assert capsule["name"] == "rgb_articulated_sequential_reaching"
    assert all(result["restart"].values())
