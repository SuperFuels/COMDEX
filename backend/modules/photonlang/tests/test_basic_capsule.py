import pytest
from backend.modules.photonlang.interpreter import run_source

# ───────────────────────────────────────────────
#  PhotonLang Integration Test • v0.1
# ───────────────────────────────────────────────

def test_basic_photon_capsule_execution():
    source = """
    import SQI
    from .atom_sheet 42 import SymPy
    from (wormhole: quantum://glyphnet/channel_7) import QuantumFieldCanvas

    ⊕μ↔  # initialize symbolic-quantum interface

    sheet = AtomSheet(id="ψ_314", mode="symbolic")
    sheet.seed("photon_resonance_pattern", coherence=0.97)

    qfield = QuantumFieldCanvas(dim=4)
    qfield.inject(sheet)
    qfield.resonate("⊕μ↔", intensity=7.2)

    send sheet through wormhole "glyphnet://aion-reflection"
    save as "resonance_test.ptn"
    """

    result = run_source(source)
    assert isinstance(result, dict)
    assert result.get("status") == "success"
    assert "glyph_boot" in result
    assert "env_keys" in result

    print("\n\n🔹 PhotonLang Execution Result 🔹")
    for k, v in result.items():
        print(f"{k}: {v}")

    # Sanity checks
    assert any("QuantumFieldCanvas" in k or "AtomSheet" in k for k in result["env_keys"])
    assert result["glyph_boot"] is True