#!/usr/bin/env python3
"""
📘 Phase 48B — Semantic Comprehension Benchmark
Generates comprehension tasks from AION LexMemory + RMC cache.
"""

import json, random, time
from pathlib import Path
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

OUT_DIR = Path("data/benchmarks")
OUT_DIR.mkdir(parents=True, exist_ok=True)
RMC = ResonantMemoryCache()

def generate_tasks(sample_size: int = 100, cycle: int = 0):
    lemmas = [k for k in RMC.cache.keys() if isinstance(k, str)]
    chosen = random.sample(lemmas, min(sample_size, len(lemmas)))
    tasks = []

    for lemma in chosen:
        entry = RMC.cache.get(lemma, {})
        definition = entry.get("definition", lemma.replace("_", " "))
        context = f"{lemma} used in context: {definition}"
        tasks.append({
            "lemma": lemma,
            "definition": definition,
            "context": context,
            "ρ": entry.get("ρ", 0.6),
            "I": entry.get("I", 0.8),
            "SQI": entry.get("SQI", 0.7),
        })

    path = OUT_DIR / f"semantic_tasks_cycle{cycle}.json"
    path.write_text(json.dumps({"cycle": cycle, "tasks": tasks}, indent=2))
    return {"path": str(path), "count": len(tasks)}