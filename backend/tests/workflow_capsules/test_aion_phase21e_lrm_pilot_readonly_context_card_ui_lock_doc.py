from pathlib import Path


DOC = Path("docs/rfc/aion_phase21e_lrm_pilot_readonly_context_card_lock.tex")


def test_phase21e_doc_exists():
    assert DOC.exists()


def test_phase21e_doc_contains_core_terms():
    text = DOC.read_text()

    for term in [
        "Phase 21E",
        "Read-only LRM Context Card",
        "existing Pilot stream",
        "renderAionLrmPilotContextReadonlyCard",
        "renderAionPilotSimpleTaskStream",
        "getAionPilotFrontendInteractionState",
        "lrm_pilot_context_payload",
        "lrm_context_payload_hash",
        "lrm_next_review_state",
        "lrm_loop_hash",
        "visible_stream_events",
        "read-only",
        "no duplicate Pilot",
        "no UI redesign",
        "preview-only",
        "human review",
        "no booking",
        "no payment",
        "no escrow",
        "no external message",
        "no live chain",
        "no workflow execution",
        "no private chain-of-thought",
        "Tessaris AI",
        "Kevin Robinson",
    ]:
        assert term in text
