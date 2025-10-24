# ================================================================
# 🧠 CEE LexMemory — Resonant Knowledge Reinforcement Engine
# Phase 45G.10 — Persistent Symbolic Resonance Memory
# ================================================================
"""
Stores and recalls resonance-weighted associations learned during
language and reasoning exercises.

Each record encodes a symbolic relationship between tokens and
its resonance weights (ρ, Ī, SQI). This enables Aion to *remember*
concept bindings across sessions — not by rote, but by field coherence.

Memory file:
    data/memory/lex_memory.json

Integration points:
  • update_lex_memory(prompt, answer, resonance)
  • recall_from_memory(prompt)
  • decay_memory() — optional gradual forgetting
"""

import json, logging, time, math
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)
MEMORY_PATH = Path("data/memory/lex_memory.json")


# ------------------------------------------------------------
def _load_memory() -> Dict[str, Any]:
    if not MEMORY_PATH.exists():
        MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        return {}
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[LexMemory] Could not load memory file: {e}")
        return {}


def _save_memory(data: Dict[str, Any]):
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ------------------------------------------------------------
def _make_key(prompt: str, answer: str) -> str:
    """Create a stable symbolic key."""
    return f"{prompt.strip()}↔{answer.strip()}"


# ------------------------------------------------------------
def update_lex_memory(prompt: str, answer: str, resonance: Dict[str, float]):
    """
    Reinforce or create a resonance link between `prompt` and `answer`.
    If it exists, merge the new resonance with exponential smoothing.
    """
    mem = _load_memory()
    key = _make_key(prompt, answer)
    entry = mem.get(key, {"ρ": 0.0, "I": 0.0, "SQI": 0.0, "count": 0, "last_update": 0})

    α = 0.35  # smoothing factor (learning rate)
    entry["ρ"] = round(entry["ρ"] * (1 - α) + resonance.get("ρ", 0) * α, 3)
    entry["I"] = round(entry["I"] * (1 - α) + resonance.get("I", 0) * α, 3)
    entry["SQI"] = round(entry["SQI"] * (1 - α) + resonance.get("SQI", 0) * α, 3)
    entry["count"] += 1
    entry["last_update"] = time.time()

    mem[key] = entry
    _save_memory(mem)
    logger.info(f"[LexMemory] Reinforced {key} → SQI={entry['SQI']}, count={entry['count']}")


# ------------------------------------------------------------
def recall_from_memory(prompt: str) -> Dict[str, Any]:
    """
    Return the most resonant stored answer for a given prompt.
    Used before guessing to simulate recall from the LexField.
    """
    mem = _load_memory()
    candidates = {k: v for k, v in mem.items() if k.startswith(prompt)}

    if not candidates:
        return {}

    # Choose the entry with highest SQI
    best_key, best_val = max(candidates.items(), key=lambda kv: kv[1].get("SQI", 0))
    answer = best_key.split("↔")[-1]
    return {"prompt": prompt, "answer": answer, "resonance": best_val}


# ------------------------------------------------------------
def decay_memory(half_life_hours: float = 48.0):
    """
    Apply natural forgetting — reduce resonance over time.
    """
    mem = _load_memory()
    now = time.time()
    decay_rate = math.log(2) / (half_life_hours * 3600)

    for k, v in mem.items():
        age = now - v.get("last_update", now)
        factor = math.exp(-decay_rate * age)
        v["ρ"] = round(v["ρ"] * factor, 3)
        v["I"] = round(v["I"] * factor, 3)
        v["SQI"] = round(v["SQI"] * factor, 3)

    _save_memory(mem)
    logger.info(f"[LexMemory] Applied decay with half-life={half_life_hours}h")


# ------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Simple test harness
    update_lex_memory("sun rises in", "east", {"ρ": 0.82, "I": 0.9, "SQI": 0.86})
    update_lex_memory("happy", "joyful", {"ρ": 0.88, "I": 0.92, "SQI": 0.9})
    print(recall_from_memory("sun rises in"))