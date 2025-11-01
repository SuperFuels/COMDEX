# backend/tests/test_photon_importer_mvp.py
import importlib
import sys

def test_demo_math_photon_import():
    # Enable .photon imports
    from backend.modules.photonlang.importer import install
    install()

    # demo_math.photon lives in backend/tests/
    tests_dir = "/workspaces/COMDEX/backend/tests"
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)

    mod = importlib.import_module("demo_math")  # loads demo_math.photon transparently

    # basic module surface checks
    assert hasattr(mod, "add_and_measure")
    assert hasattr(mod, "__OPS__")
    assert "⊕" in mod.__OPS__ and "μ" in mod.__OPS__

    # call the function and validate shape
    out = mod.add_and_measure(2, 3)
    assert isinstance(out, dict)
    assert "z" in out and "m" in out
    # minimal sanity: returned objects should be printable
    assert str(out["z"])
    assert str(out["m"])

    # second import (cache path) should still work
    mod2 = importlib.import_module("demo_math")
    assert mod2 is mod