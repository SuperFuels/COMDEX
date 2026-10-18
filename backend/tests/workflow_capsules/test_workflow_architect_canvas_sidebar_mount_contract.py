from __future__ import annotations

from pathlib import Path


def _candidate_files() -> list[Path]:
    roots = [Path("frontend"), Path("Glyph_Net_Browser")]
    out: list[Path] = []

    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix not in {".tsx", ".jsx"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            if "workflow-architect-sidebar-mount" in text:
                out.append(path)

    return out


def test_workflow_architect_panel_is_mounted_in_a_canvas_surface() -> None:
    files = _candidate_files()

    assert files, "WorkflowArchitectReviewPanel is not mounted in any frontend canvas/sidebar surface."

    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)

    assert "WorkflowArchitectReviewPanel" in combined
    assert "workflow-architect-sidebar-mount" in combined


def test_workflow_architect_sidebar_mount_uses_safe_review_callback_only() -> None:
    files = _candidate_files()
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in files)

    assert "onvalidreview" in combined
    assert "valid review ready for canvas load" in combined

    forbidden = [
        "users.messages.send",
        "gmail_live_send",
        "send_message(",
        "live_execute",
    ]

    for token in forbidden:
        assert token not in combined
