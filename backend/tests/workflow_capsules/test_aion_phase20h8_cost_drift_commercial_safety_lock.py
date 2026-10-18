from backend.services.aion_mission_mode.cost_drift_commercial_safety import (
    bind_commercial_safety_to_external_approval,
    create_commercial_payload_snapshot,
    create_commercial_plan_contract,
    evaluate_cost_drift,
    summarize_cost_drift_evaluations,
)


def _plan(**kwargs):
    base = dict(
        mission_id="mission_001",
        mission_run_id="run_001",
        step_id="buy_domain",
        provider="godaddy",
        action_type="buy_domain",
        target="homefixed.es",
        currency="EUR",
        plan_estimated_cost="10.00",
        cost_variance_percent="5.00",
        cost_variance_fixed="5.00",
        renewal_cost="19.99",
        subscription_term="yearly",
        auto_renew=True,
    )
    base.update(kwargs)
    return create_commercial_plan_contract(**base)


def _payload(**kwargs):
    base = dict(
        mission_id="mission_001",
        mission_run_id="run_001",
        step_id="buy_domain",
        provider="godaddy",
        action_type="buy_domain",
        target="homefixed.es",
        currency="EUR",
        payload_actual_cost="10.20",
        tax_amount="0.00",
        fees_amount="0.00",
        renewal_cost="19.99",
        subscription_term="yearly",
        auto_renew=True,
    )
    base.update(kwargs)
    return create_commercial_payload_snapshot(**base)


def test_phase20h8_plan_hash_deterministic() -> None:
    assert _plan()["commercial_plan_hash"] == _plan()["commercial_plan_hash"]


def test_phase20h8_payload_hash_deterministic() -> None:
    assert _payload()["commercial_payload_hash"] == _payload()["commercial_payload_hash"]


def test_phase20h8_small_cost_drift_allowed() -> None:
    result = evaluate_cost_drift(plan_contract=_plan(), payload_snapshot=_payload(payload_actual_cost="10.20"))
    assert result["allowed"] is True
    assert result["commercial_state"] == "commercial_terms_clear"


def test_phase20h8_large_cost_drift_blocks_re_review() -> None:
    result = evaluate_cost_drift(plan_contract=_plan(), payload_snapshot=_payload(payload_actual_cost="25.00"))
    assert result["allowed"] is False
    assert result["requires_plan_re_review"] is True
    assert "cost_drift_exceeds_threshold" in result["reasons"]


def test_phase20h8_rounding_is_two_decimal_stable() -> None:
    result = evaluate_cost_drift(plan_contract=_plan(plan_estimated_cost="0.30"), payload_snapshot=_payload(payload_actual_cost="0.60"))
    assert result["absolute_delta"] == "0.30"


def test_phase20h8_provider_change_blocks() -> None:
    result = evaluate_cost_drift(plan_contract=_plan(), payload_snapshot=_payload(provider="namecheap"))
    assert result["allowed"] is False
    assert "provider_mismatch" in result["reasons"]


def test_phase20h8_target_change_blocks() -> None:
    result = evaluate_cost_drift(plan_contract=_plan(), payload_snapshot=_payload(target="homefixed.co.uk"))
    assert result["allowed"] is False
    assert "target_mismatch" in result["reasons"]


def test_phase20h8_currency_change_blocks() -> None:
    result = evaluate_cost_drift(plan_contract=_plan(), payload_snapshot=_payload(currency="GBP"))
    assert result["allowed"] is False
    assert "currency_mismatch" in result["reasons"]


def test_phase20h8_renewal_cost_change_blocks() -> None:
    result = evaluate_cost_drift(plan_contract=_plan(), payload_snapshot=_payload(renewal_cost="29.99"))
    assert result["allowed"] is False
    assert "renewal_cost_changed" in result["reasons"]


def test_phase20h8_subscription_term_change_blocks() -> None:
    result = evaluate_cost_drift(plan_contract=_plan(), payload_snapshot=_payload(subscription_term="monthly"))
    assert result["allowed"] is False
    assert "subscription_term_changed" in result["reasons"]


