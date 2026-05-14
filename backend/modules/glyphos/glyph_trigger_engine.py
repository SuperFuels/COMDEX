# Triggers runtime behavior based on detected glyphs inside a .dc container

from typing import Callable, Dict, Any
import time
import threading
import os

from backend.modules.dna_chain.dc_handler import load_dimension_by_file
from backend.modules.glyphos.microgrid_index import MicrogridIndex
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.aion.dream_core import trigger_dream_reflection
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.consciousness.memory_bridge import MemoryBridge
from backend.modules.glyphos.glyph_mutator import propose_mutation, run_self_rewrite
from backend.modules.glyphos.glyph_trace_logger import glyph_trace

# Optional WebSocket push
try:
    from modules.websocket_manager import WebSocketManager
    WS = WebSocketManager()
except:
    WS = None

# Initialize core modules
memory = MemoryEngine()
state = StateManager()
container_path = state.get_current_container_path() or "containers/default.json"
container_id = os.path.splitext(os.path.basename(container_path))[0]
bridge = MemoryBridge(container_id)

# Glyph-triggered action definitions
def trigger_dream_core(metadata: Dict[str, Any]):
    print(f"🌙 Triggering DreamCore from glyph: {metadata}")
    trigger_dream_reflection(source="glyph_trigger", context=metadata)
    bridge.trace_trigger("✦", {**metadata, "origin": "glyph_trigger_engine", "role": "Dream reflection"})
    glyph_trace.log_trace("✦", "trigger_dream", context="trigger")

def trigger_teleport(metadata: Dict[str, Any]):
    print(f"🧽 Teleport activated by glyph: {metadata}")
    memory.store({
        "label": "trigger:teleport",
        "content": f"Teleport glyph triggered at {metadata.get('coord', '?')}"
    })
    bridge.trace_trigger("🧽", {**metadata, "origin": "glyph_trigger_engine", "role": "Teleport command"})
    glyph_trace.log_trace("🧽", "trigger_teleport", context="trigger")

def trigger_ethics(metadata: Dict[str, Any]):
    print(f"⚛ SoulLaw check: {metadata}")
    memory.store({
        "label": "trigger:ethics",
        "content": f"Ethic glyph triggered with payload: {metadata}"
    })
    bridge.trace_trigger("⚛", {**metadata, "origin": "glyph_trigger_engine", "role": "SoulLaw check"})
    glyph_trace.log_trace("⚛", "trigger_ethics", context="trigger")

def trigger_memory_seed(metadata: Dict[str, Any]):
    print(f"0, Storing memory seed: {metadata}")
    memory.store({
        "label": "trigger:seed",
        "content": f"Seeded memory: {metadata.get('value', 'unknown')}"
    })
    bridge.trace_trigger("0,", {**metadata, "origin": "glyph_trigger_engine", "role": "Seed memory injection"})
    glyph_trace.log_trace("0,", "trigger_memory_seed", context="trigger")

def trigger_compression(metadata: Dict[str, Any]):
    print(f"⌜ Compression event: {metadata}")
    memory.store({
        "label": "trigger:compress",
        "content": f"Compression glyph triggered for: {metadata.get('coord', '?')}"
    })
    bridge.trace_trigger("⌜", {**metadata, "origin": "glyph_trigger_engine", "role": "Compression event"})
    glyph_trace.log_trace("⌜", "trigger_compression", context="trigger")

def trigger_lock(metadata: Dict[str, Any]):
    print(f"⨿ Dimension lock triggered: {metadata}")
    memory.store({
        "label": "trigger:lock",
        "content": f"Lock glyph triggered. Tag: {metadata.get('tag', 'none')}"
    })
    bridge.trace_trigger("⨿", {**metadata, "origin": "glyph_trigger_engine", "role": "Dimension gate lock"})
    glyph_trace.log_trace("⨿", "trigger_lock", context="trigger")

