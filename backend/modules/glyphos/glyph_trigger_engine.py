# backend/modules/glyphos/glyph_trigger_engine.py
# Triggers runtime behavior based on detected glyphs inside a .dc container

from typing import Callable, Dict, Any
import time
from backend.modules.dna_chain.dc_handler import load_dimension_by_file
from backend.modules.glyphos.microgrid_index import MicrogridIndex
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.aion.dream_core import trigger_dream_reflection
from backend.modules.consciousness.state_manager import StateManager

# Instantiate memory engine for feedback
memory = MemoryEngine()

# Glyph-triggered action definitions
def trigger_dream_core(metadata: Dict[str, Any]):
    print(f"🌙 Triggering DreamCore from glyph: {metadata}")
    trigger_dream_reflection(source="glyph_trigger", context=metadata)

def trigger_teleport(metadata: Dict[str, Any]):
    print(f"🧽 Teleport activated by glyph: {metadata}")
    memory.store({
        "label": "trigger:teleport",
        "content": f"Teleport glyph triggered at {metadata.get('coord', '?')}"
    })

def trigger_ethics(metadata: Dict[str, Any]):
    print(f"⚛ SoulLaw check: {metadata}")
    memory.store({
        "label": "trigger:ethics",
        "content": f"Ethic glyph triggered with payload: {metadata}"
    })

def trigger_memory_seed(metadata: Dict[str, Any]):
    print(f"🄁 Storing memory seed: {metadata}")
    memory.store({
        "label": "trigger:seed",
        "content": f"Seeded memory: {metadata.get('value', 'unknown')}"
    })

def trigger_compression(metadata: Dict[str, Any]):
    print(f"⌜ Compression event: {metadata}")
    memory.store({
        "label": "trigger:compress",
        "content": f"Compression glyph triggered for: {metadata.get('coord', '?')}"
    })

def trigger_lock(metadata: Dict[str, Any]):
    print(f"⨿ Dimension lock triggered: {metadata}")
    memory.store({
        "label": "trigger:lock",
        "content": f"Lock glyph triggered. Tag: {metadata.get('tag', 'none')}"
    })

# Glyph character → handler map
GLYPH_TRIGGER_MAP: Dict[str, Callable[[Dict[str, Any]], None]] = {
    "✦": trigger_dream_core,
    "🧽": trigger_teleport,
    "⚛": trigger_ethics,
    "🄁": trigger_memory_seed,
    "⌜": trigger_compression,
    "⨿": trigger_lock,
}

def scan_and_trigger(container_path: str):
    """Load .dc container, parse all glyphs, and trigger mapped behavior."""
    dimension = load_dimension_by_file(container_path)
    index = MicrogridIndex()
    index.import_index(dimension.get("microgrid", {}))

    for coord, meta in index.glyph_map.items():
        glyph = meta.get("glyph")

        # 1. Direct glyph triggers (via character map)
        if glyph in GLYPH_TRIGGER_MAP:
            print(f"🚨 Triggering behavior for glyph {glyph} at {coord}")
            meta["coord"] = coord
            GLYPH_TRIGGER_MAP[glyph](meta)

        # 2. Memory action
        elif meta.get("type") == "Memory" and meta.get("action") == "store":
            print(f"📄 Storing memory glyph at {coord}: {meta}")
            label = f"glyph:{meta.get('tag', 'note')}"
            content = meta.get("value", "Unnamed memory")
            memory.store({
                "label": label,
                "content": content
            })

# Runtime loop support for C10: Trigger-on-glyph behavior loop
_last_glyph_state = {}

def glyph_behavior_loop(interval: float = 5.0):
    """Continuously scan for new glyphs and trigger mapped behaviors."""
    state = StateManager()
    path = state.get_current_container_path()

    if not path:
        print("⚠️ No container loaded — skipping glyph scan")
        return

    print("🔄 Starting glyph behavior loop...")
    while True:
        try:
            dimension = load_dimension_by_file(path)
            index = MicrogridIndex()
            index.import_index(dimension.get("microgrid", {}))

            for coord, meta in index.glyph_map.items():
                glyph = meta.get("glyph")
                key = f"{coord}:{glyph}"

                # Skip if seen before (to avoid duplicate triggering)
                if key in _last_glyph_state:
                    continue

                if glyph in GLYPH_TRIGGER_MAP:
                    print(f"⚡ Triggering glyph behavior: {glyph} at {coord}")
                    meta["coord"] = coord
                    GLYPH_TRIGGER_MAP[glyph](meta)
                    _last_glyph_state[key] = True

        except Exception as e:
            print(f"❌ Glyph behavior loop error: {e}")

        time.sleep(interval)

if __name__ == "__main__":
    test_path = "backend/modules/dimensions/containers/test_trigger.dc"
    scan_and_trigger(test_path)
