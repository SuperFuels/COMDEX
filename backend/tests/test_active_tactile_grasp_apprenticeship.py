from pathlib import Path

import numpy as np
import pytest

from backend.modules.hexcore.active_tactile_grasp_apprenticeship import (
    AttachmentBelief,
    DEVELOPMENT,
    ActiveTactileController,
    TactileGraspAuthority,
    run,
)


def test_attachment_belief_distinguishes_opposition_and_slip() -> None:
    belief = AttachmentBelief.initial()
    assert belief.update(np.asarray([.02, 0]), "close", False) == "left_only"
    assert belief.update(np.asarray([.02, .02]), "close", False) == "dual_unstable"
    belief.update(np.asarray([.02, .02]), "test_lift", True)
    assert belief.update(np.asarray([.02, .02]), "test_lift", True) == "attached"
    assert belief.update(np.asarray([0, 0]), "lift", True) == "no_contact"
    assert belief.update(np.asarray([0, 0]), "lift", True) == "slipping"


def test_authority_rejects_unsafe_or_malformed_actions() -> None:
    for action in (np.asarray([0.1, 0, 0, 0]), np.asarray([0, 0]),
                   np.asarray([0, 0, np.nan, 0])):
        with pytest.raises(ValueError):
            TactileGraspAuthority.validate(action)


def test_active_tactile_controller_uses_only_bounded_observations() -> None:
    authority = TactileGraspAuthority(DEVELOPMENT[0])
    try:
        result = ActiveTactileController().run(authority)
    finally:
        authority.close()
    assert result["safe"] is True
    assert result["privileged_runtime_geometry_used"] == 0
    assert result["teacher_actions_used"] == 0
    assert result["pre_action_commitments"] == result["steps"]


def test_active_tactile_campaign(tmp_path: Path) -> None:
    result = run(tmp_path, tmp_path / "result.json", tmp_path / "state.json",
                 tmp_path / "capsule.json")
    assert result["gate"]["sealed_success"] >= 10
    assert result["gate"]["sealed_success"] > result["gate"]["binary_baseline_success"]
    assert result["gate"]["weakest_disturbance_group"] >= .75
    assert result["gate"]["unsafe_actions"] == 0
    assert result["gate"]["malicious_rejected"] == 4
    assert result["passed"] is True
    assert all(result["restart"].values())
