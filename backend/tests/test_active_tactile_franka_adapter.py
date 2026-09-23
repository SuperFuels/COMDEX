from pathlib import Path

import numpy as np
import pytest

from integrations.isaac_lab.active_tactile_franka_adapter import (
    ActiveTactileFrankaOption,
    build,
)


ROOT = Path(__file__).resolve().parents[2]


def test_active_tactile_franka_adapter_builds_from_promoted_parent(tmp_path: Path) -> None:
    capsule = build(ROOT, tmp_path / "adapter.json")
    assert capsule["gate"]["passed"] is True
    assert capsule["gate"]["opposite_direction_checks"] == 3
    assert capsule["gate"]["malicious_rejected"] == 4
    assert capsule["authority"]["forbidden"] == [
        "object_pose", "contact_geometry", "reward", "teacher_action"
    ]


def test_active_tactile_option_is_temporal_and_fail_closed(tmp_path: Path) -> None:
    option = ActiveTactileFrankaOption(build(ROOT, tmp_path / "adapter.json"))
    rotation = np.eye(3)
    for _ in range(5):
        assert option.update(np.asarray([1.0, 0.0]), rotation, 2)["reopen_and_correct"] is False
    decision = option.update(np.asarray([1.0, 0.0]), rotation, 2)
    assert decision["reopen_and_correct"] is True
    assert np.linalg.norm(decision["correction_xy"]) <= .01001
    with pytest.raises(ValueError):
        option.update(np.asarray([np.nan, 0.0]), rotation, 2)


def test_balanced_servo_is_bounded_opposed_and_contact_preserving(tmp_path: Path) -> None:
    option = ActiveTactileFrankaOption(build(ROOT, tmp_path / "adapter.json"))
    left = option.balanced_servo(np.asarray([50., 5.]), np.eye(3))
    right = option.balanced_servo(np.asarray([5., 50.]), np.eye(3))
    assert np.allclose(left, -right)
    assert 0 < np.linalg.norm(left) <= .002501
    option.reset()
    declared_left = None
    for _ in range(6):
        declared_left = option.update(np.asarray([1.0, 0.0]), np.eye(3), 2)
    assert declared_left is not None
    assert float(np.dot(left, declared_left["correction_xy"])) < 0.0
    assert np.allclose(option.balanced_servo(np.asarray([0., 0.]), np.eye(3)), 0)


def test_vertical_closing_axis_requests_safe_reacquisition_instead_of_crashing(
    tmp_path: Path,
) -> None:
    option = ActiveTactileFrankaOption(build(ROOT, tmp_path / "adapter.json"))
    rotation = np.eye(3)
    # Put the declared local-y closing axis vertically in world coordinates.
    rotation[:, 1] = np.asarray((0.0, 0.0, 1.0))
    rotation[:, 2] = np.asarray((0.0, -1.0, 0.0))
    decision = None
    for _ in range(6):
        decision = option.update(np.asarray([1.0, 0.0]), rotation, 1)
    assert decision is not None
    assert decision["orientation_unsafe"] is True
    assert decision["reopen_and_correct"] is False
    assert np.allclose(decision["correction_xy"], 0.0)
