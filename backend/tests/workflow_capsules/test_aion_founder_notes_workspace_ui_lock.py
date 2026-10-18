from pathlib import Path


APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_founder_notes_is_a_first_class_sidebar_route():
    assert '{ key: "founder_notes", label: "Notes" }' in APP
    assert 'const notesIcon = tab.key === "founder_notes"' in APP
    assert 'if (state.activeTab === "founder_notes")' in APP
    assert 'return renderAionFounderNotesSurfaceV1();' in APP


def test_founder_notes_supports_capture_search_and_vault_autosave():
    assert 'aion.founderNotes.v1' in APP
    assert 'data-aion-founder-note-new="true"' in APP
    assert 'data-aion-founder-notes-search="true"' in APP
    assert 'data-aion-founder-note-field="title"' in APP
    assert 'data-aion-founder-note-field="body"' in APP
    assert 'data-aion-founder-note-delete=' in APP
    assert 'deleteAionFounderNoteV1(noteId)' in APP
    assert 'updateAionFounderNoteV1(noteId, fieldName, field.value)' in APP
    assert 'AionBusinessContainerClient?.saveFounderNotes' in APP
    assert 'localStorage?.setItem(AION_FOUNDER_NOTES_STORAGE_KEY_V1' not in APP
    assert 'Saved just now' in APP
