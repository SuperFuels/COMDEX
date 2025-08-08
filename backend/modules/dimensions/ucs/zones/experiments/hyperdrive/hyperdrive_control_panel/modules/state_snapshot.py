# ===============================
# 🔄 Universal Container State Snapshot
# ===============================

def get_state(engine):
    """Capture the active universal container system state."""
    return {
        "fields": getattr(engine, "fields", {}),
        "particles": getattr(engine, "particles", []),
        "tick_count": getattr(engine, "tick_count", 0),
        "resonance": getattr(engine, "resonance_phase", 0.0),
        "sqi_enabled": getattr(engine, "sqi_enabled", False),
        "injectors": getattr(engine, "injectors", []),
        "chambers": getattr(engine, "chambers", []),
        "exhaust_log": getattr(engine, "exhaust_log", []),
        "resonance_filtered": getattr(engine, "resonance_filtered", []),
    }

def set_state(engine, state):
    """Restore the engine's universal container system state."""
    engine.fields = state.get("fields", {})
    engine.particles = state.get("particles", [])
    engine.tick_count = state.get("tick_count", 0)
    engine.resonance_phase = state.get("resonance", 0.0)
    engine.sqi_enabled = state.get("sqi_enabled", False)
    engine.injectors = state.get("injectors", [])
    engine.chambers = state.get("chambers", [])
    engine.exhaust_log = state.get("exhaust_log", [])
    engine.resonance_filtered = state.get("resonance_filtered", [])