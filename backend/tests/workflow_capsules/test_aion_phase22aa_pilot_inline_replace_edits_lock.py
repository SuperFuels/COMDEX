from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase22aa_editor_supports_add_remove_and_change():
    assert "addOperations" in TEXT
    assert r"\b(remove|delete|take out)\b" in TEXT
    assert "extractAionPilotReplacementOperation" in TEXT
    assert "change|replace|edit|update|swap" in TEXT


def test_phase22aa_replace_tracks_old_and_new_inline():
    assert "Changed from:" in TEXT
    assert "Changed to:" in TEXT
    assert "[[AION_REMOVED_LINE]]" in TEXT
    assert "[[AION_ADDED_LINE]]" in TEXT


def test_phase22aa_replace_understands_arrow_and_plain_language():
    assert ">{2,}" in TEXT
    assert "to|with|for" in TEXT
    assert "cleanAionPilotEditPhrase" in TEXT


def test_phase22aa_replace_does_not_double_run_add_parser():
    assert "if (!replacementOperation)" in TEXT
