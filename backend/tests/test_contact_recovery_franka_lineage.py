from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "results/hexcore_contact_recovery_franka_lineage.json"
POLICY = ROOT / "integrations/isaac_lab/aion_precision_franka_policy.py"


def test_completed_contact_recovery_challengers_remain_rejected() -> None:
    result = json.loads(RESULT.read_text())
    completed = result["completed_physx_generations"]
    assert completed["v2_contact_relation"]["aion"]["strict_lifts"] == 1
    assert completed["v2_contact_relation"]["protected_v13"]["strict_lifts"] == 1
    assert completed["v3_replan_backtracking"]["aion"]["strict_lifts"] == 0
    assert completed["v3_replan_backtracking"]["protected_v13"]["strict_lifts"] == 1
    assert completed["v3_replan_backtracking"]["fallback_fraction"] < .10
    assert result["procedure_id"] is None
    assert result["promotion_gate"]["passed"] is False
    assert result["protected_champion_before"] == result["protected_champion_after"]


def test_v4_is_frozen_but_not_credited_without_external_receipt() -> None:
    result = json.loads(RESULT.read_text())
    v4 = result["v4_frozen_challenger"]
    assert v4["external_exam_status"] == "blocked_insufficient_brev_credit"
    assert v4["uncredited"] is True
    assert v4["required_seed_range"] == "99507-99518"
    source = POLICY.read_text()
    for phrase in ("relaxed_progress", "predictive_micro_explore", "slip_recovery_reopen"):
        assert phrase in source
    assert result["safety"]["completed_generations_zero_unsafe"] is True
