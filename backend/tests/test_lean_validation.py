import pytest
from backend.modules.lean.lean_utils import validate_logic_trees


def _make_container(entries):
    return {
        "type": "dc",
        "id": "test-container",
        "symbolic_logic": entries,
    }


def test_unique_names_violation():
    c = _make_container([
        {"name": "T1", "symbol": "⊢", "logic": "A → B"},
        {"name": "T1", "symbol": "⊢", "logic": "B → C"},
    ])
    errs = validate_logic_trees(c)
    assert any("Duplicate entry name" in e for e in errs)


def test_duplicate_signature_violation():
    c = _make_container([
        {"name": "T1", "symbol": "⊢", "logic": "A → B"},
        {"name": "T1", "symbol": "⊢", "logic": "A → B"},
    ])
    errs = validate_logic_trees(c)
    assert any("Duplicate signature" in e for e in errs)


def test_unresolved_dependency():
    c = _make_container([
        {"name": "T1", "symbol": "⊢", "logic": "A → B", "depends_on": ["Missing"]},
    ])
    errs = validate_logic_trees(c)
    assert any("Unresolved dependency" in e for e in errs)


def test_empty_logic_string():
    c = _make_container([
        {"name": "T1", "symbol": "⊢", "logic": ""},
    ])
    errs = validate_logic_trees(c)
    assert any("missing/empty logic" in e for e in errs)


def test_malformed_logic_string():
    c = _make_container([
        {"name": "T1", "symbol": "⊢", "logic": "nonsense"},
    ])
    errs = validate_logic_trees(c)
    assert any("looks malformed" in e for e in errs)


def test_invalid_symbol():
    c = _make_container([
        {"name": "T1", "symbol": "⟦ ? ⟧", "logic": "A → B"},
    ])
    errs = validate_logic_trees(c)
    assert any("invalid or missing symbol" in e for e in errs)


def test_self_circular_dependency():
    c = _make_container([
        {"name": "T1", "symbol": "⊢", "logic": "A → A", "depends_on": ["T1"]},
    ])
    errs = validate_logic_trees(c)
    assert any("Circular dependency" in e for e in errs)


def test_valid_entries_pass():
    c = _make_container([
        {"name": "T1", "symbol": "⊢", "logic": "A → B"},
        {"name": "T2", "symbol": "⊢", "logic": "B → C", "depends_on": ["T1"]},
    ])
    errs = validate_logic_trees(c)
    assert errs == []