from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def test_desktop_canvas_has_gmail_visual_mapping_lock() -> None:
    text = APP_JS.read_text()

    assert "function getWorkflowArchitectNodeVisualKind" in text

    for action in [
        "gmail.watch_emails",
        "gmail.search_emails",
        "gmail.get_email",
        "gmail.list_attachments",
        "gmail.create_draft",
        "gmail.send_email",
        "gmail.reply_email",
        "gmail.send_draft",
        "gmail.delete_email",
        "gmail.api_call",
    ]:
        assert action in text

    assert "Future-only" in text
    assert "Approval required" in text
    assert "Safe read" in text
    assert "Gmail Locked" in text
    assert "Gmail Draft" in text
    assert "Gmail Read" in text
