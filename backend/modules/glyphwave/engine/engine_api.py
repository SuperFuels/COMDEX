# File: backend/modules/glyphwave/engine/engine_api.py
import time
import threading
from queue import Queue, Empty

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.core.wave_state_store import WaveStateStore
from backend.modules.glyphwave.core.entangled_wave import EntangledWave
from backend.modules.glyphwave.kernels.interference_kernels import interfere, entangle
from backend.modules.glyphwave.logging.glyph_trace_logger import log_wave_event

# ✅ SymbolGraph adapter
from backend.modules.symbolic.adapters.symbolgraph_adapter import (
    get_bias_vector,
    push_measurement,
)

# ✅ Knowledge Graph adapter
from backend.modules.glyphwave.adapters.knowledge_graph_adapter import store_wave_measurement_in_kg

# Global wave store
wave_store = WaveStateStore()

# Async-safe queue for pushing to GPU/backends
wave_input_queue = Queue()

def push_wave(glyph_id: str, amplitude: float = 1.0, phase: float = 0.0, coherence: float = 1.0, metadata: dict = None):
    """Create and push a wave from a glyph."""
    # ✅ Apply bias vector if available
    bias = get_bias_vector(glyph_id)
    if bias:
        amplitude = bias.get("amplitude", amplitude)
        phase = bias.get("phase", phase)
        coherence = bias.get("coherence", coherence)

    wave = WaveState(
        id=f"WAVE_{glyph_id}_{int(time.time() * 1000)}",
        phase=phase,
        amplitude=amplitude,
        coherence=coherence,
        origin_trace=[glyph_id],
        timestamp=time.time(),
        metadata=metadata or {}
    )
    wave_store.add_wave(wave)
    wave_input_queue.put(wave)
    log_wave_event("push_wave", wave)
    return wave

def interfere_waves(wave_ids: list):
    """Interfere multiple waves by ID."""
    waves = [wave_store.get_wave(wid) for wid in wave_ids if wave_store.get_wave(wid)]
    if not waves:
        return None
    result = waves[0]
    for w in waves[1:]:
        result = interfere(result, w)
    wave_store.add_wave(result)
    log_wave_event("interfere", result)
    return result

def entangle_waves(wave_ids: list, mode="bidirectional"):
    """Entangle multiple waves by ID."""
    waves = [wave_store.get_wave(wid) for wid in wave_ids if wave_store.get_wave(wid)]
    if not waves:
        return None
    ent = entangle(waves, mode=mode)
    log_wave_event("entangle", ent)
    return ent

def measure_wave(wave_id: str, policy="greedy"):
    """Collapse and store result in SymbolGraph + KG."""
    wave = wave_store.get_wave(wave_id)
    if not wave:
        return None
    collapsed = {
        "glyph_id": wave.origin_trace[0] if wave.origin_trace else "unknown",
        "amplitude": wave.amplitude,
        "coherence": wave.coherence,
        "timestamp": time.time(),
        "policy": policy
    }
    log_wave_event("measure", wave, extra=collapsed)

    # ✅ Store result in SymbolGraph
    push_measurement(
        glyph_id=collapsed["glyph_id"],
        collapse_value=collapsed["amplitude"],
        score=collapsed["coherence"]
    )

    # ✅ Also store in Knowledge Graph
    store_wave_measurement_in_kg(collapsed, source_wave=wave.to_dict())

    return collapsed

# Background thread to handle wave input queue
def wave_input_loop():
    while True:
        try:
            wave = wave_input_queue.get(timeout=0.5)
            log_wave_event("queue_dispatch", wave)
            # Placeholder: dispatch to GPU/core system here
            time.sleep(0.01)  # simulate latency
        except Empty:
            continue

# Start the background loop
threading.Thread(target=wave_input_loop, daemon=True).start()

# JSON/GWIP input shape example
def parse_gwave_packet(packet: dict):
    """Create a wave from a JSON/GWIP packet."""
    return push_wave(
        glyph_id=packet.get("glyph_id", "unknown"),
        amplitude=packet.get("amplitude", 1.0),
        phase=packet.get("phase", 0.0),
        coherence=packet.get("coherence", 1.0),
        metadata=packet.get("metadata", {})
    )