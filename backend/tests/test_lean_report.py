import pytest
from backend.modules.lean.lean_report import render_report

def test_render_report_html_stub():
    container = {"glyphs": [{"name": "a", "operator": "⊕", "args": ["x", "y"]}]}
    out = render_report(container, fmt="html", kind="lean.inject")
    assert "<html>" in out
    assert "Stub only" in out