def trigger_decay_rewrite(coord: str, meta: Dict[str, Any]):
    age_ms = meta.get("age_ms", 0)
    if age_ms > 60000:
        print(f"♻️ Glyph at {coord} decayed - proposing rewrite")
        propose_mutation({
            "reason": "Decay-triggered glyph rewrite",
            "coord": coord,
            "glyph": meta.get("glyph"),
            "age_ms": age_ms
        })
        bridge.trace_trigger("♻️", {**meta, "coord": coord, "origin": "glyph_trigger_engine", "role": "Decay-based rewrite"})
        glyph_trace.log_trace("♻️", "decay_rewrite", context="trigger")

def trigger_self_rewrite(coord: str, meta: Dict[str, Any]):
    glyph = meta.get("glyph", "")
    if glyph.strip().startswith("⟦ Write") or glyph.strip().startswith("⟦ Mutate"):
        if container_path:
            print(f"♻️ Self-rewrite glyph detected at {coord}")
            success = run_self_rewrite(container_path, coord)
            status = "success" if success else "skipped"
            print(f"✅ Self-rewrite {status} at {coord}")
            glyph_trace.log_trace("⬁", f"self_rewrite:{status}", context="trigger")

# Trigger handler map
GLYPH_TRIGGER_MAP: Dict[str, Callable[[Dict[str, Any]], None]] = {
    "✦": trigger_dream_core,
    "🧽": trigger_teleport,
    "⚛": trigger_ethics,
    "0,": trigger_memory_seed,
    "⌜": trigger_compression,
    "⨿": trigger_lock,
}

# Runtime control
_last_glyph_state = {}
_loop_active = True

def emit_event_log(event: str, detail: Any = None):
    memory.store({
        "label": "glyph:scan_event",
        "content": f"Glyph scan event: {event} - {detail}"
    })

def scan_and_trigger(path: str):
    dimension = load_dimension_by_file(path)
    index = MicrogridIndex()
    index.import_index(dimension.get("microgrid", {}))

    for coord, meta in index.glyph_map.items():
        glyph = meta.get("glyph")
        if not glyph:
            continue

        meta["coord"] = coord

        if glyph in GLYPH_TRIGGER_MAP:
            GLYPH_TRIGGER_MAP[glyph](meta)

        trigger_self_rewrite(coord, meta)
        trigger_decay_rewrite(coord, meta)

        if meta.get("type") == "Memory" and meta.get("action") == "store":
            memory.store({
                "label": f"glyph:{meta.get('tag', 'note')}",
                "content": meta.get("value", "Unnamed memory")
            })
            bridge.trace_trigger("📝", {**meta, "coord": coord, "origin": "glyph_trigger_engine", "role": "Passive memory store"})

def glyph_behavior_loop(interval: float = 5.0):
    global _loop_active

    if not container_path:
        print("⚠️ No container loaded - skipping glyph scan")
        return

    print("🔄 Starting glyph behavior loop...")

    while _loop_active:
        try:
            dimension = load_dimension_by_file(container_path)
            index = MicrogridIndex()
            index.import_index(dimension.get("microgrid", {}))

            triggered_this_cycle = []

            for coord, meta in index.glyph_map.items():
                glyph = meta.get("glyph")
                key = f"{coord}:{glyph}"
                if not glyph or _last_glyph_state.get(key):
                    continue

                meta["coord"] = coord

                if glyph in GLYPH_TRIGGER_MAP:
                    GLYPH_TRIGGER_MAP[glyph](meta)
                    glyph_trace.log_trace(glyph, "triggered", context="loop")
                    _last_glyph_state[key] = True
                    triggered_this_cycle.append(glyph)

                trigger_self_rewrite(coord, meta)
                trigger_decay_rewrite(coord, meta)

            if triggered_this_cycle:
                emit_event_log("cycle_complete", triggered_this_cycle)

        except Exception as e:
            print(f"❌ Glyph behavior loop error: {e}")
            emit_event_log("loop_error", str(e))

        time.sleep(interval)

def stop_glyph_loop():
    global _loop_active
    _loop_active = False
    print("🛑 Glyph behavior loop stopped.")

# Optional test
if __name__ == "__main__":
    test_path = "backend/modules/dimensions/containers/test_trigger.dc"
    scan_and_trigger(test_path)