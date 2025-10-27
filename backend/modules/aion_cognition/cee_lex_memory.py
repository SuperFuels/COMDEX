#!/usr/bin/env python3
# ================================================================
# 🧠 CEE LexMemory — Resonant Knowledge Reinforcement Engine
# Phase 45G.13 — Atomic Persistent Symbolic Resonance Memory
# ================================================================
"""
Stores and recalls resonance-weighted associations learned during
language and reasoning exercises.  All writes are atomic and validated
to prevent corruption.

Memory file:
    data/memory/lex_memory.json
"""

import json, logging, time, math, os, re, tempfile
from pathlib import Path
from typing import Dict, Any
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MEMORY_PATH = Path("data/memory/lex_memory.json")
MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)

# ================================================================
# 🧩 Auto-Recovery Bootstrap — Phase 45G.14
# ================================================================
def _auto_recover_json(path: Path, fallback: dict = None):
    """
    Auto-repair loader for JSON memory files.
    - If file is missing → create new.
    - If file corrupt → move to .corrupt + restore from .bak or recreate clean.
    """
    fallback = fallback or {}
    if not path.exists():
        logger.warning(f"[Recovery] Missing {path.name}, creating new.")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fallback, f, indent=2)
        return fallback

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[Recovery] ⚠ Corruption in {path.name}: {e}")
        corrupt = path.with_suffix(".corrupt")
        backup = path.with_suffix(".bak")

        try:
            os.replace(path, corrupt)
            logger.warning(f"[Recovery] Renamed bad file → {corrupt}")
        except Exception:
            pass

        if backup.exists():
            logger.info(f"[Recovery] Restoring from backup → {backup}")
            data = json.loads(backup.read_text(encoding="utf-8"))
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return data

        logger.warning(f"[Recovery] No backup found; creating clean file.")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fallback, f, indent=2)
        return fallback

# ================================================================
# 🧩 Safe I/O Utilities
# ================================================================
def _atomic_write_json(path: Path, data: dict):
    """Safely write JSON with validation before replacing the original."""
    tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, suffix=".tmp")
    json.dump(data, tmp, indent=2)
    tmp.flush(); os.fsync(tmp.fileno()); tmp.close()
    try:
        json.loads(Path(tmp.name).read_text(encoding="utf-8"))
        os.replace(tmp.name, path)
        logger.info(f"[LexMemory] ✅ Atomic save verified → {path}")
    except Exception as e:
        logger.error(f"[LexMemory] ❌ Validation failed, aborting write: {e}")
        os.unlink(tmp.name)
        raise

