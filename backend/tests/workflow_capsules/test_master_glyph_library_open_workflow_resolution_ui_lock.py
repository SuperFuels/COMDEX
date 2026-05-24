from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    return APP.read_text(encoding="utf-8")


def test_library_has_separate_stage_and_open_workflow_actions() -> None:
    text = _text()

    assert "Stage to canvas" in text
    assert "Open workflow" in text

    assert "data-aion-glyph-action=\"stage\"" in text
    assert "data-aion-glyph-action=\"open-workflow\"" in text


def test_stage_to_canvas_keeps_single_call_workflow_glyph_contract() -> None:
    text = _text()

    assert "call_workflow_glyph" in text
    assert "stageAionGlyphToCanvas" in text or "__stageAionGlyphToCanvas" in text

    # Staging should preserve glyph identity/version for runtime execution.
    assert "glyph_code" in text
    assert "glyph_version" in text
    assert "version_hash" in text
    assert "child_workflow_id" in text


def test_open_workflow_resolves_selected_glyph_not_fallback() -> None:
    text = _text()

    assert "openAionGlyphWorkflow" in text or "__openAionGlyphWorkflow" in text
    assert "resolveAionGlyphWorkflowGraph" in text or "__resolveAionGlyphWorkflowGraph" in text

    # E6 guard: opening a glyph must key from selected glyph identity.
    assert "glyph.workflow_id" in text or "glyph.workflowId" in text
    assert "glyph.glyph_code" in text or "glyph.glyphCode" in text

    # E6 guard: no fixed fallback should be the primary open target.
    bad_literals = [
        "workflow:gmail.enquiry_reply.v1",
        "universal.gmail_customer_enquiry_reply.v1",
    ]
    open_idx = max(text.find("openAionGlyphWorkflow"), text.find("__openAionGlyphWorkflow"))
    assert open_idx != -1
    block = text[open_idx:open_idx + 6000]
    for literal in bad_literals:
        assert literal not in block


def test_open_workflow_creates_distinct_tab_per_glyph_code() -> None:
    text = _text()

    assert "glyph_code" in text
    assert "workflow_id" in text
    assert "openGlyphWorkflowTab" in text or "__openGlyphWorkflowTab" in text
    assert "glyph_workflow" in text
    assert "readOnly" in text
    assert "universal" in text
