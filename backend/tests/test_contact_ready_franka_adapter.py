from __future__ import annotations

import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "results/hexcore_contact_ready_franka_adapter_v4.json"
ARCHIVE = ROOT / "results/immutable/isaac_precision_franka/contact_ready_franka_v4.npz"
POLICY = ROOT / "integrations/isaac_lab/aion_precision_franka_policy.py"


def test_contact_readiness_is_development_derived_and_sealed() -> None:
    result = json.loads(RESULT.read_text())
    gate = result["contact_readiness_gate"]
    assert result["offline_gates_passed"]
    assert result["physx_tournament_authorized"]
    assert gate["passed"]
    assert gate["development_derived_position_tolerance_m"] >= .032
    assert gate["development_derived_orientation_tolerance_rad"] >= .60
    assert gate["sealed_coverage"] >= .80
    assert result["runtime_contract"]["privileged_runtime_inputs"] == 0
    assert result["runtime_contract"]["teacher_present"] is False
    relation = result["contact_relation_gate"]
    assert relation["contact_relation_time_aligned"] is True
    # The grasp-time cube pose corrects the reset-to-table settling error that
    # made v3 command an empty close about 30 mm below the learned contact.
    assert relation["mean_contact_offset_m"][2] > .085
    assert relation["mean_reset_to_grasp_settling_correction_m"][2] > .025
    assert relation["median_tool_object_error_m"] <= .02
    assert relation["sealed_20mm_coverage"] >= .80


def test_portable_runtime_contains_typed_readiness_envelope() -> None:
    with np.load(ARCHIVE, allow_pickle=False) as capsule:
        assert capsule["contact_readiness_tolerances"].shape == (2,)
        assert np.all(np.isfinite(capsule["contact_readiness_tolerances"]))
        assert capsule["contact_readiness_tolerances"][0] >= .032
        assert capsule["contact_readiness_tolerances"][1] >= .60


def test_contact_occlusion_belief_is_bounded_and_grounded() -> None:
    source = POLICY.read_text()
    assert "self.frozen_xy is not None and self.phase >= 1" in source
    assert "self.occlusion_age < 48" in source
    assert "self.occlusion_age += 1" in source
    assert '"visual_geometry_ood"' in source
