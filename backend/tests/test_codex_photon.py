import json
from pathlib import Path

import pytest
from backend.modules.codex.codex_executor import execute_photon_capsule

# ✅ Sample Photon capsule dict with glyphs
SAMPLE_CAPSULE = {
    "name": "test_capsule",
    "glyphs": [
        {"name": "superpose", "logic": "a ⊕ b", "operator": "⊕", "args": ["a", "b"]},
        {"name": "measure", "logic": "μ(x)", "operator": "μ", "args": ["x"]},
    ],
}


def test_photon_capsule_dict_roundtrip(tmp_path):
    result = execute_photon_capsule(SAMPLE_CAPSULE, context={"capsule_id": "test_capsule"})
    assert result["status"] == "success"
    assert "scroll" in result
    assert "execution" in result
    assert isinstance(result["glyphs"], list)
    # ✅ Ensure at least one operator is ⊕ or μ
    assert any(g["operator"] in {"⊕", "μ"} for g in result["glyphs"])


def test_photon_capsule_file_roundtrip(tmp_path):
    capsule_path = tmp_path / "capsule.phn"
    capsule_path.write_text(json.dumps(SAMPLE_CAPSULE, indent=2))

    result = execute_photon_capsule(str(capsule_path), context={"capsule_id": "test_capsule"})
    assert result["status"] == "success"
    assert "scroll" in result
    assert "execution" in result
    assert isinstance(result["glyphs"], list)
    assert any(g["operator"] in {"⊕", "μ"} for g in result["glyphs"])