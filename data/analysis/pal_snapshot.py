#!/usr/bin/env python3
"""
AION Snapshot Monitor (enhanced)
- Summarizes PAL memory and AKG top links
- Supports --diff, --watch N, --plot, --export-csv
"""

import argparse, json, time, os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Local imports (PAL memory + AKG)
from backend.modules.aion_perception.pal_core import MEM_PATH
from backend.modules.aion_knowledge.knowledge_graph_core import dump_summary, search

ANALYSIS_DIR = Path("data/analysis")
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = ANALYSIS_DIR / "pal_snapshots.jsonl"
CSV_PATH = ANALYSIS_DIR / "pal_snapshots.csv"
PLOT_PATH = ANALYSIS_DIR / "pal_snapshot_plot.png"

def _read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out

def _read_exemplars(mem_path: Path) -> Tuple[int, float, int, int]:
    if not mem_path.exists():
        return 0, 0.0, 0, 0
    count = 0
    rewards = []
    prompts = set()
    options = set()
    with open(mem_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                j = json.loads(line)
            except Exception:
                continue
            count += 1
            rewards.append(float(j.get("reward", 0.0)))
            prompts.add(j.get("prompt", ""))
            options.add(j.get("option", ""))
    avg_reward = (sum(rewards)/len(rewards)) if rewards else 0.0
    return count, avg_reward, len(prompts), len(options)

def _top_kg_links(top_n: int = 10) -> List[Dict[str, Any]]:
    # Pull strongest links by brute force: dump all and rank
    rows = search()  # returns list of dicts
    # sort by strength desc, take top_n
    rows.sort(key=lambda r: r.get("strength", 0.0), reverse=True)
    rows = rows[:top_n]
    # reduce payload
    keep = []
    for r in rows:
        keep.append({
            "subject": r["subject"],
            "predicate": r["predicate"],
            "object": r["object"],
            "strength": r["strength"],
        })
    return keep

def _print_snapshot(ts: str, pal_summary: dict, top_links: List[dict]):
    print(f"\n🧩 AION SNAPSHOT — {ts}")
    print(f"Exemplar count: {pal_summary['count']}")
    print(f"Average reward: {pal_summary['avg_reward']:.3f}")
    print(f"Unique prompts: {pal_summary['unique_prompts']}")
    print(f"Unique options: {pal_summary['unique_options']}\n")
    print("Top reinforced knowledge links:")
    for r in top_links:
        print(f"  {r['subject']} —[{r['predicate']}:{r['strength']:.3f}]→ {r['object']}")
    print(f"\n✅ Snapshot logged at: {LOG_PATH}")

def _diff(prev: dict, curr: dict) -> str:
    lines = []
    # PAL deltas
    pc, cc = prev["pal_summary"]["count"], curr["pal_summary"]["count"]
    pr, cr = prev["pal_summary"]["avg_reward"], curr["pal_summary"]["avg_reward"]
    lines.append(f"Δ exemplars: {cc - pc:+d} (from {pc} → {cc})")
    lines.append(f"Δ avg_reward: {cr - pr:+.3f} (from {pr:.3f} → {cr:.3f})")

    # Link deltas
    prev_links = {(x["subject"], x["predicate"], x["object"]): x["strength"] for x in prev["top_kg_links"]}
    curr_links = {(x["subject"], x["predicate"], x["object"]): x["strength"] for x in curr["top_kg_links"]}

    added = sorted(set(curr_links.keys()) - set(prev_links.keys()))
    removed = sorted(set(prev_links.keys()) - set(curr_links.keys()))
    common = sorted(set(prev_links.keys()) & set(curr_links.keys()))

    if added:
        lines.append("New links:")
        for k in added:
            s,p,o = k
            lines.append(f"  + {s} —[{p}:{curr_links[k]:.3f}]→ {o}")
    if removed:
        lines.append("Removed links:")
        for k in removed:
            s,p,o = k
            lines.append(f"  - {s} —[{p}:{prev_links[k]:.3f}]→ {o}")
    changed = [(k, prev_links[k], curr_links[k]) for k in common if abs(curr_links[k]-prev_links[k])>1e-9]
    if changed:
        lines.append("Updated strengths:")
        for k, a, b in sorted(changed, key=lambda t: abs(t[2]-t[1]), reverse=True):
            s,p,o = k
            lines.append(f"  * {s} —[{p}:{a:.3f}→{b:.3f}]→ {o}")
    if not (added or removed or changed):
        lines.append("Top link set unchanged.")

    return "\n".join(lines)

def _append_jsonl(rec: dict):
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def _write_csv(history: List[dict]):
    # headers: timestamp,count,avg_reward,unique_prompts,unique_options
    with open(CSV_PATH, "w", encoding="utf-8") as f:
        f.write("timestamp,count,avg_reward,unique_prompts,unique_options\n")
        for r in history:
            p = r["pal_summary"]
            f.write(f"{r['timestamp']},{p['count']},{p['avg_reward']:.6f},{p['unique_prompts']},{p['unique_options']}\n")

def _plot(history: List[dict]):
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("⚠️ matplotlib not available; skipping plot.")
        return
    if not history:
        return
    xs = list(range(len(history)))
    counts = [h["pal_summary"]["count"] for h in history]
    rewards = [h["pal_summary"]["avg_reward"] for h in history]

    plt.figure()
    plt.plot(xs, counts, label="Exemplar count")
    plt.plot(xs, rewards, label="Avg reward")
    plt.xlabel("Snapshot #")
    plt.ylabel("Value")
    plt.legend()
    plt.title("AION PAL Snapshot")
    plt.tight_layout()
    plt.savefig(PLOT_PATH)
    plt.close()
    print(f"📈 Plot saved → {PLOT_PATH}")

def take_snapshot(top_n: int = 10) -> dict:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    count, avg_reward, up, uo = _read_exemplars(MEM_PATH)
    top_links = _top_kg_links(top_n=top_n)
    rec = {
        "timestamp": ts,
        "pal_summary": {
            "count": count,
            "avg_reward": avg_reward,
            "unique_prompts": up,
            "unique_options": uo,
        },
        "top_kg_links": top_links
    }
    _append_jsonl(rec)
    _print_snapshot(ts, rec["pal_summary"], rec["top_kg_links"])
    return rec

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=10, help="Top-N KG links")
    ap.add_argument("--diff", action="store_true", help="Show deltas vs previous snapshot")
    ap.add_argument("--watch", type=int, default=0, help="Repeat every N seconds")
    ap.add_argument("--plot", action="store_true", help="Write PNG plot of history")
    ap.add_argument("--export-csv", action="store_true", help="Write CSV of history")
    args = ap.parse_args()

    if args.watch > 0:
        try:
            while True:
                curr = take_snapshot(top_n=args.top)
                hist = _read_jsonl(LOG_PATH)
                if args.diff and len(hist) >= 2:
                    print("\n— DIFF vs previous —")
                    print(_diff(hist[-2], hist[-1]))
                if args.export_csv:
                    _write_csv(hist)
                    print(f"🧾 CSV written → {CSV_PATH}")
                if args.plot:
                    _plot(hist)
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\n👋 stopped.")
            return

    # one-shot
    curr = take_snapshot(top_n=args.top)
    hist = _read_jsonl(LOG_PATH)
    if args.diff and len(hist) >= 2:
        print("\n— DIFF vs previous —")
        print(_diff(hist[-2], hist[-1]))
    if args.export_csv:
        _write_csv(hist)
        print(f"🧾 CSV written → {CSV_PATH}")
    if args.plot:
        _plot(hist)

if __name__ == "__main__":
    main()