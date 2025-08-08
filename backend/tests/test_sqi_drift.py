# -*- coding: utf-8 -*-
# backend/tests/test_sqi_drift.py
from backend.modules.sqi.sqi_math_adapter import compute_drift
from backend.modules.sqi.drift_types import DriftStatus

def test_missing_dep_and_incomplete():
    container = {
        "id": "c-test",
        "symbolic_logic": [
            {"name": "lemma_a", "logic": "ok"},
            {"name": "lemma_b", "depends_on": ["lemma_a","missing_1"], "logic": "ok"},
            {"name": "goal_x", "proof_status": "incomplete", "depends_on": ["lemma_b"]},
            {"name": "stub_y"}  # empty logic
        ]
    }
    rep = compute_drift(container)
    assert rep.container_id == "c-test"
    assert rep.status in (DriftStatus.OPEN, DriftStatus.DRIFTING)
    reasons = {g.reason for g in rep.gaps}
    assert "missing_dependencies" in reasons
    assert "incomplete_proof" in reasons
    assert "empty_logic" in reasons
    # weighted total > 0
    assert rep.total_weight > 0