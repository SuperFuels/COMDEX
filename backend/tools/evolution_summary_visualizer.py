#!/usr/bin/env python3
"""
Evolution Summary Visualizer — Phase 35.10 (Closure)
Tessaris / Aion Research Division

Combines:
 • Evolution metrics summary (fusion / decay / RSI)
 • Introspective entropy–order metrics (Phase 34)
 • concept:self_accuracy node reflection
 • PAL readiness for Phase 36
"""

import json, time, math
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────
LOG_PATH = Path("data/analysis/concept_evolution_log.jsonl")
OUT_PNG = Path("data/analysis/evolution_summary_report.png")
OUT_JSONL = Path("data/analysis/evolution_summary_report.jsonl")
METRICS_JSON = Path("data/analysis/concept_entropy_metrics.json")

# ─────────────────────────────────────────────
# Load logs
# ─────────────────────────────────────────────
records = []
if LOG_PATH.exists():
    with LOG_PATH.open() as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except Exception:
                continue
else:
    print(f"⚠️  No evolution log found at {LOG_PATH}")
    exit(0)

df = pd.DataFrame(records)
if df.empty:
    print("⚠️  No valid evolution records to summarize.")
    exit(0)

# ─────────────────────────────────────────────
# Compute summary stats
# ─────────────────────────────────────────────
total_fusions = len(df[df["event"].str.contains("fusion", na=False)])
total_reinforcements = len(df[df["event"].str.contains("reinforce", na=False)])
total_decays = len(df[df["event"].str.contains("decay", na=False)])
cooldown_events = df["event"].str.contains("cooldown", na=False).sum()

# RSI variance / stability metrics
if "mean_rsi" in df.columns:
    mean_rsi = df["mean_rsi"].mean()
    var_rsi = df["mean_rsi"].var()
else:
    mean_rsi = var_rsi = float("nan")

# Meta-accuracy = fraction of fusions with high stability
if "stability" in df.columns:
    stable_fusions = (df["stability"] >= 0.8).sum()
elif "mean_rsi" in df.columns:
    stable_fusions = (df["mean_rsi"] >= 0.8).sum()
else:
    stable_fusions = 0
meta_accuracy = round(stable_fusions / max(total_fusions, 1), 3)

summary = {
    "timestamp": time.time(),
    "total_fusions": total_fusions,
    "reinforcements": total_reinforcements,
    "decays": total_decays,
    "cooldowns": int(cooldown_events),
    "mean_rsi": round(mean_rsi, 4) if not math.isnan(mean_rsi) else None,
    "rsi_variance": round(var_rsi, 4) if not math.isnan(var_rsi) else None,
    "meta_accuracy": meta_accuracy,
}

with OUT_JSONL.open("a") as f:
    f.write(json.dumps(summary) + "\n")

# ─────────────────────────────────────────────
# Visualization
# ─────────────────────────────────────────────
plt.figure(figsize=(10,6))
plt.suptitle("Aion Concept Evolution Summary — Phase 35.9", fontsize=14, weight="bold")
plt.subplot(2,1,1)
labels = ["Fusions","Reinforcements","Decays","Cooldowns"]
values = [total_fusions,total_reinforcements,total_decays,cooldown_events]
plt.bar(labels, values)
plt.ylabel("Event Count")
plt.grid(alpha=0.3)

if "mean_rsi" in df.columns:
    plt.subplot(2,1,2)
    plt.plot(df["mean_rsi"], label="Mean RSI", linewidth=2)
    plt.axhline(y=mean_rsi, color="orange", linestyle="--", label=f"Avg RSI={mean_rsi:.3f}")
    plt.xlabel("Cycle")
    plt.ylabel("RSI")
    plt.legend()
    plt.grid(alpha=0.3)

plt.tight_layout(rect=[0,0,1,0.95])
plt.savefig(OUT_PNG, dpi=200)
plt.close()

# ─────────────────────────────────────────────
# Phase 34 — Introspective Entropy / Order Metrics
# ─────────────────────────────────────────────
def _entropy_norm(cnts):
    total = float(sum(cnts))
    if total <= 0: return 0.0
    p = [c/total for c in cnts if c>0]
    if not p: return 0.0
    H = -sum(pi*math.log(pi+1e-12) for pi in p)
    Hmax = math.log(len(p)) if len(p)>0 else 1.0
    return float(H / (Hmax or 1.0))

metrics = []
if "concept" in df.columns:
    groups = df.groupby("concept")
    for cname, g in groups:
        f = int((g["event"].str.contains("fusion", na=False)).sum())
        s = int((g["event"].str.contains("speciation", na=False)).sum())
        r = int((g["event"].str.contains("reinforce", na=False)).sum())
        d = int((g["event"].str.contains("decay", na=False)).sum())
        c = int((g["event"].str.contains("cooldown", na=False)).sum())
        ent = _entropy_norm([f,s,r,d,c])
        order = 1.0 - ent
        m_rsi = float(g["mean_rsi"].mean()) if "mean_rsi" in g else float("nan")
        acc = float(max(0.0, min(1.0, (0.0 if np.isnan(m_rsi) else m_rsi))) * order)
        metrics.append({
            "concept": cname,
            "entropy": ent,
            "order": order,
            "mean_rsi": None if np.isnan(m_rsi) else m_rsi,
            "self_accuracy_proxy": acc,
            "events": {"fusion":f,"speciation":s,"reinforce":r,"decay":d,"cooldown":c},
        })

METRICS_JSON.parent.mkdir(parents=True, exist_ok=True)
with METRICS_JSON.open("w") as f:
    json.dump({"timestamp": summary["timestamp"], "metrics": metrics}, f, indent=2)
print(f"🧮 Entropy/order metrics → {METRICS_JSON}")

# ─────────────────────────────────────────────
# Phase 35 — concept:self_accuracy node write-back
# ─────────────────────────────────────────────
try:
    from backend.modules.aion_knowledge import knowledge_graph_core as akg
    try:
        akg.update_self_accuracy("global_meta", summary.get("meta_accuracy", 0.0))
    except Exception as e:
        print(f"⚠️  Could not update global self-accuracy: {e}")

    TOP_N = 50
    metrics_sorted = sorted(metrics, key=lambda m: (m["self_accuracy_proxy"] or 0.0), reverse=True)[:TOP_N]
    for m in metrics_sorted:
        cname = m["concept"]
        val = round(float(m["self_accuracy_proxy"]), 4)
        akg.add_triplet(f"concept:{cname}", "self_accuracy", str(val))
    print(f"🧠 Wrote self_accuracy to top {len(metrics_sorted)} concepts.")
except Exception as e:
    print(f"⚠️  Could not write concept:self_accuracy nodes: {e}")

# ─────────────────────────────────────────────
# Console summary
# ─────────────────────────────────────────────
print("✅ Evolution summary complete:")
for k,v in summary.items():
    print(f"   {k:<15}: {v}")
print(f"📊 Saved visualization → {OUT_PNG}")
print(f"🧾 Summary log appended → {OUT_JSONL}")