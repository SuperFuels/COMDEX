# ================================================================
# ✍️ CEE Language Path - Cloze + Group Sort Generators
# ================================================================
"""
Adds advanced language exercises for the Cognitive Exercise Engine (CEE).

Implements:
  * Cloze (fill-in-the-blank) questions using LexiCoreBridge (lazy)
  * Group-Sort classification tasks (semantic grouping)

Resonance keys:
  - Use screenshot-friendly keys: {"rho","Ibar","sqi"} (preferred)
  - Back-compat accepted elsewhere: {"ρ","I","SQI"} etc.

Design:
  - No eager dataset load at import-time.
  - Bridge injection supported for callers that already hold one.
  - Avoid repeated LexiCore loads/log spam by using get_bridge() singleton.
"""

from __future__ import annotations

import time
import random
import logging
from typing import Dict, List, Optional

from backend.modules.aion_cognition.cee_lexicore_bridge import get_bridge, LexiCoreBridge

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
def _resonance() -> Dict[str, float]:
    """Generate synthetic resonance parameters for testing."""
    rho = round(random.uniform(0.6, 0.9), 3)
    Ibar = round(random.uniform(0.8, 1.0), 3)
    sqi = round((rho + Ibar) / 2.0, 3)
    return {"rho": rho, "Ibar": Ibar, "sqi": sqi}


def _safe_blank(sentence: str, missing_word: str) -> str:
    """
    Replace missing_word with "_____" (safe even if exact token not present).
    Prefer whole-word-ish replacement; otherwise append placeholder.
    """
    s = (sentence or "").strip()
    mw = (missing_word or "").strip()
    if not s:
        return "_____"
    if mw and mw in s:
        return s.replace(mw, "_____")
    # fallback: if sentence already has blank marker, keep it
    if "_____" in s or "___" in s:
        return s
    # last resort: tack on blank
    return f"{s} _____"


def _pick_distractors(pool: List[str], k: int, banned: set[str]) -> List[str]:
    pool2: List[str] = []
    for w in pool:
        if not w:
            continue
        ws = str(w).strip()
        if not ws:
            continue
        if ws.lower() in banned:
            continue
        pool2.append(ws)

    # de-dupe while preserving some variety
    pool2 = list(dict.fromkeys(pool2))
    if not pool2 or k <= 0:
        return []

    if len(pool2) <= k:
        return pool2
    return random.sample(pool2, k=k)

# ------------------------------------------------------------
def generate_cloze(
    sentence: str,
    missing_word: str,
    bridge: Optional[LexiCoreBridge] = None,
    distractor_k: int = 3,
) -> Dict:
    """
    Generate a cloze (fill-in-the-blank) exercise.
    Always includes `missing_word` in options.
    If LexiCore/ThesauriNet are unavailable, falls back to default distractors.

    IMPORTANT:
      - If caller passes a bridge, we use it (no reload).
      - Otherwise we use get_bridge() singleton.
    """
    mw = (missing_word or "").strip()
    if not mw:
        mw = "_____"

    # Lazy bridge by default (no import-time load; avoids repeated loads)
    b = bridge if bridge is not None else get_bridge()

    syns: List[str] = []
    ants: List[str] = []
    rels: List[str] = []
    try:
        syns = b.get_synonyms(mw) or []
        ants = b.get_antonyms(mw) or []
        rels = b.get_related(mw) or []
    except Exception as e:
        logger.debug(f"[CEE-Cloze] bridge lookup failed (non-fatal): {e}")

    fallback = [
        "dark", "bright", "fast", "slow",
        "east", "west", "north", "south",
        "violin", "drum", "guitar", "piano",
        "degrees", "meters", "seconds", "frequency",
    ]

    banned = {mw.lower()}
    pool = list({*(syns or []), *(ants or []), *(rels or []), *fallback})
    distractors = _pick_distractors(pool, k=int(distractor_k), banned=banned)

    # Ensure answer is present and unique (case-insensitive)
    options: List[str] = [mw]
    seen = {mw.lower()}
    for d in distractors:
        dl = d.lower()
        if dl not in seen:
            options.append(d)
            seen.add(dl)

    random.shuffle(options)

    return {
        "type": "cloze",
        "prompt": _safe_blank(sentence, missing_word),
        "options": options,
        "answer": mw,
        "resonance": _resonance(),
        "timestamp": time.time(),
    }

# ------------------------------------------------------------
def generate_group_sort(groups: Dict[str, List[str]]) -> Dict:
    """
    Generate a Group-Sort exercise:
      Input: {"Fruits": ["apple", "pear"], "Animals": ["dog", "cat"]}
      Output: exercise with randomized items and labeled groups.
    """
    g = groups or {}

    # sanitize + de-dupe items within each group
    clean_groups: Dict[str, List[str]] = {}
    for k, words in g.items():
        key = str(k).strip()
        if not key:
            continue
        ws: List[str] = []
        seen = set()
        for w in (words or []):
            w2 = str(w).strip()
            if not w2:
                continue
            wl = w2.lower()
            if wl in seen:
                continue
            ws.append(w2)
            seen.add(wl)
        if ws:
            clean_groups[key] = ws

    items = [(word, group) for group, words in clean_groups.items() for word in words]
    random.shuffle(items)

    return {
        "type": "group_sort",
        "prompt": "Sort the words into their correct categories.",
        "groups": list(clean_groups.keys()),
        "items": [w for w, _ in items],
        "answer": {gk: gv for gk, gv in clean_groups.items()},
        "resonance": _resonance(),
        "timestamp": time.time(),
    }

# ------------------------------------------------------------
# CLI smoke-test
# ------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Cloze example
    c = generate_cloze("The sun rises in the east.", "east")
    print(c)

    # Group-Sort example
    g = generate_group_sort(
        {
            "Fruits": ["apple", "pear", "banana"],
            "Animals": ["dog", "cat", "bird"],
        }
    )
    print(g)