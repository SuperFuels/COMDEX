import json
from backend.photon_algebra.rewriter import normalize
from backend.tools.photon_pp import pp

def test_pp_smoke_and_json_roundtrip():
    expr = {
        "op":"⊕",
        "states":[
            {"op":"⊗","states":["a", {"op":"⊕","states":["b","c"]}]},
            {"op":"¬","state":{"op":"★","state":"d"}},
            {"op":"↔","states":["x","y"]},
            {"op":"∅"}
        ]
    }
    # pretty-printer shouldn't crash
    _ = pp(expr)

    # JSON round-trip (structure preserved)
    dumped = json.dumps(expr, ensure_ascii=False)
    loaded = json.loads(dumped)
    assert loaded == expr

    # Normalize is idempotent post round-trip
    n1 = normalize(expr)
    n2 = normalize(json.loads(json.dumps(expr, ensure_ascii=False)))
    assert n1 == n2