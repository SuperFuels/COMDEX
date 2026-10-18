# ==========================================================
# File: backend/modules/aion_resonance/aion_symbolic_mapper.py
# ----------------------------------------------------------
# 💡 AION Symbolic Mapper - Phase 2: Symbolic Grid Expansion
# ----------------------------------------------------------
# Maps environmental events (move, collect, danger, reflect)
# into symbolic constructs from Symatic Algebra.
# Stores symbolic reflections in memory and broadcasts them
# to the Thought Stream for real-time visualization.
# ==========================================================

import datetime
from hashlib import sha256
import json
from pathlib import Path

from backend.modules.aion_learning.vault_store import AionLearningVaultStore
from backend.modules.aion_resonance.thought_stream import broadcast_event

# ----------------------------------------------------------
# Symbolic Dictionary - maps event -> Symatic operator
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

# ----------------------------------------------------------
# Helper: load + append to symbolic memory file
# ----------------------------------------------------------
def _append_symbolic_record(
    entry: dict,
    *,
    vault_store: AionLearningVaultStore,
    memory_path: Path,
) -> None:
    if vault_store.enabled:
        payload = {
            **entry,
            "event_type": "symbolic_reflection",
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        event_id = f"symbolic-reflection-{sha256(canonical).hexdigest()}"
        payload["event_id"] = event_id
        payload["ts_utc"] = str(entry.get("timestamp") or "")
        vault_store.append_event(event_id, payload)
        return

    memory_path.parent.mkdir(parents=True, exist_ok=True)
    data = []
    if memory_path.exists():
        try:
            with memory_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
    data.append(entry)
    with memory_path.open("w", encoding="utf-8") as f:
        json.dump(data[-500:], f, indent=2)  # keep last 500 entries


def _store_legacy_hexcore_memory(record: dict, memory_engine=None) -> None:
    """Preserve the legacy fan-out only outside Guardian authority.

    Importing HexCore creates additional repository-relative memory stores, so
    it must never be imported on the Guardian path.
    """

    if memory_engine is None:
        from backend.modules.hexcore.memory_engine import MemoryEngine

        memory_engine = MemoryEngine()
    memory_engine.store(
        {
            "label": f"symbolic_{record['event']}",
            "content": json.dumps(record, ensure_ascii=False),
        }
    )


# ----------------------------------------------------------
# Main Symbolic Processor
# ----------------------------------------------------------
async def process_event(
    event_type: str,
    phi_state: dict,
    belief_state: dict,
    *,
    vault_store: AionLearningVaultStore | None = None,
    memory_path: str | Path | None = None,
    legacy_memory_engine=None,
):
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
        reflection = "Collapse ∇ - entropy spike detected."
    elif event_type == "reflect":
        reflection = "Resonance ⟲ - internal self-feedback."
    elif event_type == "reinforce":
        reflection = "Measurement μ - baseline updated."
    else:
        reflection = f"Event {event_type} observed."

    record = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event": event_type,
        "symbol": symbol,
        "phi": phi_state,
        "belief": belief_state,
        "reflection": reflection,
    }

    # Store symbolic record
    store = vault_store or AionLearningVaultStore(
        auto_configure=memory_path is None
    )
    target_path = Path(memory_path or SYMBOLIC_MEMORY_PATH)
    _append_symbolic_record(
        record,
        vault_store=store,
        memory_path=target_path,
    )
    if not store.enabled:
        _store_legacy_hexcore_memory(record, legacy_memory_engine)

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
def get_recent_symbolic_reflections(
    n: int = 20,
    *,
    vault_store: AionLearningVaultStore | None = None,
    memory_path: str | Path | None = None,
):
    limit = max(0, int(n))
    if limit == 0:
        return []
    store = vault_store or AionLearningVaultStore(
        auto_configure=memory_path is None
    )
    if store.enabled:
        return store.list_events(kind="symbolic_reflection")[-limit:]

    target_path = Path(memory_path or SYMBOLIC_MEMORY_PATH)
    if not target_path.exists():
        return []
    try:
        with target_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data[-limit:]
    except Exception:
        return []
