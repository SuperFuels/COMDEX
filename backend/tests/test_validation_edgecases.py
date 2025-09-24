# backend/tests/test_validation_edgecases.py
import json
import pytest

from backend.modules.lean import lean_audit, lean_report


def test_empty_validation_errors_json_and_md(tmp_path):
    container = {"id": "c1", "type": "dc", "glyphs": []}
    md = lean_report.render_report(container, fmt="md", validation_errors=[])
    assert "Validation Errors" in md
    assert "None ✅" in md

    j = json.loads(lean_report.render_report(container, fmt="json", validation_errors=[]))
    assert j["validation_errors"] == []


def test_string_validation_errors_are_normalized():
    errors = ["Broken axiom"]
    evt = lean_audit.build_inject_event(
        container_path="?", container_id="c1", lean_path="f.lean",
        num_items=1, previews=[], validation_errors=errors
    )
    v = evt["validation_errors"]
    assert isinstance(v, list)
    assert v[0]["code"] == "E000"
    assert "Broken axiom" in v[0]["message"]


def test_mixed_validation_errors_are_normalized():
    errors = ["Broken axiom", {"code": "E999", "message": "Custom failure"}]
    evt = lean_audit.build_inject_event(
        container_path="?", container_id="c1", lean_path="f.lean",
        num_items=1, previews=[], validation_errors=errors
    )
    v = evt["validation_errors"]
    assert any(e["code"] == "E000" for e in v)
    assert any(e["code"] == "E999" for e in v)


def test_report_surfaces_validation_errors_top_level():
    errors = [{"code": "E123", "message": "Example error"}]
    container = {"id": "c1", "type": "dc", "glyphs": []}
    j = json.loads(
        lean_report.render_report(container, fmt="json", validation_errors=errors)
    )
    assert "validation_errors" in j
    assert j["validation_errors"][0]["code"] == "E123"