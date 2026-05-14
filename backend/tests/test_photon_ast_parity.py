import os, sys, importlib, types
import pytest

PHOTON_FILES = [
    "backend/tests/demo_math.photon",
    "photon_src/demo_math.photon",
]

@pytest.mark.parametrize("path", [p for p in PHOTON_FILES if os.path.exists(p)])
def test_photon_import_and_compile(path, monkeypatch):
    monkeypatch.setenv("PHOTON_IMPORT", "1")
    sys.path.insert(0, os.getcwd())
    modname = ("x." + os.path.splitext(os.path.relpath(path))[0]).replace(os.sep, ".")
    # dynamic import by file path: synthesize a module name unique per test
    import importlib.util, importlib.machinery
    from backend.modules.photonlang.runtime import photon_importer
    photon_importer.install()
    spec = importlib.util.spec_from_loader(modname, loader=None)
    # We rely on finder in meta_path to resolve .photon by name:
    m = importlib.import_module(modname)
    assert isinstance(m, types.ModuleType)
    assert hasattr(m, "__photonmap__")

def test_edgecases_async_match_fstrings(monkeypatch, tmp_path):
    code = """
async def af(): return 42
def g(x):
    match x:
        case {"k": v}: return f"v={v}"
        case _: return f"nope"
"""
    p = tmp_path/"edge.photon"
    p.write_text(code, encoding="utf-8")
    monkeypatch.setenv("PHOTON_IMPORT", "1")
    sys.path.insert(0, os.getcwd())
    from backend.modules.photonlang.runtime import photon_importer
    photon_importer.install()
    import importlib
    mod = importlib.import_module("x." + str(p.with_suffix("")).replace("/","."))
    assert hasattr(mod, "af")