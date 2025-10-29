"""
Photon ↔ Symatics Integration Test
──────────────────────────────────────────────
Verifies that ⊕, ↔, and μ operators execute successfully
through the Symatics Lightwave Dispatcher (and symbolic fallback).
"""

import json
from pathlib import Path
from backend.modules.photon.photon_executor import execute_photon_capsule


def test_lightwave_execution():
    """Run .phn capsule through Lightwave engine."""
    path = Path(__file__).parent / "test_capsule_integration.phn"
    result = execute_photon_capsule(path)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    assert result["status"] == "success"
    assert result["engine"] == "symatics"
    assert any("⊕" in str(r) for r in result["execution"])
    assert any("↔" in str(r) for r in result["execution"])
    assert any("μ" in str(r) for r in result["execution"])


def test_symbolic_fallback():
    """Run capsule dict using symbolic Symatics engine."""
    capsule_dict = {
        "name": "Symbolic_Test",
        "engine": "symbolic",
        "body": [
            {"op": "⊕", "id": "combine", "block": ["ψ1", "ψ2"]},
            {"op": "↔", "id": "entangle", "block": ["ψ3", "ψ4"]},
            {"op": "μ", "id": "measure", "block": ["ψ5"]},
        ],
    }

    result = execute_photon_capsule(capsule_dict)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    assert result["status"] == "success"
    assert "symatics" in result["engine"]
    assert all(op in str(result["execution"]) for op in ["⊕", "↔", "μ"])