from pathlib import Path

DOC = Path("docs/rfc/aion_boardroom_parallel_twin_visible_render_path_lock.tex")


def _text() -> str:
    assert DOC.exists(), "Phase 9E lock doc must exist"
    return DOC.read_text()


def test_visible_render_path_doc_exists_and_is_locked():
    text = _text()
    assert "Phase 9E" in text
    assert "Boardroom Parallel Twin Visible Render Path v0" in text
    assert "Status: LOCKED" in text


def test_visible_render_path_doc_lists_exports():
    text = _text()
    for term in [
        "installBoardroomParallelTwinVisibleRenderPathV0",
        "renderBoardroomParallelTwinVisibleRenderPathV0",
        "mountBoardroomParallelTwinVisibleRenderPathV0",
        "window.renderBoardroomParallelTwinVisibleRenderPathV0",
        "window.mountBoardroomParallelTwinVisibleRenderPathV0",
    ]:
        assert term in text


def test_visible_render_path_doc_mentions_bridge_and_home_fixed():
    text = _text()
    for term in [
        "renderBoardroomParallelTwinPayloadBridgeV0",
        "Home Fixed",
        "home_fixed",
        "home_repair",
    ]:
        assert term in text


def test_visible_render_path_doc_lists_mount_targets():
    text = _text()
    for term in [
        "[data-aion-boardroom]",
        "[data-boardroom-root]",
        "#boardroom",
        "#boardroom-root",
        ".boardroom",
        ".boardroom-root",
        ".boardroom-content",
        ".app-main",
        "main",
    ]:
        assert term in text


def test_visible_render_path_doc_states_safety_boundary():
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


def test_visible_render_path_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
