from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "results" / "hexcore_precision_franka_physx_tournament.json"


def _result() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_precision_franka_challenger_is_rejected_without_champion_regression() -> None:
    result = _result()
    tournament = result["fresh_physx_tournament"]

    assert result["status"] == "challenger_rejected"
    assert result["promotion_gate"]["passed"] is False
    assert result["procedure_id"] is None
    assert result["protected_champion_before"] == result["protected_champion_after"]
    assert tournament["routed_precision"]["strict_lifts"] == 0
    assert tournament["protected_v13"]["strict_lifts"] == 2
    assert tournament["routed_precision"]["unsafe"] == 0
    assert tournament["protected_v13"]["unsafe"] == 0
    assert tournament["teacher_present"] is False
    assert tournament["privileged_runtime_inputs"] == 0


def test_paid_cold_arm_is_omitted_only_after_challenger_cannot_promote() -> None:
    result = _result()
    tournament = result["fresh_physx_tournament"]

    assert tournament["cold"] is None
    assert tournament["routed_precision"]["strict_lifts"] <= tournament["protected_v13"]["strict_lifts"]
    assert tournament["cold_omission_reason"] == (
        "challenger_already_lost_to_protected_v13; additional paid arm cannot authorize promotion"
    )

