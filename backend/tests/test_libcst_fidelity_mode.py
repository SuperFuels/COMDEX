import os
import pytest

ENABLE = os.getenv("PHOTON_FIDELITY_LIBCST", "0") == "1"

try:
    from backend.modules.photonlang_js.fidelity.libcst_mode import expand_with_libcst
    _IMPORT_ERR = None
except Exception as e:
    expand_with_libcst = None  # type: ignore
    _IMPORT_ERR = e

pytestmark = pytest.mark.skipif(
    not ENABLE or expand_with_libcst is None,
    reason=("libcst optional path" if not ENABLE else f"libcst import failed: {_IMPORT_ERR}")
)

def test_libcst_mode_runs():
    # Keep input valid Python so libcst parses it; your transformer can inject the ops header.
    src = "def f(x):\n    return x + 1\n"
    out = expand_with_libcst(src).text  # type: ignore[union-attr]
    assert "__OPS__" in out