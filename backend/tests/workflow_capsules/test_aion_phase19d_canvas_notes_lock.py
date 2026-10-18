from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def source() -> str:
    return APP.read_text(encoding="utf-8")


def phase19d_block() -> str:
    text = source()
    start = text.index("AION PATCH: Phase 19D Canonical Canvas Text Notes Lock")
    end = text.index('console.log("[AION] Phase 19D canonical canvas text notes lock installed");', start)
    return text[start:end]


def test_phase19d_has_only_canonical_note_block() -> None:
    text = source()
    assert "Phase 19D Canonical Canvas Text Notes Lock" in text
    assert "Phase 19D Canvas Notes Documentation Lock" not in text
    assert "Phase 19D Real Canvas Text Notes Lock" not in text
    assert "Phase 19D Real Draggable Sticky Note Boxes Lock" not in text
    assert "Phase 19D Visible Sticky Note Button Lock" not in text


def test_phase19d_note_click_creates_one_canvas_note_not_node() -> None:
    block = phase19d_block()
    assert "function createNote" in block
    assert "normaliseNotes(graph)" in block
    assert "notes.push(note)" in block
    assert 'type: "canvas_note"' in block
    assert "graph.nodes = Array.isArray(graph.nodes) ? graph.nodes.filter((node) => !isLegacyStickyNoteNode(node)) : []" in block


def test_phase19d_removes_legacy_sticky_nodes_and_edges() -> None:
    block = phase19d_block()
    assert "migrateAndRemoveLegacyStickyNodes" in block
    assert "isLegacyStickyNoteNode" in block
    assert "graph.nodes = graph.nodes.filter" in block
    assert "graph.edges = graph.edges.filter" in block


def test_phase19d_note_button_is_deduped() -> None:
    block = phase19d_block()
    assert "ensureButton" in block
    assert "querySelectorAll(`[${BUTTON_ATTR}='true']`).forEach" in block
    assert "if (index > 0) button.remove()" in block


def test_phase19d_notes_are_draggable() -> None:
    block = phase19d_block()
    assert "data-aion-phase19d-note-drag" in block
    assert "pointerdown" in block
    assert "pointermove" in block
    assert "pointerup" in block
    assert "is-dragging" in block


def test_phase19d_notes_are_closable() -> None:
    block = phase19d_block()
    assert "data-aion-phase19d-note-close" in block
    assert "function deleteNote" in block
    assert "graph.canvas_notes = normaliseNotes(graph).filter" in block
    assert "stopImmediatePropagation" in block


def test_phase19d_notes_are_textareas() -> None:
    block = phase19d_block()
    assert "textarea" in block
    assert "data-aion-phase19d-note-text" in block
    assert "autoGrow" in block
    assert "width: 340px !important" in block
    assert "min-height: 160px !important" in block


def test_phase19d_notes_do_not_enable_live_execution() -> None:
    block = phase19d_block()
    forbidden = [
        "fetch(",
        "sendEmail",
        "payment_created = true",
        "booking_created = true",
        "external_writes_enabled = true",
    ]
    for token in forbidden:
        assert token not in block
