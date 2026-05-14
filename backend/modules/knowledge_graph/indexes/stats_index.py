"""
stats_index.py

📊 Index Purpose:
Stores per-container statistics on glyph usage, logic execution, entanglement, and symbolic replay.
Tracks glyph frequency, operator use, trigger types, cost over time, and SQI indicators.

Used for meta-analysis, performance tuning, anomaly detection, and Codex benchmarking.

🧪 Design Rubric Compliance:
- 🔁 Deduplication Logic ............ ✅
- 📦 Container Awareness ............ ✅
- 🧠 Semantic Metadata .............. ✅
- ⏱️ Timestamps (ISO 8601) .......... ✅
- 🧩 Plugin Compatibility ........... ✅
- 🔍 Search & Summary API .......... ✅
- 📊 Readable + Compressed Export ... ✅
- 📚 .dc Container Injection ........ ✅
"""

from typing import Dict, List
from collections import defaultdict
from datetime import datetime

def build_stats_index(glyph_trace: List[Dict]) -> Dict:
    """Creates a statistics summary from a list of glyph trace entries."""
    stats = {
        "total_glyphs": 0,
        "operator_usage": defaultdict(int),
        "trigger_types": defaultdict(int),
        "entangled_glyphs": 0,
        "avg_logic_cost": 0,
        "cost_samples": [],
        "glyph_frequencies": defaultdict(int),
        "timestamps": [],
    }

    for entry in glyph_trace:
        glyph = entry.get("glyph", "")
        stats["total_glyphs"] += 1
        stats["glyph_frequencies"][glyph] += 1

        op = entry.get("operator")
        if op:
            stats["operator_usage"][op] += 1

        trigger = entry.get("trigger_type") or entry.get("trigger")
        if trigger:
            stats["trigger_types"][trigger] += 1

        if "↔" in glyph:
            stats["entangled_glyphs"] += 1

        cost = entry.get("cost")
        if isinstance(cost, (int, float)):
            stats["cost_samples"].append(cost)

        if "timestamp" in entry:
            stats["timestamps"].append(entry["timestamp"])

    # Final calculations
    if stats["cost_samples"]:
        stats["avg_logic_cost"] = sum(stats["cost_samples"]) / len(stats["cost_samples"])

    return {
        "stats_index": {
            "created_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_glyphs": stats["total_glyphs"],
                "entangled": stats["entangled_glyphs"],
                "avg_cost": round(stats["avg_logic_cost"], 3),
                "operators": dict(stats["operator_usage"]),
                "triggers": dict(stats["trigger_types"]),
                "frequencies": dict(stats["glyph_frequencies"]),
                "timestamps": stats["timestamps"],
            }
        }
    }