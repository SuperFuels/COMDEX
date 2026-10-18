from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.commercial_assurance_service import CommercialAssuranceService


def service(tmp_path):
    key = Ed25519PrivateKey.generate()
    return CommercialAssuranceService(tmp_path / "commercial", signing_key=key), key


def test_signed_licence_is_tenant_bound_and_expires(tmp_path):
    value, _key = service(tmp_path)
    expiry = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    licence = value.issue_licence(licence_id="licence.1", tenant_id="tenant.acme", edition="boardroom", expires_at=expiry, limits={"users": 20})
    assert value.verify_licence(licence, tenant_id="tenant.acme")["valid"] is True
    assert value.verify_licence(licence, tenant_id="tenant.other")["reason"] == "licence_tenant_mismatch"
    assert value.verify_licence(licence, tenant_id="tenant.acme", as_of=(datetime.now(UTC) + timedelta(days=31)).isoformat())["reason"] == "licence_expired"


def test_tampered_licence_fails_signature(tmp_path):
    value, _key = service(tmp_path)
    licence = value.issue_licence(licence_id="licence.1", tenant_id="tenant.acme", edition="pilot_free", expires_at=(datetime.now(UTC) + timedelta(days=1)).isoformat())
    tampered = copy.deepcopy(licence)
    tampered["payload"]["edition"] = "sovereign_fabric"
    assert value.verify_licence(tampered, tenant_id="tenant.acme")["reason"] == "licence_signature_invalid"


def test_all_commercial_editions_are_signed_without_customer_data_authority(tmp_path):
    value, _ = service(tmp_path)
    for index, edition in enumerate(("pilot_free", "operator", "boardroom", "growth", "sovereign"), 1):
        licence = value.issue_licence(
            licence_id=f"licence.{index}", tenant_id="tenant.acme", edition=edition,
            expires_at=(datetime.now(UTC) + timedelta(days=30)).isoformat(),
        )
        assert licence["payload"]["customer_data_access_granted"] is False
        assert value.verify_licence(licence, tenant_id="tenant.acme")["valid"] is True


def test_ownership_survives_missing_or_expired_commercial_entitlement(tmp_path):
    value, _ = service(tmp_path)
    assert value.decide_entitlement(None, tenant_id="tenant.acme", feature="brain.export")["allowed"] is True
    expired = value.issue_licence(
        licence_id="licence.expired", tenant_id="tenant.acme", edition="operator",
        expires_at=(datetime.now(UTC) + timedelta(seconds=1)).isoformat(),
    )
    future = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    assert value.decide_entitlement(expired, tenant_id="tenant.acme", feature="brain.restore", as_of=future)["allowed"] is True
    assert value.decide_entitlement(expired, tenant_id="tenant.acme", feature="workflow.scheduled", as_of=future)["allowed"] is False


def test_entitlement_enforces_feature_and_declared_limit(tmp_path):
    value, _ = service(tmp_path)
    licence = value.issue_licence(
        licence_id="licence.operator", tenant_id="tenant.acme", edition="operator",
        expires_at=(datetime.now(UTC) + timedelta(days=30)).isoformat(),
        limits={"workflow.scheduled": 2},
    )
    assert value.decide_entitlement(licence, tenant_id="tenant.acme", feature="workflow.scheduled", current_usage=1)["allowed"] is True
    assert value.decide_entitlement(licence, tenant_id="tenant.acme", feature="workflow.scheduled", current_usage=2)["reason"] == "entitlement_limit_reached"
    assert value.decide_entitlement(licence, tenant_id="tenant.acme", feature="enterprise.identity")["reason"] == "feature_not_entitled"


def test_optional_usage_meter_rejects_private_content_and_separates_currency(tmp_path):
    value, _key = service(tmp_path)
    with pytest.raises(ValueError, match="private_content"):
        value.record_optional_usage(usage_id="u0", tenant_id="tenant.acme", capability="analysis", provider="gpu", units=1, unit_name="minute", cost=1, currency="EUR", provider_receipt_ref="r0", metadata={"prompt": "private"})
    with pytest.raises(ValueError, match="metadata_key_not_allowed"):
        value.record_optional_usage(usage_id="u-unknown", tenant_id="tenant.acme", capability="analysis", provider="gpu", units=1, unit_name="minute", cost=1, currency="EUR", provider_receipt_ref="r-unknown", metadata={"arbitrary": "value"})
    with pytest.raises(ValueError, match="private_content"):
        value.record_optional_usage(usage_id="u-secret-value", tenant_id="tenant.acme", capability="analysis", provider="gpu", units=1, unit_name="minute", cost=1, currency="EUR", provider_receipt_ref="r-secret", metadata={"route_class": "customer prompt payload"})
    value.record_optional_usage(usage_id="u1", tenant_id="tenant.acme", capability="analysis", provider="gpu", units=2, unit_name="minute", cost=1.5, currency="EUR", provider_receipt_ref="r1", metadata={"model_class": "8b"})
    value.record_optional_usage(usage_id="u2", tenant_id="tenant.acme", capability="analysis", provider="gpu", units=1, unit_name="minute", cost=2, currency="GBP", provider_receipt_ref="r2")
    summary = value.usage_summary(tenant_id="tenant.acme")
    assert summary["totals_by_currency"] == {"EUR": 1.5, "GBP": 2.0}
    assert summary["cross_currency_total_suppressed"] is True
    assert summary["private_content_monetized"] is False


def test_telemetry_is_disabled_until_category_consent(tmp_path):
    value, _key = service(tmp_path)
    with pytest.raises(PermissionError, match="not_consented"):
        value.record_diagnostic(tenant_id="tenant.acme", category="availability", component="router", status="healthy")
    policy = value.configure_telemetry(tenant_id="tenant.acme", actor_id="owner", enabled_categories=["availability"])
    assert policy["customer_content_allowed"] is False
    record = value.record_diagnostic(tenant_id="tenant.acme", category="availability", component="router", status="healthy", duration_ms=12)
    assert record["customer_content_stored"] is False
    with pytest.raises(PermissionError):
        value.record_diagnostic(tenant_id="tenant.acme", category="billing", component="meter", status="healthy")


def test_operations_commitments_do_not_invent_current_sla():
    commitments = CommercialAssuranceService.operational_commitments()
    assert commitments["disaster_recovery"]["restore_test_required"] is True
    assert commitments["current_contractual_sla_claimed"] is False


def test_public_guarantees_preserve_provider_independence():
    guarantees = CommercialAssuranceService.public_ownership_guarantees()
    assert guarantees["customer_owns_brain_and_business_map"] is True
    assert guarantees["provider_can_be_replaced"] is True
    assert guarantees["premium_model_not_required_for_core_operation"] is True


def test_external_release_gates_remain_honestly_open():
    gates = CommercialAssuranceService.external_release_gates()
    assert gates["independent_penetration_test"] == "required"
    assert gates["medium_multi_unit_field_pilot"] == "required"
    assert gates["all_satisfied"] is False
