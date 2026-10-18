from pathlib import Path

DOC = Path("docs/rfc/aion_boardroom_parallel_twin_payload_mount_lock.tex")


def _text() -> str:
    assert DOC.exists(), "Phase 9C Boardroom payload mount lock doc must exist"
    return DOC.read_text()


def test_boardroom_parallel_twin_payload_mount_doc_status_locked():
    text = _text()
    assert "Phase 9C" in text
    assert "Boardroom Parallel Twin UI Payload Mount v0" in text
    assert "Status: LOCKED" in text


def test_boardroom_parallel_twin_payload_mount_doc_mentions_renderer():
    text = _text()
    assert "desktop/mac/src/app.js" in text
    assert "renderBoardroomParallelTwinPayloadMountV0" in text
    assert "window.renderBoardroomParallelTwinPayloadMountV0" in text


def test_boardroom_parallel_twin_payload_mount_doc_lists_payload_sections():
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
        "payload\\_hash",
        "safety",
    ]:
        assert term in text


def test_boardroom_parallel_twin_payload_mount_doc_states_safety_boundary():
    text = _text()
    for term in [
        "create a booking",
        "execute the Goal Engine",
        "bypass human review",
        "move money",
        "move PHO",
        "require a wallet",
        "create a payment",
        "create escrow",
        "send external messages",
        "expose a public A2A route",
        "MUST NOT expose a live execute button",
    ]:
        assert term in text


def test_boardroom_parallel_twin_payload_mount_doc_uses_tessaris_footer():
    text = _text()
    assert "Lock ID: AION-BOARDROOM-PARALLEL-TWIN-PAYLOAD-MOUNT-v0.1" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
