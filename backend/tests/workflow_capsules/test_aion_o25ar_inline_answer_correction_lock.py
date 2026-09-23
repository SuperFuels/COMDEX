from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def renderer_block() -> str:
    text = read_app()
    start = text.index(
        "function renderAionO25ETerminalOnlyVoiceConversation"
    )
    end = text.index(
        "function syncAionO25ETerminalOnlyVoiceConversation",
        start,
    )
    return text[start:end]


def o25aj_block() -> str:
    text = read_app()
    start = text.index(
        "BEGIN AION O25AJ REAL VOICE TURN STATE BRIDGE LOCK"
    )
    return text[start:]


def test_o25ar_user_rows_show_edit_answer_control():
    block = renderer_block()
    assert "data-aion-o25e-edit-answer" in block
    assert "Edit answer" in block
    assert "Corrected" in block


def test_o25ar_inline_editor_has_save_and_cancel():
    text = read_app()
    assert "beginO25EInlineAnswerEdit" in text
    assert 'form.setAttribute("data-aion-o25e-edit-form", "true")' in text
    assert "Save correction" in text
    assert "data-aion-o25e-cancel-edit" in text


def test_o25ar_correction_updates_mapped_foundation_field():
    block = o25aj_block()
    assert "window.editAionO25EUserAnswer" in block
    assert "packet.foundation_draft[mappedField] = clean" in block
    assert "draft_updated: Boolean(mappedField)" in block


def test_o25ar_preserves_correction_provenance():
    block = o25aj_block()
    assert "original_text" in block
    assert "correction_history" in block
    assert "human_inline_correction" in block
    assert "previous_text" in block
    assert "corrected_text" in block


def test_o25ar_user_row_receives_controller_field_mapping():
    block = o25aj_block()
    assert "packet?.last_turn?.mapped_field" in block
    assert "userRow.mapped_field = mappedField" in block


def test_o25ar_user_is_told_answers_are_editable():
    block = renderer_block()
    assert (
        "You can edit any answer before finalising "
        "your Business Foundation."
    ) in block
