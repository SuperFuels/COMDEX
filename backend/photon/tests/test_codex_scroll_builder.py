# 📄 backend/tests/test_codex_scroll_builder.py

import pytest
from backend.modules.codex.codex_scroll_builder import build_scroll_as_photon_ast


def test_build_scroll_as_photon_ast_simple():
    # A simple CodexLang expression
    code = "greater_than(x, y)"
    photon_ast = build_scroll_as_photon_ast(code)

    assert isinstance(photon_ast, dict)
    assert photon_ast.get("ast_type") == "photon_ast"
    assert photon_ast.get("origin") == "codex"
    assert photon_ast.get("root") == "greater_than"


def test_build_scroll_as_photon_ast_invalid():
    # Invalid CodexLang should return error dict
    code = "INVALID_CODE("
    photon_ast = build_scroll_as_photon_ast(code)

    assert "error" in photon_ast.get("op", "error")
    assert "detail" in photon_ast