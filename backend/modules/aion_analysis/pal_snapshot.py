#!/usr/bin/env python3
"""
Aion Perceptual Snapshot Monitor (Phase 30+)
───────────────────────────────────────────────
Provides a visual + textual summary of Aion's cognitive growth:
    * PAL learning accuracy across self-tune rounds
    * Exploration parameter (ε) decay
    * Knowledge Graph reinforcement statistics
    * Exemplar memory count and distribution
Outputs:
    - Console summary
    - Plot (accuracy / ε over rounds)
    - JSONL snapshot record for longitudinal tracking
"""

import json, time, sqlite3, matplotlib.pyplot as plt
from pathlib import Path
from statistics import mean

# Paths
DATA_DIR = Path("data")
PAL_FILE = DATA_DIR / "perception" / "exemplars.jsonl"
KG_DB = DATA_DIR / "knowledge" / "aion_knowledge_graph.db"
SNAPSHOT_LOG = DATA_DIR / "analysis" / "pal_snapshots.jsonl"
SNAPSHOT_LOG.parent.mkdir(parents=True, exist_ok=True)

def read_pal_memory():
    """Load PAL exemplars for summary."""
    exemplars = []
    if PAL_FILE.exists():
        with open(PAL_FILE) as f:
            for line in f:
                try:
                    exemplars.append(json.loads(line))
                except Exception:
                    pass
    return exemplars

def read_knowledge_graph():
    """Load top triplets and reinforcement data."""
    conn = sqlite3.connect(KG_DB)
    cur = conn.execute(
        "SELECT subject,predicate,object,strength FROM knowledge ORDER BY strength DESC LIMIT 20"
    )
    data = cur.fetchall()
    conn.close()
    return [{"subject": s, "predicate": p, "object": o, "strength": w} for s,p,o,w in data]

def summarize_pal(exemplars):
    """Summarize memory content."""
    if not exemplars:
        return {"count": 0, "avg_reward": 0.0}
    rewards = [e.get("reward", 0.0) for e in exemplars]
    prompts = list({e.get("prompt") for e in exemplars})
    options = list({e.get("option") for e in exemplars})
    return {
        "count": len(exemplars),
        "avg_reward": mean(rewards),
        "unique_prompts": len(prompts),
        "unique_options": len(options),
    }

def plot_progress(log_entries):
    """Plot accuracy and ε trends."""
    rounds = list(range(1, len(log_entries) + 1))
    acc = [e["accuracy"] for e in log_entries]
    eps = [e["epsilon"] for e in log_entries]

    fig, ax1 = plt.subplots()
    ax1.set_xlabel("Rounds")
    ax1.set_ylabel("Accuracy", color="black")
    ax1.plot(rounds, acc, marker="o", label="Accuracy", color="black")
    ax1.tick_params(axis='y', labelcolor='black')

    ax2 = ax1.twinx()
    ax2.set_ylabel("Epsilon (exploration)", color="gray")
    ax2.plot(rounds, eps, marker="x", linestyle="--", color="gray", label="ε")

    fig.tight_layout()
    plt.title("Aion PAL Learning Dynamics")
    plt.savefig("data/analysis/pal_snapshot_plot.png", dpi=300)
    print("📊 Plot saved -> data/analysis/pal_snapshot_plot.png")

def create_snapshot():
    """Main entrypoint: summarize current Aion state."""
    ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    exemplars = read_pal_memory()
    kg_data = read_knowledge_graph()
    pal_summary = summarize_pal(exemplars)

    snapshot = {
        "timestamp": ts,
        "pal_summary": pal_summary,
        "top_kg_links": kg_data[:10],
    }

    with open(SNAPSHOT_LOG, "a") as f:
        f.write(json.dumps(snapshot) + "\n")

    print("\n🧩 AION SNAPSHOT -", ts)
    print(f"Exemplar count: {pal_summary['count']}")
    print(f"Average reward: {pal_summary['avg_reward']:.3f}")
    print(f"Unique prompts: {pal_summary['unique_prompts']}")
    print(f"Unique options: {pal_summary['unique_options']}")
    print("\nTop reinforced knowledge links:")
    for entry in kg_data[:10]:
        print(f"  {entry['subject']} -[{entry['predicate']}:{entry['strength']:.3f}]-> {entry['object']}")

    print("\n✅ Snapshot logged at:", SNAPSHOT_LOG)
    return snapshot

if __name__ == "__main__":
    # Optional: if a run log exists, visualize
    LOG_PATH = Path("data/analysis/pal_training_log.jsonl")
    if LOG_PATH.exists():
        with open(LOG_PATH) as f:
            rounds = [json.loads(l) for l in f]
        plot_progress(rounds)

    # Always take a fresh snapshot
    snapshot = create_snapshot()