from backend.modules.aion_lrm.evidence_gap_envelope import (
    build_default_home_fixed_evidence_gap_envelope,
    build_evidence_gap_envelope,
)
from backend.modules.aion_lrm.evidence_satisfaction_envelope import (
    EVIDENCE_SATISFACTION_ENVELOPE_VERSION,
    build_default_home_fixed_evidence_satisfaction_envelope,
    build_evidence_satisfaction_envelope,
)


def test_phase20h_builds_default_evidence_satisfaction_envelope():
    envelope = build_default_home_fixed_evidence_satisfaction_envelope()

    assert envelope["envelope_version"] == EVIDENCE_SATISFACTION_ENVELOPE_VERSION
    assert envelope["envelope_type"] == "aion_lrm_evidence_satisfaction"
    assert envelope["business_id"] == "home_fixed"
    assert envelope["satisfaction_hash"].startswith("evidence_satisfaction_envelope_")
    assert envelope["summary_hash"].startswith("evidence_satisfaction_summary_")


def test_phase20h_default_evidence_satisfies_default_gap():
    envelope = build_default_home_fixed_evidence_satisfaction_envelope()

    assert envelope["satisfaction_state"]["evidence_gap_satisfied"] is True
    assert envelope["satisfaction_state"]["remaining_missing_evidence"] == []
    assert envelope["satisfaction_state"]["next_review_state"] == "return_to_human_review"
    assert envelope["summary"]["remaining_missing_evidence_count"] == 0


def test_phase20h_partial_evidence_leaves_gap_open():
    gap = build_default_home_fixed_evidence_gap_envelope()
    envelope = build_evidence_satisfaction_envelope(
        gap,
        received_evidence={
            "site_photo": {
                "received": True,
                "evidence_hash": "evidence_site_photo_only",
            }
        },
    )

    assert envelope["satisfaction_state"]["evidence_gap_satisfied"] is False
    assert "roof_or_pergola_measurements" in envelope["satisfaction_state"]["remaining_missing_evidence"]
    assert envelope["satisfaction_state"]["next_review_state"] == "request_more_evidence"


def test_phase20h_links_back_to_gap_and_recommendation():
    gap = build_default_home_fixed_evidence_gap_envelope()
    envelope = build_evidence_satisfaction_envelope(gap)

    assert envelope["source_evidence_gap_hash"] == gap["evidence_gap_hash"]
    assert envelope["source_evidence_gap_summary_hash"] == gap["summary_hash"]
    assert envelope["satisfaction_state"]["unblocks_recommendation_card_hash"]
    assert envelope["satisfaction_state"]["unblocks_recommendation_summary_hash"]


def test_phase20h_records_received_evidence_hashes():
    envelope = build_evidence_satisfaction_envelope(
        received_evidence={
            "site_photo": {"received": True, "evidence_hash": "hash_site_photo"},
            "access_notes": {"received": True, "evidence_hash": "hash_access_notes"},
        }
    )

    assert "hash_site_photo" in envelope["satisfaction_state"]["evidence_hashes"]
    assert "hash_access_notes" in envelope["satisfaction_state"]["evidence_hashes"]


def test_phase20h_custom_gap_can_be_satisfied():
    gap = build_evidence_gap_envelope(
        required_evidence=["before_photo", "material_type"],
    )
    envelope = build_evidence_satisfaction_envelope(
        gap,
        received_evidence={
            "before_photo": {"received": True, "evidence_hash": "hash_before_photo"},
            "material_type": {"received": True, "evidence_hash": "hash_material_type"},
        },
    )

    assert envelope["satisfaction_state"]["evidence_gap_satisfied"] is True
    assert envelope["satisfaction_state"]["remaining_missing_evidence"] == []


def test_phase20h_redacts_private_reasoning_and_credentials():
    envelope = build_evidence_satisfaction_envelope(
        {
            "business_id": "home_fixed",
            "evidence_gap_hash": "gap_hash",
            "summary_hash": "gap_summary_hash",
            "private_chain_of_thought": "PRIVATE_COT_VALUE",
            "access_token": "ACCESS_TOKEN_VALUE",
        },
        received_evidence={
            "site_photo": {
                "received": True,
                "evidence_hash": "hash_site_photo",
                "api_key": "API_KEY_VALUE",
                "hidden_reasoning": "HIDDEN_REASONING_VALUE",
            }
        },
    )

    text = str(envelope)

    assert "PRIVATE_COT_VALUE" not in text
    assert "ACCESS_TOKEN_VALUE" not in text
    assert "API_KEY_VALUE" not in text
    assert "HIDDEN_REASONING_VALUE" not in text
    assert envelope["safety"]["private_chain_of_thought_exposed"] is False
    assert envelope["safety"]["hidden_reasoning_exposed"] is False
    assert envelope["safety"]["credentials_exposed"] is False


def test_phase20h_blocks_all_live_side_effects():
    envelope = build_default_home_fixed_evidence_satisfaction_envelope()
    safety = envelope["safety"]

    assert safety["preview_only"] is True
    assert safety["human_review_required"] is True
    assert safety["evidence_satisfaction_grants_live_permission"] is False
    assert safety["would_create_booking"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_send_external_message"] is False
    assert safety["would_write_live_chain"] is False
    assert safety["would_execute_workflow"] is False
    assert safety["live_side_effects_enabled"] is False


def test_phase20h_is_deterministic_for_same_inputs():
    gap = build_default_home_fixed_evidence_gap_envelope()

    one = build_evidence_satisfaction_envelope(gap)
    two = build_evidence_satisfaction_envelope(gap)

    assert one["satisfaction_hash"] == two["satisfaction_hash"]
    assert one["summary_hash"] == two["summary_hash"]
