from __future__ import annotations

from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    assert APP.exists(), "desktop/mac/src/app.js must exist"
    return APP.read_text()


def test_boardroom_parallel_twin_surface_has_required_labels_or_safe_placeholder():
    text = _text()

    required_any = [
        "Parallel Twin",
        "Machine Catalog",
        "Machine Cart",
        "Quote Preview",
        "Proof Receipt",
        "Settlement Readiness",
        "Exception Recovery",
    ]

    missing = [term for term in required_any if term not in text]

    # This is a visibility lock starter.
    # It intentionally fails until the Boardroom UI exposes the Phase 7/8 surfaces.
    assert not missing, f"Missing Boardroom Parallel Twin labels: {missing}"


def test_boardroom_must_not_expose_live_execute_without_guarded_approval():
    text = _text()

    forbidden = [
        "Execute Live Job",
        "Autonomous Execute",
        "Run Without Approval",
        "Create Live Booking",
        "Move Money",
        "Create Escrow",
    ]

    found = [term for term in forbidden if term in text]
    assert not found, f"Unsafe Boardroom live execution wording found: {found}"


def test_boardroom_should_reference_home_fixed_or_vertical_testbed():
    text = _text()

    assert (
        "Home Fixed" in text
        or "home_fixed" in text
        or "vertical testbed" in text.lower()
        or "Vertical Testbed" in text
    ), "Boardroom should expose Home Fixed / vertical testbed context"


def test_boardroom_should_surface_machine_trace_visibility():
    text = _text()

    assert (
        "Machine Trace" in text
        or "machine_trace" in text
        or "A2A trace" in text
        or "a2a trace" in text.lower()
    ), "Boardroom should show the same compact machine trace external agents will see"
