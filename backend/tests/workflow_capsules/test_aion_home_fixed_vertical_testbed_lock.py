from __future__ import annotations

from backend.modules.aion_gateway.home_fixed_vertical import (
    HOME_FIXED_VERTICAL_VERSION,
    build_home_fixed_machine_catalog,
    build_home_fixed_machine_cart_request,
    build_home_fixed_quote_preview,
    run_home_fixed_vertical_dry_run,
)


def test_home_fixed_vertical_version_locked():
    assert HOME_FIXED_VERTICAL_VERSION == "aion.home_fixed_vertical.v0.1"


def test_home_fixed_profile_and_catalog_are_present():
    out = run_home_fixed_vertical_dry_run()

    assert out["ok"] is True
    assert out["profile"]["business_id"] == "home_fixed_almeria_001"
    assert out["profile"]["business_name"] == "Home Fixed"
    assert out["catalog"]["vertical_key"] == "home_repair"
    assert "general_home_repair" in out["catalog"]["services"]


def test_home_fixed_customer_request_intake_fixture_exists():
    out = run_home_fixed_vertical_dry_run()

    request = out["request"]
    assert request["business_name"] == "Home Fixed"
    assert request["source_channel"] == "machine_cart"
    assert request["requested_outcome"]
    assert len(request["request_hash"]) == 64


def test_home_fixed_machine_cart_quote_preview_fixture_exists():
    catalog = build_home_fixed_machine_catalog()
    request = build_home_fixed_machine_cart_request()
    quote = build_home_fixed_quote_preview(request, catalog)

    assert quote["ok"] is True
    assert quote["status"] == "preview_ready"
    assert quote["currency"] == "EUR"
    assert quote["human_review_required"] is True
    assert len(quote["quote_hash"]) == 64


def test_home_fixed_fulfilment_job_preview_fixture_exists():
    out = run_home_fixed_vertical_dry_run()

    job = out["fulfilment_job_preview"]
    assert job["business_id"] == "home_fixed_almeria_001"
    assert job["vertical_key"] == "home_repair"
    assert job["current_stage"] == "requested"
    assert job["next_expected_event"] == "human_review"
    assert job["would_execute_workflow"] is False


def test_home_fixed_provider_assignment_and_timeline_fixtures_exist():
    out = run_home_fixed_vertical_dry_run()

    assignment = out["provider_assignment_preview"]
    timeline = out["timeline_preview"]

    assert assignment["provider_assignment"]["provider_id"] == "home_fixed_core_team"
    assert assignment["would_notify_provider"] is False
    assert timeline["append_only_preview"] is True
    assert timeline["would_mutate_live_timeline"] is False
    assert len(timeline["timeline_hash"]) == 64


def test_home_fixed_evidence_and_settlement_fixtures_exist():
    out = run_home_fixed_vertical_dry_run()

    evidence = out["evidence_completion_preview"]
    settlement = out["settlement_readiness_preview"]

    assert evidence["completion_confirmed"] is True
    assert len(evidence["evidence_items"]) == 3
    assert len(evidence["evidence_bundle_hash"]) == 64
    assert settlement["settlement_mode"] == "fiat_first"
    assert settlement["payment_ready"] is True
    assert settlement["would_move_money"] is False
    assert settlement["would_require_wallet"] is False


def test_home_fixed_commits_and_verifies_proof_receipt_preview():
    out = run_home_fixed_vertical_dry_run()

    proof = out["job_proof"]
    receipt = out["glyphchain_proof_receipt"]

    assert len(proof["job_proof_hash"]) == 64
    assert receipt["ok"] is True
    assert receipt["verified"] is True
    assert receipt["status"] in {"verified", "preview_fallback"}


def test_home_fixed_machine_trace_preview_exposes_internal_a2a_state():
    out = run_home_fixed_vertical_dry_run()

    trace = out["machine_trace_preview"]
    assert trace["business_id"] == "home_fixed_almeria_001"
    assert trace["status"] == "preview_ready"
    assert trace["public_route_exposed"] is False
    assert "provider_assignment" in trace
    assert "evidence_state" in trace
    assert "settlement_readiness_state" in trace
    assert "proof_commitment_state" in trace
    assert len(trace["machine_trace_hash"]) == 64


def test_home_fixed_vertical_dry_run_has_no_live_side_effects():
    out = run_home_fixed_vertical_dry_run()

    assert out["human_review_required"] is True
    assert out["would_execute_workflow"] is False
    assert out["would_create_booking"] is False
    assert out["would_move_money"] is False
    assert out["would_create_payment"] is False
    assert out["would_create_escrow"] is False
    assert out["public_route_exposed"] is False


def test_home_fixed_hash_changes_when_service_changes():
    first = run_home_fixed_vertical_dry_run(service_key="general_home_repair")
    second = run_home_fixed_vertical_dry_run(service_key="painting_decorating")

    assert first["job_proof"]["job_proof_hash"] != second["job_proof"]["job_proof_hash"]
    assert first["home_fixed_vertical_hash"] != second["home_fixed_vertical_hash"]
