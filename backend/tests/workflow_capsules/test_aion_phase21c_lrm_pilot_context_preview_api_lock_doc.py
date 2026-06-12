from pathlib import Path


DOC = Path("docs/rfc/aion_phase21c_lrm_pilot_context_preview_api_lock.tex")
ROUTER = Path("backend/api/local_node_router.py")


def test_phase21c_doc_exists():
    assert DOC.exists()


def test_phase21c_router_contains_endpoint():
    text = ROUTER.read_text()

    assert "PHASE 21C LOCK: AION-LRM Pilot Context Preview Endpoint" in text
    assert '@router.get("/aion/lrm/pilot-context-preview")' in text
    assert "build_lrm_pilot_context_payload" in text
    assert "would_execute_workflow" in text


def test_phase21c_doc_contains_core_terms():
    text = DOC.read_text()

    for term in [
        "Phase 21C",
        "Local API Preview Endpoint",
        "AION-LRM",
        "Pilot Context Payload",
        "/api/local-node/aion/lrm/pilot-context-preview",
        "backend/api/local_node_router.py",
        "build_lrm_pilot_context_payload",
        "pilot_cockpit_projection",
        "boardroom_projection",
        "business_container_root",
        "preview-only",
        "human review",
        "no booking",
        "no payment",
        "no escrow",
        "no external message",
        "no live chain",
        "no workflow execution",
        "no business-container write",
        "no private chain-of-thought",
        "Tessaris AI",
        "Kevin Robinson",
    ]:
        assert term in text
