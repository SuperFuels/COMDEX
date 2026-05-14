import pytest
from backend.modules.lean.lean_inject_utils import normalize_logic_entry
from backend.modules.lean.lean_injector import inject_theorems_into_container


def test_normalize_logic_entry_minimal_decl(tmp_path):
    # Minimal fake decl with only a name
    decl = {"name": "trivial"}
    logic_entry = normalize_logic_entry(decl, str(tmp_path / "theorem.lean"))

    # Ensure required keys are present
    required_keys = {
        "name",
        "symbol",
        "logic",
        "logic_raw",
        "codexlang",
        "glyph_tree",
        "source",
        "body",
    }
    assert required_keys.issubset(set(logic_entry.keys()))

    # Fallbacks
    assert logic_entry["logic_raw"] == "True"
    assert logic_entry["logic"] == "True"
    assert logic_entry["codexlang"]["logic"] == "True"
    assert logic_entry["codexlang"]["normalized"] == "True"
    assert logic_entry["codexlang"]["explanation"]


def test_normalize_logic_entry_with_codexlang(tmp_path):
    # Decl with codexlang already defined
    decl = {
        "name": "lemma1",
        "codexlang": {"logic": "A -> B", "normalized": "A -> B"},
        "glyph_tree": {"type": "LogicGlyph"},
        "body": "proof goes here",
    }
    logic_entry = normalize_logic_entry(decl, str(tmp_path / "lemma.lean"))

    assert logic_entry["name"] == "lemma1"
    assert logic_entry["logic_raw"] == "A -> B"
    assert logic_entry["logic"]  # should be simplified form
    assert isinstance(logic_entry["codexlang"], dict)
    assert logic_entry["glyph_tree"]["type"] == "LogicGlyph"
    assert logic_entry["body"] == "proof goes here"


def test_normalize_logic_entry_with_codexlang_string(tmp_path):
    # Decl with only codexlang_string legacy field
    decl = {"name": "lemma2", "codexlang_string": "C ∧ D"}
    logic_entry = normalize_logic_entry(decl, str(tmp_path / "legacy.lean"))

    assert logic_entry["logic_raw"] == "C ∧ D"
    assert logic_entry["codexlang"]["logic"] == "C ∧ D"
    assert logic_entry["codexlang"]["legacy"] == "C ∧ D"


def test_normalize_logic_entry_base_keys(tmp_path):
    decl = {"name": "trivial"}
    logic_entry = normalize_logic_entry(decl, str(tmp_path / "theorem.lean"))

    required_keys = {
        "name",
        "symbol",
        "logic",
        "logic_raw",
        "codexlang",
        "glyph_tree",
        "source",
        "body",
    }
    assert required_keys.issubset(logic_entry.keys())

    # Injector-only keys should NOT exist here
    for k in ["leanProof", "symbolicProof", "proofExplanation", "replay_tags"]:
        assert k not in logic_entry


def test_injector_adds_extras(tmp_path):
    lean_file = tmp_path / "lemma.lean"
    lean_file.write_text("theorem trivial : True := trivial")

    # Minimal container
    container = {"type": "dc", "glyphs": [], "symbolic_logic": [], "thought_tree": []}
    updated = inject_theorems_into_container(container, str(lean_file))

    assert updated["symbolic_logic"], "No logic entries injected"
    logic_entry = updated["symbolic_logic"][0]

    # Injector adds extras
    assert "leanProof" in logic_entry
    assert "symbolicProof" in logic_entry
    assert "proofExplanation" in logic_entry
    assert "replay_tags" in logic_entry

    # Base keys still present
    for k in ["name", "symbol", "logic", "logic_raw", "codexlang", "glyph_tree", "source", "body"]:
        assert k in logic_entry