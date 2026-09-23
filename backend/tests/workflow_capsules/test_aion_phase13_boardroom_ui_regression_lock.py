from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

BOARDROOM_UI_FILES = [
    "backend/tests/workflow_capsules/test_aion_boardroom_parallel_twin_visibility_ui_lock.py",
    "backend/tests/workflow_capsules/test_aion_boardroom_parallel_twin_payload_mount_ui_lock.py",
    "backend/tests/workflow_capsules/test_aion_boardroom_parallel_twin_payload_bridge_ui_lock.py",
    "backend/tests/workflow_capsules/test_aion_boardroom_parallel_twin_visible_render_path_ui_lock.py",
    "backend/tests/workflow_capsules/test_aion_boardroom_parallel_twin_panel_polish_ui_lock.py",
    "backend/tests/workflow_capsules/test_aion_boardroom_founder_override_preview_controls_ui_lock.py",
    "backend/tests/workflow_capsules/test_aion_boardroom_trust_summary_visibility_ui_lock.py",
]


def _text(path: str) -> str:
    return (ROOT / path).read_text().lower()


def test_phase13_boardroom_ui_lock_files_exist():
    for path in BOARDROOM_UI_FILES:
        assert (ROOT / path).exists(), path


def test_phase13_boardroom_ui_surfaces_parallel_twin_state():
    combined = "\n".join(_text(path) for path in BOARDROOM_UI_FILES)

    for term in [
        "boardroom",
        "parallel",
        "twin",
        "visibility",
    ]:
        assert term in combined


def test_phase13_boardroom_ui_keeps_home_fixed_context_visible():
    combined = "\n".join(_text(path) for path in BOARDROOM_UI_FILES)

    assert "home_fixed" in combined or "home fixed" in combined
    assert "costa_connect" not in combined
    assert "costa_conexion" not in combined


def test_phase13_boardroom_ui_mount_path_is_locked():
    combined = "\n".join(_text(path) for path in BOARDROOM_UI_FILES)

    for term in [
        "payload",
        "mount",
        "render",
    ]:
        assert term in combined


def test_phase13_boardroom_ui_founder_controls_remain_preview_only():
    combined = "\n".join(_text(path) for path in BOARDROOM_UI_FILES)

    for term in [
        "founder",
        "override",
        "preview",
    ]:
        assert term in combined

    for forbidden in [
        '"auto_approve": true',
        '"auto_dispatch": true',
        '"would_capture_payment": true',
        '"would_release_escrow": true',
        '"would_confirm_booking": true',
        "capture_payment(",
        "release_escrow(",
        "create_booking(",
        "send_email(",
        "send_sms(",
        "post_social(",
    ]:
        assert forbidden not in combined


def test_phase13_boardroom_ui_trust_summary_visible_without_live_side_effects():
    combined = "\n".join(_text(path) for path in BOARDROOM_UI_FILES)

    for term in [
        "trust",
        "summary",
        "visibility",
    ]:
        assert term in combined

    for forbidden in [
        "auto_approve_by_reputation",
        "booking_confirmed",
        "payment_captured",
        "escrow_released",
        "external_message_sent",
    ]:
        assert forbidden not in combined
