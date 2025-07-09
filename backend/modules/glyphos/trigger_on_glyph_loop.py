# File: backend/modules/glyphos/trigger_on_glyph_loop.py

import threading
import time
from backend.modules.consciousness.reflection_engine import ReflectionEngine
from backend.modules.dna_chain.dc_handler import load_dc_container
from backend.modules.hexcore.memory_engine import MEMORY

# Optional: Map glyphs to specific behavior
GLYPH_ACTIONS = {
    "🧠": lambda container_id: ReflectionEngine().reflect(),
    "✧": lambda container_id: MEMORY.store({
        "role": "system",
        "type": "glyph_trigger",
        "content": f"✧ glyph triggered a curiosity log in {container_id}"
    })
}

# Track which containers we've already scanned to avoid re-triggering
_triggered_flags = {}

def trigger_on_glyph_loop(poll_interval=5):
    print("🔁 Starting glyph-on-trigger scanner...")
    while True:
        try:
            for container_id in _triggered_flags.keys():
                container = load_dc_container(container_id)
                microgrid = container.get("microgrid", {})
                for coord, glyph in microgrid.items():
                    symbol = glyph.get("symbol")
                    if symbol in GLYPH_ACTIONS:
                        unique_key = f"{container_id}:{coord}:{symbol}"
                        if not _triggered_flags[container_id].get(unique_key):
                            print(f"⚡ Triggering glyph {symbol} at {coord} in {container_id}")
                            GLYPH_ACTIONS[symbol](container_id)
                            _triggered_flags[container_id][unique_key] = True
        except Exception as e:
            print(f"[⚠️ GlyphTriggerError] {e}")

        time.sleep(poll_interval)

def register_container_for_glyph_triggers(container_id):
    if container_id not in _triggered_flags:
        _triggered_flags[container_id] = {}
        print(f"✅ Registered container for glyph triggers: {container_id}")

# Launchable thread

def start_trigger_loop():
    thread = threading.Thread(target=trigger_on_glyph_loop, daemon=True)
    thread.start()
    return thread