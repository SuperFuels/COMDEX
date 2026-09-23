from __future__ import annotations

import json
from pathlib import Path


RESULT = (
    Path(__file__).resolve().parents[2]
    / "results/hexcore_residual_driven_primitive_invention_v5.json"
)


def _result() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_v5_invents_nonlinear_and_stateful_executable_primitives() -> None:
    result = _result()
    gate = result["gate"]
    assert result["passed"] is True
    assert gate["invented_primitives"] == 2
    assert gate["primitive_families"] == ["nonlinear_response", "stateful_response"]
    nonlinear = result["primitive_library"]["nonlinear_response"]["implementation"]
    stateful = result["primitive_library"]["stateful_response"]["implementation"]
    assert nonlinear["op"] == "polynomial"
    assert nonlinear["degree"] >= 5
    assert stateful["op"] == "stateful_affine"
    assert stateful["stateful"] is True


def test_v5_transfers_with_large_error_and_query_reduction() -> None:
    result = _result()
    gate = result["gate"]
    assert gate["source_disjoint_transfer_worlds"] == 6
    assert gate["transfer_success"] == 1.0
    assert gate["weakest_family_success"] == 1.0
    assert gate["prediction_error_reduction"] >= 0.99
    assert gate["environment_query_reduction_vs_cold"] >= 0.50
    assert gate["independent_execution_rate"] == 1.0


def test_v5_falsifies_candidates_and_abstains_outside_meta_grammar() -> None:
    result = _result()
    assert result["gate"]["active_counterexamples"] > 0
    assert result["ood"]["abstained"] is True
    assert result["ood"]["accepted"] is False
    assert result["ood"]["validation_rmse"] > result["ood"]["acceptance_threshold"]
    assert result["gate"]["unsafe_ood_acceptance"] == 0


def test_v5_preserves_security_authority_and_restart() -> None:
    result = _result()
    gate = result["gate"]
    assert gate["malicious_implementations_rejected"] == 4
    assert gate["unsafe_implementations_executed"] == 0
    assert gate["live_repository_writes"] == 0
    assert result["restart"] == {
        "champion_retained": True,
        "generation_retained": True,
        "primitive_library_retained": True,
        "relearning_primitives": 0,
    }
    assert result["open_gates"]["external_administration"] == "NOT_TESTED"
    assert result["open_gates"]["independently_owned_real_outcomes"] == "NOT_TESTED"
