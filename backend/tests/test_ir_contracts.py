from backend.ir.registry import build_maps

def test_ir_bijections():
    maps = build_maps()
    # Operators bijective
    assert len(maps.op_to_js) == len(maps.js_to_op)
    for g, js in maps.op_to_js.items():
        assert maps.js_to_op[js] == g
    # Punctuation bijective
    assert len(maps.punct_to_js) == len(maps.js_to_punct)
    for g, js in maps.punct_to_js.items():
        assert maps.js_to_punct[js] == g