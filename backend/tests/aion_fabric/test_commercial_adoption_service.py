from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.modules.aion_business.runtime.commercial_adoption_service import CommercialAdoptionService


def times():
    start = datetime.now(UTC)
    return start, start + timedelta(days=30)


def start_trial(service, **overrides):
    start, end = times()
    values = dict(trial_id="trial.1", tenant_id="tenant.acme", department="sales", actor_id="owner.1",
                  starts_at=start.isoformat(), ends_at=end.isoformat(), action_limit=2,
                  managed_cost_limit=10, currency="EUR", offer_version="sales-2026-09",
                  consent_ref="consent.1")
    values.update(overrides)
    return service.start_trial(**values)


def test_trial_requires_exact_auto_renew_terms(tmp_path):
    service = CommercialAdoptionService(tmp_path)
    with pytest.raises(ValueError, match="auto_renew_terms_required"):
        start_trial(service, auto_renew=True)


def test_trial_is_idempotency_protected_and_one_per_department(tmp_path):
    service = CommercialAdoptionService(tmp_path)
    start_trial(service)
    with pytest.raises(ValueError, match="trial_id_reused"):
        start_trial(service)
    with pytest.raises(ValueError, match="already_active"):
        start_trial(service, trial_id="trial.2")


def test_verified_action_limit_enters_safe_review_only_mode(tmp_path):
    service = CommercialAdoptionService(tmp_path)
    start_trial(service)
    for number in (1, 2):
        service.record_action(action_id=f"action.{number}", trial_id="trial.1", tenant_id="tenant.acme",
                              department="sales", action_type="lead_processed",
                              accounting_class="verified_business_action", funding_class="local_customer_owned",
                              verified=True, receipt_ref=f"receipt.{number}")
    status = service.trial_status(trial_id="trial.1")
    assert status["state"] == "review_only"
    assert status["fallback"]["receive_enquiries"] is True
    assert status["fallback"]["agent_to_agent"] is True
    assert status["fallback"]["autonomous_external_actions"] is False


def test_internal_work_and_customer_tokens_do_not_count_as_actions(tmp_path):
    service = CommercialAdoptionService(tmp_path)
    start_trial(service)
    for number, classification in enumerate(("internal_reasoning", "retry", "deterministic_check", "customer_provider_token"), 1):
        row = service.record_action(action_id=f"action.{number}", trial_id="trial.1", tenant_id="tenant.acme",
                                    department="sales", action_type=classification, accounting_class=classification,
                                    funding_class="customer_provider", verified=True, receipt_ref=f"receipt.{number}", cost=2)
        assert row["counts_as_verified_action"] is False
    assert service.trial_status(trial_id="trial.1")["verified_actions"] == 0


def test_only_tessaris_managed_cost_consumes_trial_budget(tmp_path):
    service = CommercialAdoptionService(tmp_path)
    start_trial(service, managed_cost_limit=5, action_limit=10)
    service.record_action(action_id="local", trial_id="trial.1", tenant_id="tenant.acme", department="sales",
                          action_type="draft", accounting_class="verified_business_action",
                          funding_class="local_customer_owned", verified=True, receipt_ref="r1", cost=100)
    service.record_action(action_id="customer", trial_id="trial.1", tenant_id="tenant.acme", department="sales",
                          action_type="draft", accounting_class="verified_business_action",
                          funding_class="customer_provider", verified=True, receipt_ref="r2", cost=100)
    assert service.trial_status(trial_id="trial.1")["managed_cost"] == 0
    service.record_action(action_id="managed", trial_id="trial.1", tenant_id="tenant.acme", department="sales",
                          action_type="draft", accounting_class="internal_reasoning",
                          funding_class="tessaris_managed", verified=True, receipt_ref="r3", cost=5)
    assert service.trial_status(trial_id="trial.1")["state"] == "review_only"


def test_expired_trial_falls_back_without_abandoning_inbox(tmp_path):
    service = CommercialAdoptionService(tmp_path)
    start, end = times()
    start_trial(service, starts_at=start.isoformat(), ends_at=end.isoformat())
    status = service.trial_status(trial_id="trial.1", as_of=(end + timedelta(seconds=1)).isoformat())
    assert status["state"] == "review_only"
    assert status["fallback"]["prepare_for_review"] is True


def test_cancel_and_paid_activation_retain_hashed_receipts(tmp_path):
    service = CommercialAdoptionService(tmp_path)
    start_trial(service)
    paid = service.activate_paid(trial_id="trial.1", actor_id="owner.1", entitlement_ref="entitlement.1",
                                 billing_receipt_ref="billing.1")
    assert paid["state"] == "paid_active"
    assert "billing.1" not in str(paid)
    cancelled = service.cancel(trial_id="trial.1", actor_id="owner.1", cancellation_ref="cancel.1")
    assert cancelled["state"] == "cancelled"
    assert cancelled["fallback"]["agent_to_agent"] is True


def test_overage_requires_separate_approval(tmp_path):
    service = CommercialAdoptionService(tmp_path)
    with pytest.raises(ValueError, match="overage_approval_required"):
        service.set_capacity_control(tenant_id="tenant.acme", department="sales", actor_id="owner.1",
                                     monthly_action_limit=100, overage_allowed=True)
    row = service.set_capacity_control(tenant_id="tenant.acme", department="sales", actor_id="owner.1",
                                       monthly_action_limit=100, overage_allowed=True,
                                       overage_approval_ref="approval.1")
    assert row["overage_allowed"] is True


def test_value_ledger_separates_verified_estimated_and_inferred(tmp_path):
    service = CommercialAdoptionService(tmp_path)
    start_trial(service)
    for number, level in enumerate(("verified", "estimated", "inferred"), 1):
        service.record_value(value_id=f"value.{number}", tenant_id="tenant.acme", department="sales",
                             metric="hours_saved", lower=1, upper=2, unit="hours",
                             evidence_level=level, evidence_ref=f"evidence.{number}")
    row = service.value_summary(tenant_id="tenant.acme")["values"][0]
    assert row["lower"] == 3
    assert row["upper"] == 6
    assert row["evidence_levels"] == ["estimated", "inferred", "verified"]


def test_revenue_generated_claim_fails_without_causal_authority(tmp_path):
    service = CommercialAdoptionService(tmp_path)
    with pytest.raises(ValueError, match="causal_authority"):
        service.record_value(value_id="value.1", tenant_id="tenant.acme", department="sales",
                             metric="revenue_generated", lower=1, upper=1, unit="EUR",
                             evidence_level="verified", evidence_ref="evidence.1")
