# ================================================================
# 🧠 CEE LexMemory — Resonant Knowledge Reinforcement Engine
# Phase 45G.12 — Persistent Symbolic Resonance Memory (Fuzzy Recall)
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
  • decay_memory() — gradual forgetting
"""

import json, logging, time, math, os, re
from pathlib import Path
from typing import Dict, Any
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)
MEMORY_PATH = Path("data/memory/lex_memory.json")

# ------------------------------------------------------------
# 🧩 Internal Utilities
# ------------------------------------------------------------
def _load_memory() -> Dict[str, Any]:
    """Safely load memory from disk."""
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
    """Persist memory structure to disk."""
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def _make_key(prompt: str, answer: str) -> str:
    """Create a stable symbolic key joining prompt and answer."""
    return f"{prompt.strip()}↔{answer.strip()}"

# ------------------------------------------------------------
# 🔁 Memory Update / Reinforcement
# ------------------------------------------------------------
def update_lex_memory(prompt: str, answer: str, resonance: Dict[str, float]):
    """
    Reinforce or create a resonance link between `prompt` and `answer`.
    If it exists, merge the new resonance with exponential smoothing.
    """
    mem = _load_memory()
    key = _make_key(prompt, answer)
    entry = mem.get(key, {"ρ": 0.0, "I": 0.0, "SQI": 0.0, "count": 0, "last_update": 0})

    α = 0.35  # learning rate / smoothing factor
    entry["ρ"] = round(entry["ρ"] * (1 - α) + resonance.get("ρ", 0) * α, 3)
    entry["I"] = round(entry["I"] * (1 - α) + resonance.get("I", 0) * α, 3)
    entry["SQI"] = round(entry["SQI"] * (1 - α) + resonance.get("SQI", 0) * α, 3)
    entry["count"] += 1
    entry["last_update"] = time.time()

    mem[key] = entry
    _save_memory(mem)
    logger.info(f"[LexMemory] Reinforced {key} → SQI={entry['SQI']}, count={entry['count']}")

# ------------------------------------------------------------
# 🔍 Field-Coherent Semantic Recall
# ------------------------------------------------------------
def _normalize_prompt(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text

def _tokenize(text: str) -> set:
    return set(_normalize_prompt(text).split())

def recall_from_memory(prompt: str) -> Dict[str, Any]:
    """
    Field-coherent recall: combines fuzzy and token-overlap similarity.
    Enables conceptual recall across rephrased linguistic prompts.
    """
    mem = _load_memory()
    if not mem or not prompt:
        return {}

    prompt_norm = _normalize_prompt(prompt)
    prompt_tokens = _tokenize(prompt)
    best_key, best_val, best_score = None, None, 0.0

    for key, entry in mem.items():
        base_prompt = key.split("↔")[0]
        base_norm = _normalize_prompt(base_prompt)
        base_tokens = _tokenize(base_prompt)

        ratio = SequenceMatcher(None, base_norm, prompt_norm).ratio()
        overlap = len(prompt_tokens & base_tokens) / max(len(prompt_tokens), 1)
        coherence = (0.6 * ratio + 0.4 * overlap) * (entry.get("SQI", 1.0) or 1.0)

        logger.debug(
            f"[LexMemory] Match {coherence:.2f} (ratio={ratio:.2f}, overlap={overlap:.2f}) : {base_prompt[:60]}"
        )

        if coherence > best_score:
            best_key, best_val, best_score = key, entry, coherence

    if best_key:
        answer = best_key.split("↔")[-1]
        logger.info(
            f"[LexMemory] 🔍 Top candidate ({best_score:.2f}) → {answer} "
            f"[best prompt match: {best_key.split('↔')[0][:70]}...]"
        )
        if best_score > 0.25:  # lowered threshold for higher recall sensitivity
            return {
                "prompt": prompt,
                "answer": answer,
                "resonance": best_val,
                "confidence": round(best_score, 2),
            }

    logger.debug(
        f"[LexMemory] No sufficient recall match for '{prompt}' (best={best_score:.2f})"
    )
    return {}

# ------------------------------------------------------------
# 🕒 Natural Decay
# ------------------------------------------------------------
def decay_memory(half_life_hours: float = 48.0):
    """
    Apply natural forgetting — exponential decay of resonance over time.
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
    logger.info(f"[LexMemory] Applied decay (half-life={half_life_hours}h)")

# ------------------------------------------------------------
# 🔄 Field Resonance Reinforcement Utility
# ------------------------------------------------------------
def reinforce_field(prompt: str, answer: str, resonance: Dict[str, float]):
    """
    Strengthen all related prompts that share token overlap with `prompt`.
    Used when a correct recall occurs to propagate learning through a concept field.
    """
    mem = _load_memory()
    prompt_tokens = _tokenize(prompt)
    for key, v in mem.items():
        base_prompt = key.split("↔")[0]
        base_tokens = _tokenize(base_prompt)
        overlap = len(prompt_tokens & base_tokens) / max(len(prompt_tokens), 1)
        if overlap > 0.4:  # same semantic field
            v["ρ"] = round(v["ρ"] + resonance.get("ρ", 0) * 0.05, 3)
            v["I"] = round(v["I"] + resonance.get("I", 0) * 0.05, 3)
            v["SQI"] = round(v["SQI"] + resonance.get("SQI", 0) * 0.05, 3)
            v["last_update"] = time.time()
            logger.info(f"[LexMemory] 🔄 Field resonance reinforced for '{base_prompt}'")

    _save_memory(mem)

# ------------------------------------------------------------
# 🧪 Self-Test Harness
# ------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    update_lex_memory("The sun rises in the", "east", {"ρ": 0.82, "I": 0.9, "SQI": 0.86})
    update_lex_memory("Happy", "joyful", {"ρ": 0.88, "I": 0.92, "SQI": 0.9})
    res = recall_from_memory("The sun rises in")
    print(json.dumps(res, indent=2))