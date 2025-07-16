# backend/modules/glyphos/glyph_trigger_engine.py
# Triggers runtime behavior based on detected glyphs inside a .dc container

from typing import Callable, Dict, Any
import time
import threading
from backend.modules.dna_chain.dc_handler import load_dimension_by_file
from backend.modules.glyphos.microgrid_index import MicrogridIndex
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.aion.dream_core import trigger_dream_reflection
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.memory.memory_bridge import MemoryBridge  # ✅ New
from backend.modules.dna_chain.glyph_mutator import propose_rewrite  # ♻️ Glyph rewrite

# Instantiate memory engine for feedback
memory = MemoryEngine()
state = StateManager()
container_id = state.get_current_container_id() or "default"
bridge = MemoryBridge(container_id)  # ✅ MemoryBridge instance

# Glyph-triggered action definitions
def trigger_dream_core(metadata: Dict[str, Any]):
    print(f"🌙 Triggering DreamCore from glyph: {metadata}")
    trigger_dream_reflection(source="glyph_trigger", context=metadata)
    bridge.trace_trigger("✦", {
        **metadata,
        "origin": "glyph_trigger_engine",
        "role": "Dream reflection",
    })

def trigger_teleport(metadata: Dict[str, Any]):
    print(f"🧽 Teleport activated by glyph: {metadata}")
    memory.store({
        "label": "trigger:teleport",
        "content": f"Teleport glyph triggered at {metadata.get('coord', '?')}"
    })
    bridge.trace_trigger("🧽", {
        **metadata,
        "origin": "glyph_trigger_engine",
        "role": "Teleport command",
    })

def trigger_ethics(metadata: Dict[str, Any]):
    print(f"⚛ SoulLaw check: {metadata}")
    memory.store({
        "label": "trigger:ethics",
        "content": f"Ethic glyph triggered with payload: {metadata}"
    })
    bridge.trace_trigger("⚛", {
        **metadata,
        "origin": "glyph_trigger_engine",
        "role": "SoulLaw check",
    })

def trigger_memory_seed(metadata: Dict[str, Any]):
    print(f"🄁 Storing memory seed: {metadata}")
    memory.store({
        "label": "trigger:seed",
        "content": f"Seeded memory: {metadata.get('value', 'unknown')}"
    })
    bridge.trace_trigger("🄁", {
        **metadata,
        "origin": "glyph_trigger_engine",
        "role": "Seed memory injection",
    })

def trigger_compression(metadata: Dict[str, Any]):
    print(f"⌜ Compression event: {metadata}")
    memory.store({
        "label": "trigger:compress",
        "content": f"Compression glyph triggered for: {metadata.get('coord', '?')}"
    })
    bridge.trace_trigger("⌜", {
        **metadata,
        "origin": "glyph_trigger_engine",
        "role": "Compression event",
    })

def trigger_lock(metadata: Dict[str, Any]):
    print(f"⨿ Dimension lock triggered: {metadata}")
    memory.store({
        "label": "trigger:lock",
        "content": f"Lock glyph triggered. Tag: {metadata.get('tag', 'none')}"
    })
    bridge.trace_trigger("⨿", {
        **metadata,
        "origin": "glyph_trigger_engine",
        "role": "Dimension gate lock",
    })

def trigger_decay_rewrite(coord: str, meta: Dict[str, Any]):
    age_ms = meta.get("age_ms", 0)
    if age_ms > 60000:  # 60s decay threshold
        print(f"♻️ Glyph at {coord} decayed — proposing rewrite")
        propose_rewrite(coord, {
            "reason": "Decay-triggered glyph rewrite",
            "original_glyph": meta.get("glyph"),
            "age_ms": age_ms,
            "metadata": meta
        })
        bridge.trace_trigger("♻️", {
            **meta,
            "coord": coord,
            "origin": "glyph_trigger_engine",
            "role": "Decay-based rewrite",
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

# Runtime state and control
_last_glyph_state = {}
_loop_active = True  # Graceful shutdown flag

def emit_event_log(event: str, detail: Any = None):
    memory.store({
        "label": "glyph:scan_event",
        "content": f"Glyph scan event: {event} — {detail}"
    })

def scan_and_trigger(container_path: str):
    """Load .dc container, parse all glyphs, and trigger mapped behavior."""
    dimension = load_dimension_by_file(container_path)
    index = MicrogridIndex()
    index.import_index(dimension.get("microgrid", {}))

    for coord, meta in index.glyph_map.items():
        glyph = meta.get("glyph")

        if not glyph:
            continue

        if glyph in GLYPH_TRIGGER_MAP:
            print(f"🚨 Triggering behavior for glyph {glyph} at {coord}")
            meta["coord"] = coord
            GLYPH_TRIGGER_MAP[glyph](meta)

        # Decay rewrite logic
        trigger_decay_rewrite(coord, meta)

        elif meta.get("type") == "Memory" and meta.get("action") == "store":
            print(f"📄 Storing memory glyph at {coord}: {meta}")
            label = f"glyph:{meta.get('tag', 'note')}"
            content = meta.get("value", "Unnamed memory")
            memory.store({
                "label": label,
                "content": content
            })

def glyph_behavior_loop(interval: float = 5.0):
    """Continuously scan for new glyphs and trigger mapped behaviors."""
    global _loop_active
    state = StateManager()
    path = state.get_current_container_path()

    if not path:
        print("⚠️ No container loaded — skipping glyph scan")
        return

    print("🔄 Starting glyph behavior loop...")

    while _loop_active:
        try:
            dimension = load_dimension_by_file(path)
            index = MicrogridIndex()
            index.import_index(dimension.get("microgrid", {}))

            triggered_this_cycle = []

            for coord, meta in index.glyph_map.items():
                glyph = meta.get("glyph")
                key = f"{coord}:{glyph}"

                if not glyph or key in _last_glyph_state:
                    continue

                if glyph in GLYPH_TRIGGER_MAP:
                    print(f"⚡ Triggering glyph behavior: {glyph} at {coord}")
                    meta["coord"] = coord
                    GLYPH_TRIGGER_MAP[glyph](meta)
                    _last_glyph_state[key] = True
                    triggered_this_cycle.append(glyph)

                # Also check for decay-based rebirth
                trigger_decay_rewrite(coord, meta)

            if triggered_this_cycle:
                emit_event_log("cycle_complete", triggered_this_cycle)

        except Exception as e:
            print(f"❌ Glyph behavior loop error: {e}")
            emit_event_log("loop_error", str(e))

        time.sleep(interval)

def stop_glyph_loop():
    """Signal loop to stop gracefully."""
    global _loop_active
    _loop_active = False
    print("🛑 Glyph behavior loop stopped.")

# For testing
if __name__ == "__main__":
    test_path = "backend/modules/dimensions/containers/test_trigger.dc"
    scan_and_trigger(test_path)

    # threading.Thread(target=glyph_behavior_loop).start()
    # time.sleep(30)
    # stop_glyph_loop()