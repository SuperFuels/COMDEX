from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase22ab_compound_replace_add_parser_exists():
    assert "splitAionPilotCompoundAddInstruction" in TEXT
    assert "extra_add_text" in TEXT
    assert "and\\s+then|then|also" in TEXT


def test_phase22ab_add_typo_adda_is_supported():
    assert "adda?" in TEXT


def test_phase22ab_new_item_to_list_cleanup_exists():
    assert "new\\s+item" in TEXT
    assert "plan|list|section|draft|document" in TEXT


def test_phase22ab_replace_can_still_add_second_operation():
    assert "replacementOperation && replacementOperation.extra_add_text" in TEXT
    assert "Added:" in TEXT
    assert "Changed to:" in TEXT
