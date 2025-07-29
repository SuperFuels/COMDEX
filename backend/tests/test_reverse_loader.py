# backend/tests/test_reverse_loader.py

import os
import json
import tempfile
from backend.modules.glyphos.glyph_reverse_loader import extract_glyphs_from_universal_container_system
from backend.modules.dna_chain.dc_handler import save_dimension

def create_test_container(path: str):
    """Creates a mock .dc container file with known glyph bytecode."""
    dimension = {
        "name": "test_container",
        "cubes": [
            {
                "x": 0, "y": 0, "z": 0,
                "bytecode": "⟦ Memory | Note : 'Test' → Save ⟧"
            },
            {
                "x": 1, "y": 1, "z": 1,
                "bytecode": "⟦ Skill | Learn : Python → Boot ⟧"
            },
            {
                "x": 2, "y": 2, "z": 2,
                "bytecode": "INVALID"
            }
        ]
    }
    save_dimension(dimension, path)

def test_extract_glyphs_from_container():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "test.dc")
        create_test_container(test_path)

        glyphs = extract_glyphs_from_container(test_path)

        # We expect 2 valid glyphs, 1 invalid one ignored
        assert len(glyphs) == 2
        assert glyphs[0]["tag"] == "Note"
        assert glyphs[1]["tag"] == "Learn"
        assert "coord" in glyphs[0]

        print("[✅] test_extract_glyphs_from_container passed.")