def _safe_val(v):
    """Convert unsupported types into JSON-serializable primitives."""
    if isinstance(v, (int, float, str, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_safe_val(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _safe_val(val) for k, val in v.items()}
    return str(v)

# ================================================================
# 🧠 Memory Load / Save
# ================================================================
def _load_memory() -> Dict[str, Any]:
    """
    Safely load LexMemory from disk.
    - If file missing → create new.
    - If corrupted → move to .corrupt, restore from .bak if available.
    - Always returns a valid dict.
    """
    if not MEMORY_PATH.exists():
        logger.warning(f"[LexMemory] Missing {MEMORY_PATH.name}, creating new.")
        MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
        return {}

    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[LexMemory] ⚠ Corrupted file detected: {e}")
        corrupt = MEMORY_PATH.with_suffix(".corrupt")
        backup = MEMORY_PATH.with_suffix(".bak")

        try:
            os.replace(MEMORY_PATH, corrupt)
            logger.warning(f"[LexMemory] Renamed bad file → {corrupt}")
        except Exception:
            pass

        if backup.exists():
            try:
                data = json.loads(backup.read_text(encoding="utf-8"))
                with open(MEMORY_PATH, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                logger.info(f"[LexMemory] ✅ Restored from backup → {backup}")
                return data
            except Exception as e2:
                logger.warning(f"[LexMemory] Backup restore failed: {e2}")

        logger.warning(f"[LexMemory] No usable backup found; reinitializing.")
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
        return {}

def _save_memory(data: Dict[str, Any]):
    """Persist memory atomically."""
    _atomic_write_json(MEMORY_PATH, _safe_val(data))

def _make_key(prompt: str, answer: str) -> str:
    return f"{prompt.strip()}↔{answer.strip()}"

# ================================================================
# 🔁 Update / Reinforcement
# ================================================================
def update_lex_memory(prompt: str, answer: str, resonance: Dict[str, float]):
    mem = _load_memory()
    key = _make_key(prompt, answer)
    entry = mem.get(key, {"ρ": 0.0, "I": 0.0, "SQI": 0.0, "count": 0, "last_update": 0})
    α = 0.35
    entry["ρ"] = round(entry["ρ"] * (1 - α) + resonance.get("ρ", 0) * α, 3)
    entry["I"] = round(entry["I"] * (1 - α) + resonance.get("I", 0) * α, 3)
    entry["SQI"] = round(entry["SQI"] * (1 - α) + resonance.get("SQI", 0) * α, 3)
    entry["count"] += 1
    entry["last_update"] = time.time()
    mem[key] = entry
    _save_memory(mem)
    logger.info(f"[LexMemory] Reinforced {key} → SQI={entry['SQI']}, count={entry['count']}")

# ================================================================
# 🧩 Concept-Level Storage for Direct Recall
# ================================================================
def store_concept_definition(term: str, definition: str, resonance: Dict[str, float]):
    """
    Store a simple term ↔ definition pair for direct lookup.
    Used during 'teach' sessions to enable definition recall.
    """
    mem = _load_memory()
    key = _make_key(term, definition)
    entry = {
        "ρ": resonance.get("ρ", 0.75),
        "I": resonance.get("I", 0.8),
        "SQI": resonance.get("SQI", 0.85),
        "count": 1,
        "last_update": time.time()
    }
    mem[key] = entry
    _save_memory(mem)
    logger.info(f"[LexMemory] 📘 Stored concept '{term}' → '{definition}'")

# ================================================================
# 🔍 Field-Coherent Recall
# ================================================================
def _normalize_prompt(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text)

def _tokenize(text: str) -> set:
    return set(_normalize_prompt(text).split())

def recall_from_memory(prompt: str) -> Dict[str, Any]:
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
        if coherence > best_score:
            best_key, best_val, best_score = key, entry, coherence

    if best_key:
        answer = best_key.split("↔")[-1]
        logger.info(f"[LexMemory] 🔍 Top candidate ({best_score:.2f}) → {answer}")
        if best_score > 0.25:
            return {"prompt": prompt, "answer": answer, "resonance": best_val, "confidence": round(best_score, 2)}

    return {}

# ================================================================
# 🕒 Natural Decay
# ================================================================
def decay_memory(half_life_hours: float = 48.0):
    mem = _load_memory()
    now = time.time()
    decay_rate = math.log(2) / (half_life_hours * 3600)
    for k, v in mem.items():
        age = now - v.get("last_update", now)
        factor = math.exp(-decay_rate * age)
        v["ρ"] = round(v.get("ρ", 0) * factor, 3)
        v["I"] = round(v.get("I", 0) * factor, 3)
        v["SQI"] = round(v.get("SQI", 0) * factor, 3)
    _save_memory(mem)
    logger.info(f"[LexMemory] Applied decay (half-life={half_life_hours}h)")

# ================================================================
# 🔄 Field Resonance Reinforcement
# ================================================================
def reinforce_field(prompt: str, answer: str, resonance: Dict[str, float]):
    mem = _load_memory()
    prompt_tokens = _tokenize(prompt)
    for key, v in mem.items():
        base_prompt = key.split("↔")[0]
        base_tokens = _tokenize(base_prompt)
        overlap = len(prompt_tokens & base_tokens) / max(len(prompt_tokens), 1)
        if overlap > 0.4:
            v["ρ"] = round(v.get("ρ", 0) + resonance.get("ρ", 0) * 0.05, 3)
            v["I"] = round(v.get("I", 0) + resonance.get("I", 0) * 0.05, 3)
            v["SQI"] = round(v.get("SQI", 0) + resonance.get("SQI", 0) * 0.05, 3)
            v["last_update"] = time.time()
            logger.info(f"[LexMemory] 🔄 Field resonance reinforced for '{base_prompt}'")
    _save_memory(mem)

# ================================================================
# 🧪 Self-Test
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    update_lex_memory("The sun rises in the", "east", {"ρ": 0.82, "I": 0.9, "SQI": 0.86})
    update_lex_memory("Happy", "joyful", {"ρ": 0.88, "I": 0.92, "SQI": 0.9})
    res = recall_from_memory("The sun rises in")
    print(json.dumps(res, indent=2))