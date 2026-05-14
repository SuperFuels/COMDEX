# backend/tests/test_glyph_reversibility.py

import os
import tempfile
from backend.modules.dna_chain.dc_handler import save_dimension
from backend.modules.glyphos.glyph_trigger_engine import scan_and_trigger
from backend.modules.hexcore.memory_engine import MemoryEngine

def create_reversible_container(path: str):
    container = {
        "id": "reversibility_test",
        "name": "Reversibility Container",
        "description": "Test for glyph to memory and back",
        "microgrid": {
            "0,0,0,null": {
                "type": "Memory",
                "tag": "note",
                "value": "mirror test glyph",
                "action": "store",
                "glyph": "🜁"
            }
        }
    }
    save_dimension(path, container)

def test_reversibility():
    with tempfile.NamedTemporaryFile(suffix=".dc.json", delete=False) as tf:
        temp_path = tf.name
    create_reversible_container(temp_path)
    scan_and_trigger(temp_path)

    # Fetch memory content and verify exact value
    memory = MemoryEngine()
    entries = memory.get_all()

    matched = [
        m for m in entries
        if m.get("label") == "trigger:seed" and m.get("content") == "Seeded memory: mirror test glyph"
    ]

    assert matched, "❌ Reversibility test failed: content not stored exactly"
    print("✅ Reversibility test passed: content preserved from glyph to memory")

if __name__ == "__main__":
    test_reversibility()