from pathlib import Path

DOC = Path("docs/rfc/aion_boardroom_parallel_twin_payload_bridge_lock.tex")


def _text() -> str:
    assert DOC.exists(), "Phase 9D lock doc must exist"
    return DOC.read_text()


def test_payload_bridge_lock_doc_exists_and_is_locked():
    text = _text()
    assert "Phase 9D" in text
    assert "Boardroom Parallel Twin Live Payload Bridge v0" in text
    assert "Status: LOCKED" in text


def test_payload_bridge_lock_doc_lists_frontend_exports():
    text = _text()
    for term in [
        "installBoardroomParallelTwinPayloadBridgeV0",
        "renderBoardroomParallelTwinPayloadBridgeV0",
        "window.renderBoardroomParallelTwinPayloadBridgeV0",
        "window.__aionBoardroomParallelTwinPayloadV0",
        "window.__aionSetBoardroomParallelTwinPayloadV0",
    ]:
        assert term in text


def test_payload_bridge_lock_doc_lists_fallback_identity():
    text = _text()
    for term in [
        "Home Fixed",
        "home_fixed",
        "home_repair",
        "preview_unavailable",
        "payload_hash",
    ]:
        assert term in text


def test_payload_bridge_lock_doc_lists_payload_sections():
    text = _text()
    for term in [
        "machine\\_catalog",
        "machine\\_cart",
        "quote\\_preview",
        "fulfilment\\_job\\_preview",
        "settlement\\_readiness",
        "proof\\_receipt",
        "exception\\_recovery",
        "machine\\_trace\\_preview",
        "safety",
    ]:
        assert term in text


def test_payload_bridge_lock_doc_states_safety_boundary():
    text = _text()
    for term in [
        "create a booking",
        "execute the Goal Engine",
        "move money",
        "move PHO",
        "require a wallet",
        "create a payment",
        "create escrow",
        "send external messages",
        "public A2A route",
        "live execute button",
    ]:
        assert term in text


def test_payload_bridge_lock_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
