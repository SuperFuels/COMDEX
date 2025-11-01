#!/usr/bin/env python3
"""
🧮 Phase 48B - Semantic Benchmark Runner
Evaluates meaning consistency (MCI) and contextual accuracy.
"""

import json, time, random
from pathlib import Path
from difflib import SequenceMatcher
from statistics import mean
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

RMC = ResonantMemoryCache()

def semantic_similarity(a, b):
    return round(SequenceMatcher(None, a.lower(), b.lower()).ratio(), 3)

def run_taskset(task_path: Path):
    data = json.loads(Path(task_path).read_text())
    results = []
    for t in data["tasks"]:
        sim = semantic_similarity(t["definition"], t["context"])
        drift = abs(t.get("I", 0.8) - t.get("ρ", 0.6))
        mci = round(sim / (1 + drift), 3)
        results.append({
            "lemma": t["lemma"],
            "sim": sim,
            "drift": drift,
            "MCI": mci,
            "SQI": t.get("SQI", 0.7)
        })

        # Update RMC entry with MCI
        entry = RMC.cache.get(t["lemma"], {})
        entry["MCI"] = mci
        RMC.cache[t["lemma"]] = entry

    RMC.save()

    summary = {
        "avg_similarity": round(mean(r["sim"] for r in results), 3),
        "avg_MCI": round(mean(r["MCI"] for r in results), 3),
        "avg_SQI": round(mean(r["SQI"] for r in results), 3),
        "count": len(results),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    return summary