from pathlib import Path

import numpy as np
import pytest

from backend.modules.hexcore.precision_control_apprenticeship import (
    DEVELOPMENT_WORLDS,
    PredictivePrecisionController,
    PrecisionMotionAuthority,
    PrecisionWorld,
    run,
)


def test_precision_authority_fails_closed():
    authority = PrecisionMotionAuthority(DEVELOPMENT_WORLDS[0])
    with pytest.raises(ValueError):
        authority.commit(np.asarray([np.nan]), np.asarray([0.0]))
    with pytest.raises(ValueError):
        authority.commit(np.asarray([2.0]), np.asarray([0.0]))
    with pytest.raises(RuntimeError):
        authority.step(np.asarray([0.0]), np.asarray([0.0]))


def test_world_contract_rejects_inconsistent_dimensions():
    with pytest.raises(ValueError):
        PrecisionWorld("bad", 2, (1.0,), (0.1, 0.1), 0, (0.0, 0.0))


def test_cross_body_precision_campaign(tmp_path: Path):
    state_path = tmp_path / "state.json"
    result = run(tmp_path, tmp_path / "result.json", state_path)
    assert result["promotion_authorized"] is True
    assert result["gates"]["sealed_success"] == result["gates"]["sealed_total"]
    assert result["gates"]["sealed_success"] > result["gates"]["cold_success"]
    assert result["gates"]["malicious_rejected"] == 3
    assert result["gates"]["ood_uncontrollable_abstention"] is True
    assert result["gates"]["precision_improvement_factor_vs_cold"] > 1000
    assert result["gates"]["hidden_delay_identification_accuracy"] == 1.0
    assert all(result["restart"].values())
    assert result["retained_method"]["memorized_trajectories"] == 0


def test_uncontrollable_body_causes_abstention():
    authority = PrecisionMotionAuthority(
        PrecisionWorld("weak", 1, (0.01,), (0.4,), 1, (0.8,))
    )
    controller = PredictivePrecisionController()
    model = controller.identify(authority)
    assert model.reliable is False
    with pytest.raises(RuntimeError, match="precision_model_unreliable_abstain"):
        controller.control(authority, model)
