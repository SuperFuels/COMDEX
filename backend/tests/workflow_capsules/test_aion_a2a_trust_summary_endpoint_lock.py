from backend.modules.aion_gateway.a2a_trust_summary import (
    A2A_TRUST_SUMMARY_CONTRACT_VERSION,
    build_a2a_trust_summary_endpoint_preview,
    build_a2a_trust_summary_endpoint_summary,
)


def test_a2a_trust_summary_endpoint_preview_shape():
    payload = build_a2a_trust_summary_endpoint_preview()

    assert payload["ok"] is True
    assert payload["status"] == "trust_summary_preview_ready"
    assert payload["contract_version"] == A2A_TRUST_SUMMARY_CONTRACT_VERSION
    assert payload["endpoint_key"] == "trust_summary"
    assert payload["method"] == "GET"
    assert payload["path"] == "/api/aion/a2a/home_fixed/trust_summary"
    assert payload["schema_versioned"] is True
    assert payload["deterministic_response"] is True
    assert payload["preview_only"] is True
    assert payload["guarded"] is True
    assert payload["requires_auth"] is True
    assert payload["auth_mode"] == "api_key_or_signed_agent_preview"


def test_a2a_trust_summary_endpoint_uses_home_fixed_defaults():
    payload = build_a2a_trust_summary_endpoint_preview()
    summary = payload["trust_summary"]

    assert payload["business_id"] == "home_fixed"
    assert payload["business_name"] == "Home Fixed"
    assert payload["vertical_key"] == "home_repair"
    assert payload["industry_key"] == "trades"

    assert summary["business_id"] == "home_fixed"
    assert summary["business_name"] == "Home Fixed"
    assert summary["vertical_key"] == "home_repair"
    assert summary["industry_key"] == "trades"


def test_a2a_trust_summary_contains_required_metrics():
    payload = build_a2a_trust_summary_endpoint_preview()
    summary = payload["trust_summary"]

    for key in [
        "verified_completed_jobs",
        "disputed_jobs",
        "cancelled_jobs",
        "failed_jobs",
        "average_response_time_minutes",
        "average_completion_time_minutes",
        "evidence_backed_completion_rate",
        "proof_commitment_rate",
        "proof_verification_success_rate",
        "quote_reliability_rate",
        "recovery_success_rate",
        "trust_score_preview",
        "trust_tier_preview",
        "explainability_notes",
        "trust_summary_hash",
    ]:
        assert key in summary


def test_a2a_trust_summary_rates_are_clamped():
    payload = build_a2a_trust_summary_endpoint_preview(
        {
            "evidence_backed_completion_rate": 5,
            "proof_commitment_rate": -1,
            "proof_verification_success_rate": 0.8,
            "quote_reliability_rate": "0.7",
            "recovery_success_rate": "bad",
        }
    )
    summary = payload["trust_summary"]

    assert summary["evidence_backed_completion_rate"] == 1.0
    assert summary["proof_commitment_rate"] == 0.0
    assert summary["proof_verification_success_rate"] == 0.8
    assert summary["quote_reliability_rate"] == 0.7
    assert summary["recovery_success_rate"] == 0.0


def test_a2a_trust_summary_is_deterministic():
    first = build_a2a_trust_summary_endpoint_preview()
    second = build_a2a_trust_summary_endpoint_preview()

    assert first["trust_summary"]["trust_summary_hash"] == second["trust_summary"]["trust_summary_hash"]
    assert first["response_hash"] == second["response_hash"]
    assert first["bundle_hash"] == second["bundle_hash"]


def test_a2a_trust_summary_hash_changes_when_metrics_change():
    first = build_a2a_trust_summary_endpoint_preview({"verified_completed_jobs": 1})
    second = build_a2a_trust_summary_endpoint_preview({"verified_completed_jobs": 2})

    assert first["trust_summary"]["trust_summary_hash"] != second["trust_summary"]["trust_summary_hash"]
    assert first["response_hash"] != second["response_hash"]
    assert first["bundle_hash"] != second["bundle_hash"]


def test_a2a_trust_summary_does_not_expose_public_ranking():
    payload = build_a2a_trust_summary_endpoint_preview()
    summary = payload["trust_summary"]

    assert payload["public_route_exposed"] is False
    assert payload["public_ranking_exposed"] is False
    assert payload["no_public_ranking"] is True
    assert summary["public_ranking_exposed"] is False
    assert summary["no_public_ranking"] is True


def test_a2a_trust_summary_safety_boundary():
    payload = build_a2a_trust_summary_endpoint_preview()
    safety = payload["safety"]

    assert safety["preview_only"] is True
    assert safety["human_review_required"] is True
    assert safety["public_route_exposed"] is False
    assert safety["public_ranking_exposed"] is False
    assert safety["no_public_ranking"] is True

    for key in [
        "would_execute_workflow",
        "would_create_booking",
        "would_create_live_job",
        "would_confirm_final_completion",
        "would_move_money",
        "would_move_pho",
        "would_require_wallet",
        "would_create_payment",
        "would_create_escrow",
        "would_release_funds",
        "would_send_external_message",
        "live_status_polling_enabled",
    ]:
        assert safety[key] is False


def test_a2a_trust_summary_blocked_reasons_are_explicit():
    payload = build_a2a_trust_summary_endpoint_preview()
    blocked = payload["blocked_reasons"]

    for reason in [
        "preview_only",
        "guarded_endpoint",
        "auth_required",
        "public_route_not_exposed",
        "public_ranking_not_exposed",
        "no_live_execution",
        "no_booking_side_effect",
        "no_payment_side_effect",
        "no_escrow_side_effect",
        "no_external_message_side_effect",
    ]:
        assert reason in blocked


def test_a2a_trust_summary_endpoint_summary_shape():
    summary = build_a2a_trust_summary_endpoint_summary()

    assert summary["ok"] is True
    assert summary["endpoint_key"] == "trust_summary"
    assert summary["business_id"] == "home_fixed"
    assert summary["vertical_key"] == "home_repair"
    assert summary["preview_only"] is True
    assert summary["requires_auth"] is True
    assert summary["public_route_exposed"] is False
    assert summary["public_ranking_exposed"] is False
    assert summary["no_public_ranking"] is True
    assert summary["human_review_required"] is True

    for key in [
        "trust_summary_hash",
        "response_hash",
        "bundle_hash",
        "summary_hash",
    ]:
        assert summary[key]
