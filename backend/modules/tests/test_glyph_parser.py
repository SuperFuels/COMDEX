# backend/modules/tests/test_glyph_parser.py
import pytest
from backend.modules.glyphos import glyph_parser as gp


def test_resolve_symbol_known(monkeypatch):
    """resolve_symbol should pull metadata if available."""
    monkeypatch.setattr(
        gp,  # patch the reference inside glyph_parser
        "get_instruction_metadata",
        lambda sym: {"domain": "logic", "name": "xor", "type": "operator", "tags": ["test"]},
    )
    out = gp.resolve_symbol("⊕")
    assert out["valid"] is True
    assert out["opcode"] == "logic:⊕"
    assert "xor" in out["name"]


def test_resolve_symbol_fallback():
    """Unknown glyph should fall back to glyph_index or mark invalid."""
    out = gp.resolve_symbol("🜁")  # in glyph_index
    assert out["valid"] is True
    assert out["opcode"].startswith("glyph:")

    out2 = gp.resolve_symbol("💀")  # not in index
    assert out2["valid"] is False
    assert out2["opcode"] == "glyph:💀"


def test_structuredglyph_parsing_action_and_raw(monkeypatch):
    """StructuredGlyph should keep action_raw string and canonicalize action dict."""
    # Patch translator to make it deterministic
    monkeypatch.setattr(
        "backend.modules.glyphos.codexlang_translator.parse_action_expr",
        lambda raw: {"op": "⊕", "args": ["A", "B"]},
    )
    monkeypatch.setattr(
        "backend.modules.glyphos.codexlang_translator.translate_node",
        lambda node: {"op": "logic:⊕", "args": ["A", "B"]},
    )

    sg = gp.StructuredGlyph("⟦ Logic | Test : A -> ⊕(A,B) ⟧")
    parsed = sg.to_dict()

    assert "action_raw" in parsed
    assert parsed["action_raw"] == "⊕(A,B)"
    assert isinstance(parsed["action"], dict)
    assert parsed["action"]["op"] == "logic:⊕"


def test_structuredglyph_invalid_returns_error():
    """Malformed structured glyph should not crash."""
    sg = gp.StructuredGlyph("⟦ Invalid ⟧")
    parsed = sg.to_dict()
    assert "error" in parsed
    assert parsed["error"].startswith("Invalid")


def test_glyphparser_handles_raw_glyphs():
    """GlyphParser should parse raw glyph strings into entries."""
    parser = gp.GlyphParser("🜁⚛✦")
    parsed = parser.parse()
    assert len(parsed) == 3
    assert all("symbol" in g for g in parsed)


def test_parse_glyph_and_parse_glyph_string(monkeypatch):
    """parse_glyph should map to canonical ops if available."""
    monkeypatch.setattr("backend.modules.codex.canonical_ops.CANONICAL_OPS", {"⊕": "logic:⊕"})

    single = gp.parse_glyph("⊕")
    assert single["op"] == "logic:⊕"

    string = gp.parse_glyph_string("🜁⚛")
    assert isinstance(string, list)
    assert all("symbol" in g for g in string)


def test_parse_codexlang_string_roundtrip(monkeypatch):
    """parse_codexlang_string should return first parsed entry."""
    monkeypatch.setattr(
        "backend.modules.glyphos.glyph_parser.StructuredGlyph._parse",
        lambda self: {"type": "logic", "action": {"op": "logic:⊕"}, "action_raw": "⊕(X,Y)"},
    )
    out = gp.parse_codexlang_string("⟦ Logic | Test : A -> ⊕(X,Y) ⟧")
    assert "action" in out
    assert "action_raw" in out