import json
import pytest
from pathlib import Path
from backend.modules.holograms.knowledge_pack_generator import generate_knowledge_pack

@pytest.fixture
def sample_logic_tree():
    return [
        {"symbol": "⬁", "label": "Rewrite Self"},
        {"symbol": "↔", "label": "Entangle Logic"},
        {"symbol": "🧠", "label": "Cognitive Anchor"},
        {"symbol": "⧖", "label": "Collapse Event"},
    ]

def test_generate_knowledge_pack_structure(sample_logic_tree, tmp_path):
    container_id = "aion/seed/container-9"
    ghx_bundle = generate_knowledge_pack(sample_logic_tree, container_id)

    # ✅ Check main structure
    assert isinstance(ghx_bundle, dict)
    assert ghx_bundle.get("container_id") == container_id
    assert "nodes" in ghx_bundle
    assert isinstance(ghx_bundle["nodes"], list)
    assert len(ghx_bundle["nodes"]) == len(sample_logic_tree)

    # ✅ Check node structure
    for g in ghx_bundle["nodes"]:
        assert "symbol" in g
        assert "label" in g
        assert "glyph_id" in g
        assert "light_intensity" in g
        assert "color" in g
        assert "timestamp" in g
        assert isinstance(g.get("entangled", []), list)
        assert isinstance(g.get("replay", []), list)

    # ✅ Check entanglement and collapse triggers
    symbols = [g["symbol"] for g in ghx_bundle["nodes"]]
    assert "↔" in symbols
    assert "⧖" in symbols

    # ✅ Check metadata
    assert "metadata" in ghx_bundle
    assert ghx_bundle["metadata"].get("ghx_version") == "1.0"
    assert ghx_bundle["metadata"].get("recursive_pack") is True

    # ✅ Save to debug file
    output_file = tmp_path / "test_seed_knowledge_pack.ghx.json"
    with open(output_file, "w") as f:
        json.dump(ghx_bundle, f, indent=2)

    assert output_file.exists()