# ============================================================
# 🧩 test_wiki_linter.py
# ============================================================

import tempfile
from pathlib import Path
from backend.modules.wiki_capsules.validation_maintenance.wiki_linter import (
    lint_capsule,
    lint_directory,
)

# ─────────────────────────────────────────────────────────────
# Test: Single file lint - Missing metadata block
# ─────────────────────────────────────────────────────────────
def test_linter_detects_missing_meta(tmp_path: Path):
    bad_file = tmp_path / "broken.wiki.phn"
    bad_file.write_text("lemma: test\n", encoding="utf-8")
    result = lint_capsule(bad_file)

    assert not result["valid"]
    assert "Missing 'meta:' header block." in result["errors"]


# ─────────────────────────────────────────────────────────────
# Test: Valid file passes lint cleanly
# ─────────────────────────────────────────────────────────────
def test_linter_valid_file(tmp_path: Path):
    good_file = tmp_path / "good.wiki.phn"
    good_file.write_text(
        "meta:\n  version: 1.0\n  signed_by: Tessaris-Core\n  checksum: abc\n"
        "lemma: Apple\n"
        "definitions: [fruit]\n"
        "examples: [example]\n",
        encoding="utf-8",
    )
    result = lint_capsule(good_file)
    assert result["valid"]
    assert result["status"] == "ok"


# ─────────────────────────────────────────────────────────────
# Test: Directory lint collects all valid capsules
# ─────────────────────────────────────────────────────────────
def test_lint_directory_collects_all(tmp_path: Path):
    f1 = tmp_path / "A.wiki.phn"
    f2 = tmp_path / "B.wiki.phn"

    f1.write_text("meta:\n  version: 1.0\n  signed_by: Tessaris-Core\n", encoding="utf-8")
    f2.write_text("meta:\n  version: 1.0\n  signed_by: Tessaris-Core\n", encoding="utf-8")

    results = lint_directory(tmp_path)
    assert isinstance(results, list)
    assert len(results) == 2
    assert all("status" in r for r in results)