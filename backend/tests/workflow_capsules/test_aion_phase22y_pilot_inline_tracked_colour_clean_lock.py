from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase22y_added_and_removed_lines_have_internal_markers():
    assert "[[AION_ADDED_LINE]]" in TEXT
    assert "[[AION_REMOVED_LINE]]" in TEXT


def test_phase22y_renderer_colours_added_and_removed_lines():
    assert "aion-pilot-tracked-line-added" in TEXT
    assert "aion-pilot-tracked-line-removed" in TEXT
    assert "#087f3f" in TEXT
    assert "#1d4ed8" in TEXT
    assert "line-through" in TEXT


def test_phase22y_clean_me_button_exists_and_finalises_tracking():
    assert "Clean Me" in TEXT
    assert "cleanAionPilotTrackedDraftOutput" in TEXT
    assert "cleanAionPilotTrackedDraftText" in TEXT
    assert "cleaned_tracked_changes" in TEXT


def test_phase22y_cleaning_keeps_additions_and_removes_deletions():
    assert 'filter((line) => !line.includes("[[AION_REMOVED_LINE]]"))' in TEXT
    assert 'replace(/\\[\\[AION_ADDED_LINE\\]\\]/g, "")' in TEXT
