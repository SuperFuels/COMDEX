# File: backend/tests/test_axioms_consistency.py
"""
Axioms Consistency Tests
------------------------
Cross-checks:
  * LAW_REGISTRY in Python
  * Lean axioms in symatics_axioms.lean
Ensures naming and coverage are consistent across sources.
"""

import pytest
import pathlib

from backend.symatics.symatics_rulebook import LAW_REGISTRY
from backend.modules.lean.convert_lean_to_codexlang import convert_lean_to_codexlang


LEAN_FILE = "backend/modules/lean/symatics_axioms.lean"


def test_python_and_lean_axioms_alignment():
    """Compare LAW_REGISTRY['⋈'] entries with Lean axioms by name."""
    lean_results = convert_lean_to_codexlang(LEAN_FILE)
    lean_names = {decl["name"] for decl in lean_results["parsed_declarations"]}

    python_names = {law.__name__ for law in LAW_REGISTRY.get("⋈", [])}

    # Every Lean axiom should have a Python counterpart
    missing_in_python = lean_names - python_names
    # Every Python law should be declared in Lean
    missing_in_lean = python_names - lean_names

    if missing_in_python or missing_in_lean:
        pytest.fail(
            f"Inconsistency detected:\n"
            f"  Missing in Python: {sorted(missing_in_python)}\n"
            f"  Missing in Lean:   {sorted(missing_in_lean)}"
        )


def test_all_laws_callable():
    """Ensure all laws in LAW_REGISTRY['⋈'] are callable functions."""
    for law in LAW_REGISTRY.get("⋈", []):
        assert callable(law), f"{law} is not callable"


def test_axioms_file_exists():
    """Guardrail: ensure Lean axioms file is present."""
    path = pathlib.Path(LEAN_FILE)
    assert path.exists(), f"Lean axioms file missing: {LEAN_FILE}"