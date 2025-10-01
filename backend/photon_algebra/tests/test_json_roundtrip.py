import pytest
from backend.photon_algebra.core import superpose, entangle, negate, EMPTY
from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.photon_adapter import to_json, from_json

@pytest.mark.parametrize("expr", [
    "a",
    EMPTY,
    superpose("a", "b", "c"),
    entangle("a", "b"),
    negate("a"),
    {"op": "⊗", "states": ["a", "b", "c"]},
])
def test_json_roundtrip(expr):
    js = to_json(expr)
    back = from_json(js)
    assert normalize(back) == normalize(expr)