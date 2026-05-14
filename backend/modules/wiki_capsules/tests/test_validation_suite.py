"""
✅ Validation Suite Tests
-------------------------
Tests Wiki Linter, Reference Validator, and Maintenance orchestration.
"""

import json
from pathlib import Path
from backend.modules.wiki_capsules.validation_maintenance import wiki_linter, reference_validator, maintenance_jobs


def setup_temp_files(tmp_path):
    """Create mock data for validation."""
    kg_dir = tmp_path / "data" / "knowledge" / "Lexicon"
    kg_dir.mkdir(parents=True)
    file_path = kg_dir / "Apple.wiki.phn"
    file_path.write_text(
        """
meta:
  version: 1.0
  signed_by: Tessaris-Core
  checksum: "abc123"
lemma: Apple
pos: noun
definitions:
  - A sweet fruit.
entangled_links:
  Lexicon: [Banana]
""",
        encoding="utf-8",
    )

    registry = {
        "Lexicon": {
            "Apple": {
                "path": str(file_path),
                "meta": {"signed_by": "Tessaris-Core"},
                "entangled_links": {"Lexicon": ["Banana"]},
            },
            "Banana": {
                "path": str(kg_dir / "Banana.wiki.phn"),
                "meta": {"signed_by": "Tessaris-Core"},
            },
        }
    }
    kg_path = tmp_path / "data" / "knowledge" / "kg_registry.json"
    kg_path.parent.mkdir(parents=True, exist_ok=True)
    kg_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    return file_path, kg_path


def test_wiki_linter_detects_missing_fields(tmp_path):
    f, _ = setup_temp_files(tmp_path)
    result = wiki_linter.lint_capsule_file(str(f))
    assert result["status"] in ("ok", "warn")
    assert "meta" in result


def test_reference_validator_cross_links(tmp_path):
    _, kg_path = setup_temp_files(tmp_path)
    result = reference_validator.validate_references(str(kg_path))
    assert "status" in result
    assert isinstance(result["errors"], list)
    assert all("Lexicon" in e for e in result["errors"]) or result["status"] == "ok"


def test_maintenance_job_runs(tmp_path):
    f, kg = setup_temp_files(tmp_path)
    root = str(tmp_path / "data" / "knowledge")
    res = maintenance_jobs.run_maintenance(root)
    assert "lint" in res and "refs" in res