from backend.modules.aion_gateway.trust_reputation import (
    TRUST_REPUTATION_VERSION,
    build_business_trust_summary,
    build_home_fixed_trust_summary_fixture,
)


def test_trust_summary_has_version_and_identity():
    out = build_home_fixed_trust_summary_fixture()
    assert out["ok"] is True
    assert out["status"] == "trust_summary_ready"
    assert out["contract_version"] == TRUST_REPUTATION_VERSION

    s = out["trust_summary"]
    assert s["contract_version"] == TRUST_REPUTATION_VERSION
    assert s["business_id"] == "home_fixed"
    assert s["business_name"] == "Home Fixed"
    assert s["vertical_key"] == "home_repair"


def test_trust_summary_tracks_required_counts_and_rates():
    s = build_home_fixed_trust_summary_fixture()["trust_summary"]

    assert s["verified_completed_jobs"] == 2
    assert s["disputed_jobs"] == 1
    assert s["cancelled_jobs"] == 1
    assert s["failed_jobs"] == 1
    assert s["evidence_backed_completion_rate"] == 1.0
    assert s["proof_commitment_rate"] == 1.0
    assert s["proof_verification_success_rate"] == 0.6667
    assert s["quote_reliability_rate"] == 0.6667
    assert s["recovery_success_rate"] == 0.5


def test_trust_summary_tracks_response_and_completion_times():
    s = build_home_fixed_trust_summary_fixture()["trust_summary"]

    assert s["average_response_minutes"] > 0
    assert s["average_completion_hours"] > 0


def test_trust_summary_is_visibility_only_and_not_public_a2a():
    s = build_home_fixed_trust_summary_fixture()["trust_summary"]

    assert s["visibility_only"] is True
    assert s["human_review_required"] is True
    assert s["public_a2a_exposed"] is False


def test_trust_summary_is_explainable():
    s = build_home_fixed_trust_summary_fixture()["trust_summary"]

    notes = " ".join(s["explainability_notes"])
    assert "explainable" in notes
    assert "Verified completions" in notes
    assert "GlyphChain" in notes
    assert "visibility-only" in notes


def test_trust_summary_hash_is_stable_for_same_payload():
    out1 = build_home_fixed_trust_summary_fixture()
    out2 = build_home_fixed_trust_summary_fixture()

    assert out1["trust_summary_hash"] == out2["trust_summary_hash"]


def test_trust_summary_hash_changes_when_job_data_changes():
    out1 = build_business_trust_summary(
        business_id="home_fixed",
        business_name="Home Fixed",
        vertical_key="home_repair",
        jobs=[{"status": "completed", "evidence_backed": True, "proof_committed": True, "proof_verified": True}],
    )
    out2 = build_business_trust_summary(
        business_id="home_fixed",
        business_name="Home Fixed",
        vertical_key="home_repair",
        jobs=[{"status": "failed"}],
    )

    assert out1["trust_summary_hash"] != out2["trust_summary_hash"]


def test_empty_summary_is_safe_zero_state():
    s = build_business_trust_summary(
        business_id="home_fixed",
        business_name="Home Fixed",
        vertical_key="home_repair",
        jobs=[],
    )["trust_summary"]

    assert s["verified_completed_jobs"] == 0
    assert s["evidence_backed_completion_rate"] == 0.0
    assert s["proof_commitment_rate"] == 0.0
    assert s["proof_verification_success_rate"] == 0.0
    assert s["quote_reliability_rate"] == 0.0
    assert s["recovery_success_rate"] == 0.0
    assert s["visibility_only"] is True
