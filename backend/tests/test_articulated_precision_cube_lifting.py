from pathlib import Path

import numpy as np
import pytest

from backend.modules.hexcore.articulated_precision_cube_lifting import (
    ArticulatedCubeAuthority,
    DEVELOPMENT,
    RGBLandmarks,
    run,
)


def test_articulated_authority_rejects_unsafe_actions():
    for action, grip in ((np.asarray([np.nan, 0.0]), 0.0),
                         (np.asarray([2.0, 0.0]), 0.0),
                         (np.asarray([0.0]), 0.0),
                         (np.zeros(2), 2.0)):
        with pytest.raises(ValueError):
            ArticulatedCubeAuthority.validate(action, grip)


def test_rgb_runtime_contains_required_landmarks():
    authority = ArticulatedCubeAuthority(DEVELOPMENT[0])
    try:
        points, visible = RGBLandmarks().locate(authority.observe()["rgb"])
        assert set(points) == {"base", "elbow", "wrist", "cube"}
        assert visible["cube"] is True
    finally:
        authority.close()


def test_articulated_precision_lift_campaign(tmp_path: Path):
    result = run(tmp_path, tmp_path / "result.json", tmp_path / "state.json")
    assert result["gate"]["privileged_runtime_geometry"] == 0
    assert result["gate"]["teacher_actions"] == 0
    assert result["gate"]["malicious_rejected"] == 4
    assert result["gate"]["learned_success"] == result["gate"]["sealed_total"]
    assert result["gate"]["learned_success"] > result["gate"]["cold_success"]
    assert result["gate"]["selective_memory_non_regression"] is True
    assert result["passed"] is True
    assert all(result["restart"].values())
