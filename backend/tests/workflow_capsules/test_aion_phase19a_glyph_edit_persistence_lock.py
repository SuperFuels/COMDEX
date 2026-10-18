from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def source() -> str:
    return APP.read_text()


def test_phase19a_glyph_edit_persistence_lock_exists() -> None:
    text = source()
    assert "AION PATCH: Phase 19A Glyph Workflow Edit Persistence Lock" in text
    assert "installAionPhase19AGlyphWorkflowEditPersistenceLock" in text
    assert "__aionPersistActiveGlyphWorkflowGraph" in text
    assert "__aionHydrateActiveGlyphWorkflowGraph" in text


def test_phase19a_persists_opened_glyph_graph_by_code() -> None:
    text = source()
    assert "__aionOpenedGlyphWorkflowGraphsByCode" in text
    assert "store[glyphCode] = graph" in text
    assert "store[glyphCode.toUpperCase()] = graph" in text
    assert "store[glyphCode.toLowerCase()] = graph" in text
    assert "window.__aionOpenedGlyphWorkflowGraph = graph" in text


def test_phase19a_keeps_main_and_glyph_workflows_separate() -> None:
    text = source()
    assert 'activeTab !== "glyph"' in text
    assert 'glyphCode.toLowerCase() === "main"' in text
    assert 'window.__aionActiveWorkflowTab = "glyph"' in text
    assert 'window.__aionActiveWorkflowTab = "main"' in text


def test_phase19a_does_not_enable_live_execution() -> None:
    text = source()
    block = text.split("AION PATCH: Phase 19A Glyph Workflow Edit Persistence Lock", 1)[1]
    block = block.split("AION PATCH: Workflow Tab Active Graph Isolation E9", 1)[0]
    forbidden = [
        "fetch(",
        "sendEmail",
        "payment_created = true",
        "booking_created = true",
        "external_writes_enabled = true",
    ]
    for token in forbidden:
        assert token not in block


def test_phase19a_captures_input_and_change_edits() -> None:
    text = source()
    assert 'document.addEventListener("input"' in text
    assert 'document.addEventListener("change"' in text
    assert 'persistActiveGlyphWorkflowGraph("input_edit")' in text
    assert 'persistActiveGlyphWorkflowGraph("change_edit")' in text
