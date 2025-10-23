#!/usr/bin/env python3
"""
PAL Adaptation Tool — Phase 35.10 (Closure)
Tessaris / Aion Research Division

Reflects entropy–order metrics and meta-accuracy into
PAL (Perception–Action Loop) configuration parameters.

If no concept-level metrics are found, synthesizes a
fallback reflection from latest evolution summary.
"""

import json
import time
import math
from pathlib import Path

METRICS_JSON = Path("data/analysis/concept_entropy_metrics.json")
SUMMARY_JSONL = Path("data/analysis/evolution_summary_report.jsonl")
OUT_JSON = Path("data/feedback/pal_config.json")

# ─────────────────────────────────────────────
# Load entropy metrics
# ─────────────────────────────────────────────
metrics = []
if METRICS_JSON.exists():
    with METRICS_JSON.open() as f:
        try:
            data = json.load(f)
            metrics = data.get("metrics", [])
        except Exception:
            print(f"⚠️  Could not parse {METRICS_JSON}, continuing.")
else:
    print(f"⚠️  Missing entropy metrics file: {METRICS_JSON}")

# ─────────────────────────────────────────────
# Fallback synthesis from evolution summary
# ─────────────────────────────────────────────
if not metrics:
    print("ℹ️  Synthesizing fallback metric from evolution summary...")
    mean_order = 0.7
    mean_entropy = 0.3
    mean_acc = 0.5

    if SUMMARY_JSONL.exists():
        try:
            with SUMMARY_JSONL.open() as f:
                last_line = [l for l in f if l.strip()][-1]
                summary = json.loads(last_line)
                mean_acc = summary.get("meta_accuracy", 0.5)
        except Exception:
            pass

    metrics = [{
        "concept": "global_meta",
        "order": mean_order,
        "entropy": mean_entropy,
        "self_accuracy_proxy": mean_acc,
        "events": {"fusion": 0, "reinforce": 0, "decay": 0, "cooldown": 0}
    }]

# ─────────────────────────────────────────────
# Compute reflective statistics
# ─────────────────────────────────────────────
orders = [m["order"] for m in metrics if m.get("order") is not None]
entropies = [m["entropy"] for m in metrics if m.get("entropy") is not None]
accuracies = [m["self_accuracy_proxy"] for m in metrics if m.get("self_accuracy_proxy") is not None]

mean_order = sum(orders) / len(orders)
mean_entropy = sum(entropies) / len(entropies)
mean_acc = sum(accuracies) / len(accuracies)

# Adaptive reflection logic
epsilon = round(max(0.05, min(0.9, 0.5 + (mean_entropy - mean_order))), 3)
gain_k = round(max(0.1, min(2.0, 1.0 + (mean_acc - 0.5))), 3)

pal_cfg = {
    "timestamp": time.time(),
    "mean_order": mean_order,
    "mean_entropy": mean_entropy,
    "mean_self_accuracy": mean_acc,
    "epsilon": epsilon,
    "gain_k": gain_k,
}

# ─────────────────────────────────────────────
# Save PAL reflection
# ─────────────────────────────────────────────
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
with OUT_JSON.open("w") as f:
    json.dump(pal_cfg, f, indent=2)

print(f"✅ PAL reflection written → {OUT_JSON}")
print(json.dumps(pal_cfg, indent=2))

# ─────────────────────────────────────────────
# Update AKG reflection node
# ─────────────────────────────────────────────
try:
    from backend.modules.aion_knowledge import knowledge_graph_core as akg
    akg.add_triplet("system:PAL", "reflection_order", str(round(mean_order, 4)))
    akg.add_triplet("system:PAL", "reflection_entropy", str(round(mean_entropy, 4)))
    akg.add_triplet("system:PAL", "exploration_epsilon", str(epsilon))
    akg.add_triplet("system:PAL", "gain_k", str(gain_k))
    print("🧠 PAL reflection values written into AKG.")
except Exception as e:
    print(f"⚠️  Could not update AKG: {e}")