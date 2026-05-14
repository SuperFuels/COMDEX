# backend/tests/test_glyph_runtime_loop.py

import tempfile
import time
from backend.modules.dna_chain.dc_handler import save_dimension
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.glyphos.glyph_trigger_engine import glyph_behavior_loop

def create_container_with_glyph(path: str):
    container = {
        "id": "glyph_loop_test",
        "name": "Loop Test Container",
        "microgrid": {
            "0,0,0,null": {
                "glyph": "🜁",  # memory seed glyph
                "type": "Memory",
                "tag": "observation",
                "value": "watch this glyph",
                "action": "store"
            }
        }
    }
    save_dimension(path, container)

def test_glyph_loop_behavior():
    with tempfile.NamedTemporaryFile(suffix=".dc.json", delete=False) as tf:
        test_path = tf.name
    create_container_with_glyph(test_path)

    # Patch StateManager to return our test path
    from backend.modules.consciousness.state_manager import StateManager
    StateManager().current_container = test_path

    # Run glyph loop for 3 seconds max
    from threading import Thread
    t = Thread(target=glyph_behavior_loop, kwargs={"interval": 1.0}, daemon=True)
    t.start()
    time.sleep(3)

    entries = MemoryEngine().get_all()
    matched = [m for m in entries if "watch this glyph" in m.get("content", "")]
    assert matched, "❌ Glyph behavior loop did not trigger memory store"
    print("✅ Glyph behavior loop triggered successfully")

if __name__ == "__main__":
    test_glyph_loop_behavior()