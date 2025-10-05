from backend.photon_algebra.photon_adapter import normalize_expr

def test_distribution_count():
    expr = {"op": "⊗", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]}
    norm, meta = normalize_expr(expr)
    assert meta["distributions"] >= 1
    assert meta["invariants"]["no_plus_under_times"]
    
def test_absorption_count():
    expr = {"op": "⊕", "states": ["a", {"op": "⊗", "states": ["a", "b"]}]}
    norm, meta = normalize_expr(expr)
    assert meta["absorptions"] >= 1
    assert norm == "a" or norm == {"op": "⊕", "states": ["a"]}

def test_idempotence_count():
    expr = {"op": "⊗", "states": ["a", "a"]}
    norm, meta = normalize_expr(expr)
    assert meta["idempotence"] >= 1
    assert norm == "a"