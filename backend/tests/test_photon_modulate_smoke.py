# ✅ Smoke-test for PhotonLang ⧖ modulation
from backend.modules.photonlang.interpreter import run_source

def test_photon_modulate_smoke():
    result = run_source("⊕⧖")
    print("\n=== Photon ⧖ Mod Test ===")
    print(result)

    assert result["status"] == "success"
    assert result["glyph_boot"] is True