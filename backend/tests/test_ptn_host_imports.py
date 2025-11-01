import os
import sys
import importlib
from pathlib import Path
import textwrap

import pytest

# --- imports from your codebase ---
# spec/validator/runner we added earlier
from backend.modules.photon.ptn_spec import normalize_host_import
from backend.modules.photon.ptn_validator import validate_page
from backend.modules.photon.ptn_runner import (
    _bind_python_host_modules,
    _ensure_photon_importer,
)
# glyph compressor for making a .photon on-the-fly
from backend.modules.photonlang.adapters.python_tokens import compress_text_py


# ------------------------ helpers ------------------------

def _write_photon(tmp_path: Path, mod_name: str, py_src: str, ext: str = ".photon") -> Path:
    """Write a glyph-compressed Python module as .photon/.pthon."""
    mod_path = tmp_path / f"{mod_name}{ext}"
    mod_path.write_text(compress_text_py(py_src), encoding="utf-8")
    return mod_path


# ------------------------ unit tests: normalize ------------------------

def test_normalize_host_import_string_and_object_forms():
    s_ok = "host:python:photon_lib.demo"
    d_ok = {"host": "python", "module": "a.b.c", "as": "abc"}

    n1 = normalize_host_import(s_ok)
    n2 = normalize_host_import(d_ok)

    assert n1 == {"host": "python", "module": "photon_lib.demo"}
    assert n2 == {"host": "python", "module": "a.b.c", "as": "abc"}

    # bad inputs
    assert normalize_host_import("host:py:bad") is None
    assert normalize_host_import({"host": "python"}) is None
    assert normalize_host_import(42) is None


def test_validator_attaches_normalized_host_imports():
    page = {
        "name": "QFC_Demo",
        "imports": [
            "host:python:photon_lib.demo",
            {"host": "python", "module": "aion.sqi.tools", "as": "sqi"},
        ],
        "body": "⊕ … ↔ … ∇ …",
    }
    out = validate_page(page)
    assert "_host_imports" in out
    assert out["_host_imports"] == [
        {"host": "python", "module": "photon_lib.demo"},
        {"host": "python", "module": "aion.sqi.tools", "as": "sqi"},
    ]


# ------------------------ integration: import .photon/.pthon ------------------------

@pytest.mark.parametrize("ext", [".photon", ".pthon"])
def test_bind_and_call_photon_module(tmp_path: Path, ext: str, monkeypatch):
    # Create a glyph-compressed module with a simple function
    py_src = textwrap.dedent(
        """
        def ping():
            return "pong"
        """
    )
    _write_photon(tmp_path, "demo", py_src, ext=ext)

    # Ensure the temporary directory is importable
    sys.path.insert(0, str(tmp_path))
    importlib.invalidate_caches()

    # Make sure our importer is active
    _ensure_photon_importer()

    # Bind via the runner helper
    ctx = {}
    host_imports = [{"host": "python", "module": "demo"}]
    _bind_python_host_modules(host_imports, ctx)

    # Assertions: module is available directly and in ctx['python']
    assert "demo" in ctx
    assert "python" in ctx and "demo" in ctx["python"]
    assert ctx["demo"].ping() == "pong"


def test_alias_binding_with_as(tmp_path: Path):
    py_src = "def f():\n    return 314\n"
    _write_photon(tmp_path, "demo2", py_src, ext=".photon")

    sys.path.insert(0, str(tmp_path))
    importlib.invalidate_caches()
    _ensure_photon_importer()

    ctx = {}
    host_imports = [{"host": "python", "module": "demo2", "as": "m"}]
    _bind_python_host_modules(host_imports, ctx)

    assert "m" in ctx
    assert ctx["m"].f() == 314