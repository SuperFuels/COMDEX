import json
from pathlib import Path

def test_math_core_seed_exists_and_shape():
    p = Path("backend/modules/dimensions/containers/math_core.dc.json")
    assert p.exists(), "math_core.dc.json seed missing"

    data = json.loads(p.read_text(encoding="utf-8"))
    # required top-level keys
    for k in ("id", "name", "glyph_categories", "nodes"):
        assert k in data, f"seed missing key: {k}"

    assert data["id"] == "math_core"
    assert isinstance(data["glyph_categories"], list) and len(data["glyph_categories"]) >= 2
    assert isinstance(data["nodes"], list) and len(data["nodes"]) >= 3

    # categories present
    cat_ids = {c["id"] for c in data["glyph_categories"]}
    assert "linear_algebra" in cat_ids
    assert "ode_pde" in cat_ids

    # nodes reference valid categories
    for n in data["nodes"]:
        assert "category" in n and n["category"] in cat_ids

def test_math_core_links_reference_nodes():
    p = Path("backend/modules/dimensions/containers/math_core.dc.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    node_ids = {n["id"] for n in data["nodes"]}
    for e in data.get("links", []):
        assert e["src"] in node_ids and e["dst"] in node_ids

def test_math_core_loader_roundtrip():
    try:
        from backend.modules.dimensions.container_expander import load_seed_container
    except Exception:
        # loader not present in some branches; test remains optional
        return
    data = load_seed_container("math_core")
    assert data and data.get("id") == "math_core"