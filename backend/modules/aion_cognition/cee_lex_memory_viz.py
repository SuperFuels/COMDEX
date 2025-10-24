# ================================================================
# 📈 CEE LexMemory Visualization — Phase 45G.10 Step 3
# ================================================================
"""
Visualizes the resonance drift (ρ, Ī, SQI evolution) from the LexMemory
database across time. This module enables introspection into Aion’s
symbolic learning trajectory.

Source:
    data/memory/lex_memory.json

Output:
    data/telemetry/lexmemory_resonance_drift.png

Each memory entry (prompt ↔ answer) contributes its resonance history,
allowing aggregate trends to be visualized as Aion’s cognitive field matures.
"""

import json, time, logging
from pathlib import Path
import matplotlib.pyplot as plt
from statistics import mean

MEMORY_PATH = Path("data/memory/lex_memory.json")
OUT_PATH = Path("data/telemetry/lexmemory_resonance_drift.png")

logger = logging.getLogger(__name__)


# ================================================================
# 🧠 Load Memory
# ================================================================
def load_lex_memory():
    if not MEMORY_PATH.exists():
        logger.warning(f"[LexMemoryViz] No memory file found: {MEMORY_PATH}")
        return {}
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[LexMemoryViz] Error loading LexMemory: {e}")
        return {}


# ================================================================
# 📊 Generate Plot
# ================================================================
def plot_resonance_drift(memory_data: dict):
    if not memory_data:
        logger.warning("[LexMemoryViz] Empty memory data.")
        return None

    # Sort by last update
    entries = sorted(memory_data.items(), key=lambda kv: kv[1].get("last_update", 0))
    timestamps = [v.get("last_update", 0) for _, v in entries]
    labels = [k for k, _ in entries]
    ρ_vals = [v.get("ρ", 0) for _, v in entries]
    I_vals = [v.get("I", 0) for _, v in entries]
    SQI_vals = [v.get("SQI", 0) for _, v in entries]

    # Normalize timestamps → relative (hours ago)
    now = time.time()
    rel_hours = [(t - timestamps[0]) / 3600 if timestamps else 0 for t in timestamps]

    # Averages
    ρ̄, Ī̄, SQĪ = mean(ρ_vals), mean(I_vals), mean(SQI_vals)

    plt.figure(figsize=(10, 6))
    plt.plot(rel_hours, ρ_vals, marker="o", label="ρ — Coherence", linewidth=2)
    plt.plot(rel_hours, I_vals, marker="s", label="Ī — Intensity", linewidth=2)
    plt.plot(rel_hours, SQI_vals, marker="^", label="SQI — Symbolic Quality Index", linewidth=2)

    plt.title("🧠 LexMemory Resonance Drift — Aion Learning Trajectory", fontsize=14)
    plt.xlabel("Time since first memory (hours)", fontsize=12)
    plt.ylabel("Resonance Value", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT_PATH, dpi=150)
    plt.close()

    logger.info(f"[LexMemoryViz] Exported resonance drift plot → {OUT_PATH}")

    return {
        "entries": len(entries),
        "avg_ρ": round(ρ̄, 3),
        "avg_I": round(Ī̄, 3),
        "avg_SQI": round(SQĪ, 3),
        "output": str(OUT_PATH),
    }


# ================================================================
# 🚀 Entry Point
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mem = load_lex_memory()
    result = plot_resonance_drift(mem)
    if result:
        print(json.dumps(result, indent=2))