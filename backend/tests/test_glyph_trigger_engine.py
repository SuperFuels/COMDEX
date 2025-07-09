# backend/tests/test_glyph_trigger_engine.py

import os
import tempfile
from backend.modules.glyphos.glyph_trigger_engine import scan_and_trigger
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.dna_chain.dc_handler import save_dimension

def create_test_container(path: str):
    container = {
        "id": "test_container",
        "name": "Test Container",
        "description": "For glyph trigger test",
        "microgrid": {
            "0,0,0,null": {
                "type": "Memory",
                "tag": "note",
                "value": "just a note",
                "action": "store",
                "glyph": "🜁"
            }
        }
    }
    save_dimension(path, container)

def test_scan_and_trigger():
    with tempfile.NamedTemporaryFile(suffix=".dc.json", delete=False) as tf:
        temp_path = tf.name
    create_test_container(temp_path)
    scan_and_trigger(temp_path)

    # Reload memory and verify entry
    memory = MemoryEngine()
    entries = memory.get_all()

    # Match correct label and content
    matched = [
        m for m in entries
        if m.get("label") == "trigger:seed" and "just a note" in m.get("content", "")
    ]

    assert matched, "❌ Memory seed glyph not correctly stored in memory"
    print("✅ Glyph trigger test passed: memory seed found")

if __name__ == "__main__":
    test_scan_and_trigger()