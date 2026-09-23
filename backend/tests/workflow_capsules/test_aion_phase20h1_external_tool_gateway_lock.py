import pytest

from backend.services.aion_mission_mode.external_tool_gateway import (
    create_capability_receipt,
    create_capability_registry,
    create_tool_call_request,
    evaluate_tool_call,
    gateway_summary,
    get_capability,
    validate_tool_mode,
)


def test_phase20h1_tool_modes_validate() -> None:
    assert validate_tool_mode("safe_internal") == "safe_internal"
    assert validate_tool_mode("read_only_external") == "read_only_external"
    assert validate_tool_mode("staged_external") == "staged_external"
    assert validate_tool_mode("approved_live_external") == "approved_live_external"


def test_phase20h1_unknown_tool_mode_rejected() -> None:
    with pytest.raises(ValueError):
        validate_tool_mode("raw_uncontrolled_browser")


def test_phase20h1_registry_hash_is_deterministic() -> None:
    first = create_capability_registry()
    second = create_capability_registry()
    assert first["registry_hash"] == second["registry_hash"]


def test_phase20h1_registry_contains_expected_providers() -> None:
    registry = create_capability_registry()
    assert "domain_provider" in registry["providers"]
    assert "vercel" in registry["providers"]
    assert "meta" in registry["providers"]
    assert "payment_provider" in registry["providers"]


def test_phase20h1_get_capability() -> None:
    registry = create_capability_registry()
    capability = get_capability(registry=registry, tool_name="buy_domain")
    assert capability["provider"] == "domain_provider"
    assert capability["tool_mode"] == "approved_live_external"


def test_phase20h1_unregistered_tool_blocked() -> None:
    registry = create_capability_registry()
    request = create_tool_call_request(
        mission_id="mission_001",
        mission_run_id="run_001",
        step_id="step_001",
        tool_name="unknown_tool",
        requested_by="aion_pilot",
        payload={},
    )

    result = evaluate_tool_call(registry=registry, request=request, evaluation_time=100)

    assert result["allowed"] is False
    assert "unregistered_tool_blocked" in result["reasons"]


def test_phase20h1_raw_model_access_blocked_even_for_safe_tool() -> None:
    registry = create_capability_registry()
    request = create_tool_call_request(
        mission_id="mission_001",
        mission_run_id="run_001",
        step_id="step_001",
        tool_name="generate_copy",
        requested_by="model",
        payload={"brief": "draft homepage"},
    )

    result = evaluate_tool_call(
        registry=registry,
        request=request,
        evaluation_time=100,
        caller="model",
    )

    assert result["allowed"] is False
    assert "raw_model_tool_access_blocked" in result["reasons"]


def test_phase20h1_safe_internal_tool_allowed_for_pilot() -> None:
    registry = create_capability_registry()
    request = create_tool_call_request(
        mission_id="mission_001",
        mission_run_id="run_001",
        step_id="step_001",
        tool_name="generate_copy",
        requested_by="aion_pilot",
        payload={"brief": "draft homepage"},
    )

    result = evaluate_tool_call(registry=registry, request=request, evaluation_time=100)

    assert result["allowed"] is True
    assert result["tool_mode"] == "safe_internal"
    assert result["tool_call_hash"].startswith("sha256:")


def test_phase20h1_read_only_external_allowed_without_payload_approval() -> None:
    registry = create_capability_registry()
    request = create_tool_call_request(
        mission_id="mission_001",
        mission_run_id="run_001",
        step_id="step_001",
        tool_name="domain_availability_check",
        requested_by="aion_pilot",
        payload={"domain": "homefixed.es"},
    )

    result = evaluate_tool_call(registry=registry, request=request, evaluation_time=100)

    assert result["allowed"] is True
    assert result["tool_mode"] == "read_only_external"


def test_phase20h1_staged_external_allowed_without_live_approval() -> None:
    registry = create_capability_registry()
    request = create_tool_call_request(
        mission_id="mission_001",
        mission_run_id="run_001",
        step_id="step_001",
        tool_name="prepare_vercel_deploy",
        requested_by="aion_pilot",
        payload={"project": "homefixed"},
    )

    result = evaluate_tool_call(registry=registry, request=request, evaluation_time=100)

    assert result["allowed"] is True
    assert result["tool_mode"] == "staged_external"


