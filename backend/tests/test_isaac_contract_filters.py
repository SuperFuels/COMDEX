from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "isaac_contract_filters", ROOT / "integrations/isaac_lab/isaac_contract_filters.py"
)
assert SPEC and SPEC.loader
FILTERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FILTERS)


def test_runner_uses_object_filtered_touch_not_total_contact_force() -> None:
    runner = (ROOT / "integrations/isaac_lab/aion_isaac_lab_runner.py").read_text()
    assert "filter_prim_paths_expr=[cfg.scene.object.prim_path]" in runner
    assert "sensor.data.force_matrix_w" in runner
    assert "sensor.data.net_forces_w" not in runner
    assert "cfg.episode_length_s = max" in runner
    assert 'trajectory["object_position_post"].append(object_position)' in runner
    assert 'trajectory["policy_mode"].append' in runner


def test_runner_tunes_only_arm_damping_for_settled_cartesian_waypoints() -> None:
    runner = (ROOT / "integrations/isaac_lab/aion_isaac_lab_runner.py").read_text()
    assert 'if any("finger" in value for value in expressions)' in runner
    assert "actuator.damping = 20.0" in runner
    assert 'asset_recovery["precision_arm_damping"] = 20.0' in runner
    assert 'raise RuntimeError("precision_arm_actuator_groups_not_identified")' in runner


def test_filter_retains_only_rgb_and_bounded_robot_proprioception() -> None:
    result = FILTERS.permitted_observation(
        {"policy": np.zeros((1, 4), dtype=np.float32)},
        np.zeros((1, 96, 128, 3), dtype=np.uint8),
        np.arange(18, dtype=np.float32), 2, 7,
    )
    assert result["rgb"].shape == (96, 128, 3)
    assert result["proprioception_bounded"].shape == (18,)
    assert set(result) == {"rgb", "timestamp", "episode_id", "observation_sha256",
                           "proprioception_bounded", "proprioception_sha256"}


@pytest.mark.parametrize("key", sorted(FILTERS.PROHIBITED))
def test_privileged_fields_fail_closed_even_when_nested(key: str) -> None:
    with pytest.raises(RuntimeError, match="privileged"):
        FILTERS.permitted_observation(
            {"policy": {key: np.zeros(3)}}, np.zeros((96, 128, 3), dtype=np.uint8),
            np.zeros(18), 0, 0,
        )


def test_invalid_camera_or_proprioception_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="resolution"):
        FILTERS.permitted_observation({}, np.zeros((32, 32, 3), dtype=np.uint8),
                                     np.zeros(18), 0, 0)
    with pytest.raises(RuntimeError, match="proprioception"):
        FILTERS.permitted_observation({}, np.zeros((96, 128, 3), dtype=np.uint8),
                                     np.asarray([np.nan]), 0, 0)
