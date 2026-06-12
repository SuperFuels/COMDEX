from pathlib import Path


DOC = Path("docs/rfc/aion_phase21b_lrm_pilot_context_payload_adapter_lock.tex")


def test_phase21b_lock_doc_exists():
    assert DOC.exists()


def test_phase21b_lock_doc_contains_core_terms():
    text = DOC.read_text()

    for term in [
        "Phase 21B",
        "LRM Pilot Context Payload Adapter",
        "AION-LRM",
        "Pilot",
        "Boardroom",
        "Phase 20I",
        "end-to-end decision loop",
        "pilot_cockpit_projection",
        "boardroom_projection",
        "business_container_root",
        "visible_stream_events",
        "artifact",
        "receipt",
        "proof",
        "human review",
        "preview-only",
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
