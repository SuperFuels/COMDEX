# ==========================================================
# File: backend/modules/aion_resonance/aion_symbolic_mapper.py
# ----------------------------------------------------------
# 💡 AION Symbolic Mapper — Phase 2: Symbolic Grid Expansion
# ----------------------------------------------------------
# Maps environmental events (move, collect, danger, reflect)
# into symbolic constructs from Symatic Algebra.
# Stores symbolic reflections in memory and broadcasts them
# to the Thought Stream for real-time visualization.
# ==========================================================

import json, datetime, os
from pathlib import Path
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.aion_resonance.thought_stream import broadcast_event

# ----------------------------------------------------------
# Symbolic Dictionary — maps event → Symatic operator
# ----------------------------------------------------------
SYMBOLIC_MAP = {
    "move": "↔",         # exploration / entanglement
    "collect": "⊕",      # superposition / success
    "danger": "∇",       # collapse / entropy
    "reflect": "⟲",      # resonance / self-reflection
    "reinforce": "μ",    # measurement / learning
}

# File to store symbolic reflection history
SYMBOLIC_MEMORY_PATH = Path("data/symbolic_memory.json")

memory = MemoryEngine()

# ----------------------------------------------------------
# Helper: load + append to symbolic memory file
# ----------------------------------------------------------
def _append_symbolic_record(entry):
    os.makedirs(SYMBOLIC_MEMORY_PATH.parent, exist_ok=True)
    data = []
    if SYMBOLIC_MEMORY_PATH.exists():
        try:
            with open(SYMBOLIC_MEMORY_PATH, "r") as f:
                data = json.load(f)
        except Exception:
            data = []
    data.append(entry)
    with open(SYMBOLIC_MEMORY_PATH, "w") as f:
        json.dump(data[-500:], f, indent=2)  # keep last 500 entries


# ----------------------------------------------------------
# Main Symbolic Processor
# ----------------------------------------------------------
async def process_event(event_type: str, phi_state: dict, belief_state: dict):
    """
    Translate an AION cognitive event into its symbolic form,
    store in memory, and broadcast to the Thought Stream.
    """

    symbol = SYMBOLIC_MAP.get(event_type, "?")
    reflection = ""

    # Simple interpretive templates
    if event_type == "move":
        reflection = "Exploration ↔ curiosity extension."
    elif event_type == "collect":
        reflection = "Superposition ⊕ of curiosity and stability."
    elif event_type == "danger":
        reflection = "Collapse ∇ — entropy spike detected."
    elif event_type == "reflect":
        reflection = "Resonance ⟲ — internal self-feedback."
    elif event_type == "reinforce":
        reflection = "Measurement μ — baseline updated."
    else:
        reflection = f"Event {event_type} observed."

    record = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "event": event_type,
        "symbol": symbol,
        "phi": phi_state,
        "belief": belief_state,
        "reflection": reflection,
    }

    # Store symbolic record
    _append_symbolic_record(record)
    memory.store({"label": f"symbolic_{event_type}", "content": json.dumps(record)})

    # Broadcast to Thought Stream
    await broadcast_event({
        "type": "symbolic_reflection",
        "symbol": symbol,
        "message": reflection,
        "phi": phi_state,
        "belief": belief_state,
        "timestamp": record["timestamp"],
    })

    print(f"[🧠 Symbolic Reflection] {symbol} {reflection}")
    return record


# ----------------------------------------------------------
# Public Accessor: get last N symbolic reflections
# ----------------------------------------------------------
def get_recent_symbolic_reflections(n: int = 20):
    if not SYMBOLIC_MEMORY_PATH.exists():
        return []
    try:
        with open(SYMBOLIC_MEMORY_PATH, "r") as f:
            data = json.load(f)
            return data[-n:]
    except Exception:
        return []