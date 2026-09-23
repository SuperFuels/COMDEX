from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    assert APP.exists(), "desktop/mac/src/app.js must exist"
    return APP.read_text()


def test_boardroom_parallel_twin_payload_mount_renderer_exists():
    text = _text()
    assert "renderBoardroomParallelTwinPayloadMountV0" in text
    assert "window.renderBoardroomParallelTwinPayloadMountV0" in text
    assert "boardroom-parallel-twin-payload-mount-v0" in text


def test_boardroom_parallel_twin_payload_mount_renders_live_payload_sections():
    text = _text()
    for term in [
        "Machine Catalog",
        "Machine Cart",
        "Quote Preview",
        "FulfilmentJob",
        "Settlement Readiness",
        "Proof Receipt",
        "Exception Recovery",
        "Machine Trace",
        "Payload Hash",
        "Home Fixed",
    ]:
        assert term in text


def test_boardroom_parallel_twin_payload_mount_reads_payload_fields():
    text = _text()
    for term in [
        "machine_catalog",
        "machine_cart",
        "quote_preview",
        "fulfilment_job_preview",
        "settlement_readiness",
        "proof_receipt",
        "exception_recovery",
        "machine_trace_preview",
        "payload_hash",
        "safety",
    ]:
        assert term in text


def test_boardroom_parallel_twin_payload_mount_preserves_safety_boundary():
    text = _text()
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
        assert term in text


def test_boardroom_parallel_twin_payload_mount_has_no_live_execute_button():
    text = _text()
    section_start = text.find("renderBoardroomParallelTwinPayloadMountV0")
    assert section_start >= 0
    section = text[section_start:]
    banned = [
        "Execute Now",
        "Run Live",
        "Create Booking",
        "Take Payment",
        "Create Escrow",
        "Send Message",
    ]
    for term in banned:
        assert term not in section
