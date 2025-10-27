#!/usr/bin/env python3
"""
🌐 AION Advanced Cognition — Lexical Task Generator
──────────────────────────────────────────────────
Generates semantic reasoning tasks directly from LexMemory.
Used by the Advanced Cognition Loop to teach AION real-word understanding.

Output → data/tasks/advanced_cognition/tasks_cycle<N>.json
"""

import json, random, time, logging
from pathlib import Path
from backend.modules.aion_cognition.cee_lex_memory import recall_from_memory
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

log = logging.getLogger(__name__)

TASK_PATH = Path("data/tasks/advanced_cognition")
TASK_PATH.mkdir(parents=True, exist_ok=True)

RMC = ResonantMemoryCache()

# ------------------------------------------------------------
def _make_anagram(word: str) -> str:
    chars = list(word)
    random.shuffle(chars)
    return "".join(chars)

def _make_choices(correct: str, pool: list, k: int = 3):
    distractors = random.sample([p for p in pool if p != correct], min(k, len(pool)-1))
    return random.sample(distractors + [correct], len(distractors)+1)

def generate_tasks(cycle: int = 1, limit: int = 150):
    """Build a suite of cognitive tasks from LexMemory and RMC."""
    # Collect lemmas from RMC (filter short/non-alpha)
    lemmas = [
        k for k in getattr(RMC, "cache", {}).keys()
        if isinstance(k, str) and k.isascii() and k.isalpha() and len(k) >= 3
    ]
    if not lemmas:
        log.warning("[LCE] ⚠ No lemmas available in RMC cache.")
        lemmas = ["photon", "wave", "field", "energy", "resonance"]

    chosen = random.sample(lemmas, min(limit, len(lemmas)))
    tasks = []

    for i, lemma in enumerate(chosen):
        # Prefer LexMemory recall; fall back to any stored RMC definition
        mem = recall_from_memory(lemma) or {}
        definition = (
            mem.get("answer")
            or mem.get("definition")
            or (RMC.lookup(lemma) or {}).get("definition", "")
        )

        if not isinstance(definition, str) or not definition.strip():
            continue

        ttype = random.choice(["definition_match", "synonym_choice", "anagram", "completion"])
        task = {"id": f"task_{cycle:02d}_{i:04d}", "lemma": lemma, "type": ttype}

        if ttype == "definition_match":
            task["definition"] = definition
            task["choices"] = _make_choices(lemma, chosen)

        elif ttype == "synonym_choice":
            task["prompt"] = f"Select the closest meaning to '{lemma}'"
            # Use choices drawn from lemma pool; first is the correct lemma
            task["choices"] = _make_choices(lemma, chosen)

        elif ttype == "anagram":
            ana = _make_anagram(lemma)
            # ensure the anagram is not identical to the lemma (rare for short words)
            if ana == lemma and len(lemma) > 3:
                ana = _make_anagram(lemma)
            task["anagram"] = ana
            task["target"] = lemma

        elif ttype == "completion":
            # Use first sentence/phrase of the definition as the target
            first_clause = definition.split(".", 1)[0].strip()
            task["prompt"] = f"{lemma.capitalize()} is..."
            task["definition"] = first_clause

        tasks.append(task)

    # 🔁 Fallback if none generated
    if not tasks:
        log.warning("[LCE] ⚠ No tasks generated — inserting default lexical seeds.")
        tasks = [
            {
                "id": f"task_{cycle:02d}_seed_01",
                "lemma": "photon",
                "type": "definition_match",
                "definition": "a quantum of light",
                "choices": ["photon", "electron", "wave", "field"],
            },
            {
                "id": f"task_{cycle:02d}_seed_02",
                "lemma": "wave",
                "type": "completion",
                "prompt": "Wave is...",
                "definition": "an oscillation transferring energy",
            },
            {
                "id": f"task_{cycle:02d}_seed_03",
                "lemma": "field",
                "type": "anagram",
                "anagram": "dleif",
                "target": "field",
            },
        ]

    # 🧾 Write tasks to disk
    out = TASK_PATH / f"tasks_cycle{cycle}.json"
    out.write_text(json.dumps({"cycle": cycle, "timestamp": time.time(), "tasks": tasks}, indent=2))
    log.info(f"[LCE] 🧩 Generated {len(tasks)} tasks → {out}")
    return {"count": len(tasks), "path": str(out)}