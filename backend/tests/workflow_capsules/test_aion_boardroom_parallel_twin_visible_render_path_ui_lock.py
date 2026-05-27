from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    assert APP.exists(), "desktop/mac/src/app.js must exist"
    return APP.read_text()


def test_visible_render_path_installer_exists():
    text = _text()
    assert "installBoardroomParallelTwinVisibleRenderPathV0" in text
    assert "renderBoardroomParallelTwinVisibleRenderPathV0" in text
    assert "mountBoardroomParallelTwinVisibleRenderPathV0" in text
    assert "window.renderBoardroomParallelTwinVisibleRenderPathV0" in text
    assert "window.mountBoardroomParallelTwinVisibleRenderPathV0" in text


def test_visible_render_path_calls_payload_bridge():
    text = _text()
    section_start = text.find("installBoardroomParallelTwinVisibleRenderPathV0")
    assert section_start >= 0
    section = text[section_start:]

    assert "renderBoardroomParallelTwinPayloadBridgeV0" in section
    assert "boardroom-parallel-twin-visible-render-path-v0" in section
    assert "boardroom-parallel-twin-visible-mount-v0" in section


def test_visible_render_path_references_home_fixed_context():
    text = _text()
    section_start = text.find("installBoardroomParallelTwinVisibleRenderPathV0")
    assert section_start >= 0
    section = text[section_start:]

    for term in [
        "Home Fixed",
        "home_fixed",
        "home_repair",
        "Parallel Twin",
        "Machine Trace",
        "Visibility only",
    ]:
        assert term in section


def test_visible_render_path_preserves_safety_boundary():
    text = _text()
    section_start = text.find("installBoardroomParallelTwinVisibleRenderPathV0")
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


def test_visible_render_path_does_not_expose_live_controls():
    text = _text()
    section_start = text.find("installBoardroomParallelTwinVisibleRenderPathV0")
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
