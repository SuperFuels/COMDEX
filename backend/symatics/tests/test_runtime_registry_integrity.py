"""
Runtime Registry Integrity Test (v0.4.5)
---------------------------------------
Verifies that all entries in RUNTIME_LAW_REGISTRY are complete,
valid, and callable. Ensures versioned metadata integrity across
Tessaris Runtime Law Validation System.
"""

import inspect
from backend.symatics.core.validators import law_check


def test_registry_structure_valid():
    """Ensure registry exists and contains valid entries."""
    registry = getattr(law_check, "RUNTIME_LAW_REGISTRY", None)
    assert registry is not None and isinstance(registry, dict)
    assert len(registry) >= 5, "Registry too small - missing runtime law entries."

    for name, meta in registry.items():
        assert isinstance(meta, dict), f"{name} entry must be dict"
        assert "symbol" in meta, f"{name} missing 'symbol'"
        assert "description" in meta, f"{name} missing 'description'"
        assert "version" in meta, f"{name} missing 'version'"
        assert isinstance(meta["symbol"], str)
        assert isinstance(meta["description"], str)
        assert isinstance(meta["version"], str)
        assert "function" in meta, f"{name} missing function reference"
        func = meta["function"]
        assert callable(func), f"{name} function is not callable"


def test_list_runtime_laws_summary():
    """Check that list_runtime_laws() reports proper metadata."""
    summary = law_check.list_runtime_laws()
    assert isinstance(summary, dict)
    assert all("symbol" in v and "version" in v for v in summary.values())

    # Verbose mode must include function names
    verbose = law_check.list_runtime_laws(verbose=True)
    for info in verbose.values():
        assert "function" in info and isinstance(info["function"], str)


def test_registry_function_signatures_consistent():
    """Verify all registered functions accept (expr, ctx) arguments."""
    for name, meta in law_check.RUNTIME_LAW_REGISTRY.items():
        func = meta.get("function")
        if not callable(func):
            continue
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        assert params[0] in {"expr", "a", "state"}, f"{name} first arg should be expr-like"
        # ctx may be optional
        assert "ctx" in params or any(p for p in params if "ctx" in p), f"{name} should accept ctx"