def test_phase20h8_auto_renew_change_blocks() -> None:
    result = evaluate_cost_drift(plan_contract=_plan(), payload_snapshot=_payload(auto_renew=False))
    assert result["allowed"] is False
    assert "auto_renew_changed" in result["reasons"]


def test_phase20h8_tax_and_fee_warnings_present() -> None:
    result = evaluate_cost_drift(
        plan_contract=_plan(),
        payload_snapshot=_payload(tax_amount="2.00", fees_amount="1.00"),
    )
    assert "tax_amount_present" in result["warnings"]
    assert "fees_amount_present" in result["warnings"]


def test_phase20h8_cost_drift_hash_deterministic() -> None:
    first = evaluate_cost_drift(plan_contract=_plan(), payload_snapshot=_payload())
    second = evaluate_cost_drift(plan_contract=_plan(), payload_snapshot=_payload())
    assert first["cost_drift_hash"] == second["cost_drift_hash"]


def test_phase20h8_external_approval_binding_allowed_when_hash_matches() -> None:
    evaluation = evaluate_cost_drift(plan_contract=_plan(), payload_snapshot=_payload())
    approval = {
        "allowed": True,
        "mission_id": "mission_001",
        "mission_run_id": "run_001",
        "step_id": "buy_domain",
        "approved_payload_hash": evaluation["commercial_payload_hash"],
        "approval_hash": "sha256:approval",
    }
    binding = bind_commercial_safety_to_external_approval(
        cost_drift_evaluation=evaluation,
        external_approval=approval,
    )
    assert binding["allowed"] is True


def test_phase20h8_external_approval_binding_blocks_cost_drift() -> None:
    evaluation = evaluate_cost_drift(plan_contract=_plan(), payload_snapshot=_payload(payload_actual_cost="25.00"))
    approval = {
        "allowed": True,
        "mission_id": "mission_001",
        "mission_run_id": "run_001",
        "step_id": "buy_domain",
        "approved_payload_hash": evaluation["commercial_payload_hash"],
        "approval_hash": "sha256:approval",
    }
    binding = bind_commercial_safety_to_external_approval(
        cost_drift_evaluation=evaluation,
        external_approval=approval,
    )
    assert binding["allowed"] is False
    assert "commercial_terms_not_clear" in binding["reasons"]


def test_phase20h8_external_approval_binding_blocks_wrong_payload_hash() -> None:
    evaluation = evaluate_cost_drift(plan_contract=_plan(), payload_snapshot=_payload())
    approval = {
        "allowed": True,
        "mission_id": "mission_001",
        "mission_run_id": "run_001",
        "step_id": "buy_domain",
        "approved_payload_hash": "sha256:wrong",
        "approval_hash": "sha256:approval",
    }
    binding = bind_commercial_safety_to_external_approval(
        cost_drift_evaluation=evaluation,
        external_approval=approval,
    )
    assert binding["allowed"] is False
    assert "approval_payload_not_bound_to_commercial_snapshot" in binding["reasons"]


def test_phase20h8_summary_blocks_when_any_evaluation_blocked() -> None:
    ok = evaluate_cost_drift(plan_contract=_plan(), payload_snapshot=_payload())
    bad = evaluate_cost_drift(plan_contract=_plan(), payload_snapshot=_payload(payload_actual_cost="25.00"))
    summary = summarize_cost_drift_evaluations(
        mission_id="mission_001",
        mission_run_id="run_001",
        evaluations=[ok, bad],
    )
    assert summary["allowed_count"] == 1
    assert summary["blocked_count"] == 1
    assert summary["runtime_state"] == "commercial_re_review_required"


def test_phase20h8_summary_hash_deterministic() -> None:
    ok = evaluate_cost_drift(plan_contract=_plan(), payload_snapshot=_payload())
    first = summarize_cost_drift_evaluations(
        mission_id="mission_001",
        mission_run_id="run_001",
        evaluations=[ok],
    )
    second = summarize_cost_drift_evaluations(
        mission_id="mission_001",
        mission_run_id="run_001",
        evaluations=[ok],
    )
    assert first["summary_hash"] == second["summary_hash"]
