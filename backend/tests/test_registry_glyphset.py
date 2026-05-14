from backend.modules.photonlang.registry import load_registry
import json, pathlib

def test_glyphs_cover_token_map():
    reg = load_registry()
    map_path = pathlib.Path("backend/modules/photonlang_js/javascript_token_map.json")
    t = json.loads(map_path.read_text(encoding="utf-8"))
    ops = set(t["operators"].values())
    # Ensure every glyph we emit for JS is known to the registry
    missing = [g for g in ops if g not in reg]
    assert not missing, f"glyphs missing from registry: {missing}"