def test_phase20h1_live_tool_requires_approved_payload_hash() -> None:
    registry = create_capability_registry()
    request = create_tool_call_request(
        mission_id="mission_001",
        mission_run_id="run_001",
        step_id="buy_domain",
        tool_name="buy_domain",
        requested_by="aion_pilot",
        payload={"domain": "homefixed.es", "cost": "11.99 EUR"},
    )

    result = evaluate_tool_call(registry=registry, request=request, evaluation_time=100)

    assert result["allowed"] is False
    assert "missing_approved_payload_hash" in result["reasons"]
    assert "missing_approval_hash" in result["reasons"]


def test_phase20h1_live_tool_blocks_payload_mismatch() -> None:
    registry = create_capability_registry()
    request = create_tool_call_request(
        mission_id="mission_001",
        mission_run_id="run_001",
        step_id="buy_domain",
        tool_name="buy_domain",
        requested_by="aion_pilot",
        payload={"domain": "homefixed.es", "cost": "11.99 EUR"},
        approved_payload_hash="sha256:old",
        approval_hash="sha256:approval",
        approval_expires_at=200,
    )

    result = evaluate_tool_call(registry=registry, request=request, evaluation_time=100)

    assert result["allowed"] is False
    assert "payload_hash_mismatch" in result["reasons"]


def test_phase20h1_live_tool_blocks_expired_approval() -> None:
    registry = create_capability_registry()
    payload = {"domain": "homefixed.es", "cost": "11.99 EUR"}
    request = create_tool_call_request(
        mission_id="mission_001",
        mission_run_id="run_001",
        step_id="buy_domain",
        tool_name="buy_domain",
        requested_by="aion_pilot",
        payload=payload,
        approval_hash="sha256:approval",
        approval_expires_at=50,
    )
    request["approved_payload_hash"] = request["payload_hash"]

    result = evaluate_tool_call(registry=registry, request=request, evaluation_time=100)

    assert result["allowed"] is False
    assert "approval_expired" in result["reasons"]


def test_phase20h1_live_tool_allowed_with_exact_unexpired_approval() -> None:
    registry = create_capability_registry()
    payload = {"domain": "homefixed.es", "cost": "11.99 EUR"}
    request = create_tool_call_request(
        mission_id="mission_001",
        mission_run_id="run_001",
        step_id="buy_domain",
        tool_name="buy_domain",
        requested_by="aion_pilot",
        payload=payload,
        approval_hash="sha256:approval",
        approval_expires_at=200,
    )
    request["approved_payload_hash"] = request["payload_hash"]

    result = evaluate_tool_call(registry=registry, request=request, evaluation_time=100)

    assert result["allowed"] is True
    assert result["tool_mode"] == "approved_live_external"


def test_phase20h1_capability_receipt_created_for_allowed_call() -> None:
    registry = create_capability_registry()
    request = create_tool_call_request(
        mission_id="mission_001",
        mission_run_id="run_001",
        step_id="step_001",
        tool_name="domain_availability_check",
        requested_by="aion_pilot",
        payload={"domain": "homefixed.es"},
    )
    evaluation = evaluate_tool_call(registry=registry, request=request, evaluation_time=100)

    receipt = create_capability_receipt(
        evaluation=evaluation,
        provider_response={"available": True},
        before_state_hash="sha256:before",
        after_state_hash="sha256:after",
        evidence_hashes=["sha256:evidence"],
    )

    assert receipt["receipt_hash"].startswith("sha256:")
    assert receipt["provider_response_hash"].startswith("sha256:")
    assert receipt["requested_payload_hash"] == receipt["executed_payload_hash"]


def test_phase20h1_receipt_rejected_for_blocked_call() -> None:
    registry = create_capability_registry()
    request = create_tool_call_request(
        mission_id="mission_001",
        mission_run_id="run_001",
        step_id="buy_domain",
        tool_name="buy_domain",
        requested_by="aion_pilot",
        payload={"domain": "homefixed.es"},
    )
    evaluation = evaluate_tool_call(registry=registry, request=request, evaluation_time=100)

    with pytest.raises(ValueError):
        create_capability_receipt(evaluation=evaluation)


def test_phase20h1_gateway_summary_counts_modes() -> None:
    registry = create_capability_registry()
    summary = gateway_summary(registry)

    assert summary["capability_count"] == registry["capability_count"]
    assert summary["tool_mode_counts"]["approved_live_external"] >= 1
    assert summary["summary_hash"].startswith("sha256:")


def test_phase20h1_custom_registry_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError):
        create_capability_registry(
            providers={"internal": {"provider_type": "internal"}},
            capabilities={
                "bad_tool": {
                    "provider": "missing_provider",
                    "tool_mode": "safe_internal",
                    "risk_level": "low",
                    "requires_payload_approval": False,
                }
            },
        )
