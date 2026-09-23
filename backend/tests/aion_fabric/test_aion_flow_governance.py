from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.modules.aion_business.runtime.aion_flow_governance import AionFlowGovernancePlanner


def actor(**overrides):
    value = {"person_id": "p1", "organisation_id": "o1", "workspace_id": "w1", "role": "owner", "purpose": "analysis"}
    value.update(overrides)
    return value


def policy():
    return {"allowed_roles": ["owner"], "allowed_purposes": ["analysis"], "maximum_external_classification": "internal", "allowed_destinations": ["customer-vpc"], "allowed_residencies": ["eu"]}


def graph():
    return {
        "flow_id": "flow-1",
        "nodes": [
            {"id": "aion", "location": "local"},
            {"id": "model", "location": "customer_cloud", "destination": "customer-vpc", "residency": "eu"},
            {"id": "send", "location": "local", "requires_approval": True, "approval_id": "approval-1", "exact_scope_hash": "scope-1", "separation_of_duty": True},
        ],
        "edges": [{"id": "e1", "source": "aion", "target": "model", "destination": "customer-vpc", "data_classification": "internal", "fields": ["sales.total"], "encrypted": True}],
    }


def test_governance_plan_exposes_boundary_fields_destination_colour_and_exact_approval():
    approval = {"approval_id": "approval-1", "approved": True, "scope_hash": "scope-1", "approver_person_id": "p2", "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()}
    result = AionFlowGovernancePlanner().preflight(graph=graph(), actor=actor(), policy=policy(), approvals=[approval])
    assert result["allowed"] is True
    assert result["edges"][0]["fields"] == ["sales.total"]
    assert result["edges"][0]["colour"] == "indigo"
    assert result["approvals"][0]["valid"] is True


def test_privacy_residency_encryption_and_fallback_cannot_silently_expand():
    value = graph()
    value["edges"][0].update({"data_classification": "restricted", "encrypted": False, "fallback": True, "original_policy": {"maximum_classification": "internal", "destinations": ["local"], "maximum_cost": 0}, "estimated_cost": 2})
    result = AionFlowGovernancePlanner().preflight(graph=value, actor=actor(), policy=policy())
    assert result["allowed"] is False
    reasons = " ".join(result["blocked_explanations"])
    assert "too sensitive" in reasons
    assert "without encryption" in reasons
    assert "fallback" in reasons.lower()
    assert result["restricted_content_exposed_in_explanations"] is False


def test_expiry_revocation_scope_change_and_separation_of_duty_fail_closed():
    expired_actor = actor(membership_expires_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat())
    result = AionFlowGovernancePlanner().preflight(graph=graph(), actor=expired_actor, policy=policy(), approvals=[{"approval_id": "approval-1", "approved": True, "scope_hash": "changed", "approver_person_id": "p1"}])
    assert result["allowed"] is False
    explanations = " ".join(result["blocked_explanations"])
    assert "expired" in explanations
    assert "different authorized person" in explanations


def test_revoked_actor_and_unsupported_role_are_explained_without_private_content():
    result = AionFlowGovernancePlanner().preflight(graph={"flow_id": "x", "nodes": [], "edges": []}, actor=actor(role="viewer", revoked=True), policy=policy())
    assert result["allowed"] is False
    assert result["restricted_content_exposed_in_explanations"] is False
    assert any("role" in item.lower() for item in result["blocked_explanations"])
    assert any("authority" in item.lower() for item in result["blocked_explanations"])
