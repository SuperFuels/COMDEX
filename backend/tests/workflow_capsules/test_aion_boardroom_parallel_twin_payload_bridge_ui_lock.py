from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    assert APP.exists(), "desktop/mac/src/app.js must exist"
    return APP.read_text()


def test_boardroom_parallel_twin_payload_bridge_exists():
    text = _text()
    assert "installBoardroomParallelTwinPayloadBridgeV0" in text
    assert "renderBoardroomParallelTwinPayloadBridgeV0" in text
    assert "window.renderBoardroomParallelTwinPayloadBridgeV0" in text
    assert "boardroom-parallel-twin-payload-bridge-v0" in text


def test_bridge_uses_payload_mount_renderer():
    text = _text()
    assert "renderBoardroomParallelTwinPayloadMountV0" in text
    assert "window.__aionBoardroomParallelTwinPayloadV0" in text
    assert "window.__aionSetBoardroomParallelTwinPayloadV0" in text


def test_bridge_has_safe_fallback_payload():
    text = _text()
    for term in [
        "Home Fixed",
        "home_fixed",
        "home_repair",
        "preview_unavailable",
        "Static fallback",
        "payload_hash",
        "safety",
    ]:
        assert term in text


def test_bridge_preserves_read_only_safety_boundary():
    text = _text()
    section_start = text.find("installBoardroomParallelTwinPayloadBridgeV0")
    assert section_start >= 0
    section = text[section_start:]

    for term in [
        "visibility_only",
        "human_review_required",
        "autonomous_execution_allowed",
        "would_execute_workflow",
        "would_create_booking",
        "would_move_money",
        "would_move_pho",
        "would_require_wallet",
        "would_create_payment",
        "would_create_escrow",
        "would_send_external_message",
        "public_a2a_route_exposed",
    ]:
        assert term in section


def test_bridge_does_not_expose_live_execution_controls():
    text = _text()
    section_start = text.find("installBoardroomParallelTwinPayloadBridgeV0")
    assert section_start >= 0
    section = text[section_start:]

    banned = [
        "Execute Now",
        "Run Live",
        "Create Booking",
        "Take Payment",
        "Create Escrow",
        "Send Message",
        "Charge Customer",
        "Submit Public A2A",
    ]
    for term in banned:
        assert term not in section
