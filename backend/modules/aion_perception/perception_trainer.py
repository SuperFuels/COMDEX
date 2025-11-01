#!/usr/bin/env python3
"""
Terminal trainer for PAL.
Usage examples:

# quick built-in shapes curriculum, 60 episodes
PYTHONPATH=. python backend/modules/aion_perception/perception_trainer.py --episodes 60

# custom curriculum JSONL
PYTHONPATH=. python backend/modules/aion_perception/perception_trainer.py \
  --episodes 100 \
  --curriculum data/curriculum/perception_shapes.jsonl

# interactive single-prompt spot checks
PYTHONPATH=. python backend/modules/aion_perception/perception_trainer.py --interactive
"""

import argparse, json, random, time
from pathlib import Path
from pal_core import PAL  # same folder

DEFAULT_CURR = [
    {"prompt":"select the square",   "options":["■","●","▲"], "answer":"■"},
    {"prompt":"select the circle",   "options":["●","■","▲"], "answer":"●"},
    {"prompt":"select the triangle", "options":["▲","●","■"], "answer":"▲"},
]

def load_curriculum(path: Path):
    if not path or not path.exists():
        return DEFAULT_CURR
    items = []
    for ln in path.read_text().strip().splitlines():
        try:
            items.append(json.loads(ln))
        except Exception:
            continue
    return items or DEFAULT_CURR

def run_batch(episodes: int, curriculum):
    pal = PAL()
    pal.load()
    correct = 0
    history = []

    print("🎯 Starting PAL trainer")
    print(f"   memory={len(pal.memory)} k={pal.k} ε={pal.epsilon:.2f}")

    for i in range(1, episodes+1):
        item = random.choice(curriculum)
        prompt = item["prompt"]; opts = item["options"]; ans = item["answer"]
        choice, conf, vec = pal.ask(prompt, opts)
        reward = 1.0 if choice == ans else 0.0
        pal.feedback(prompt, choice, ans, vec, reward)
        correct += (1 if reward > 0 else 0)
        acc = correct / i

        print(f"[{i:03d}] {prompt} | opts={opts} | chose={choice} (p≈{conf:.2f}) "
              f"| {'✅' if reward>0 else '❌'} | acc={acc:.2f} | mem={len(pal.memory)} ε={pal.epsilon:.2f}")

        history.append({"i":i,"acc":acc,"choice":choice,"ans":ans,"conf":conf})

        # small sleep so RAL can update between steps (optional)
        time.sleep(0.15)

    # write metrics
    out = Path("data/perception/metrics.jsonl"); out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "a") as f:
        for h in history: f.write(json.dumps(h) + "\n")
    print("📝 metrics appended ->", out)

def run_interactive():
    pal = PAL(); pal.load()
    print("🧪 Interactive mode. Ctrl+C to exit.")
    while True:
        prompt = input("Prompt: ").strip()
        opts = input("Options (comma-separated): ").strip().split(",")
        opts = [o.strip() for o in opts if o.strip()]
        ans  = input("Correct option exactly (must match one option): ").strip()
        choice, conf, vec = pal.ask(prompt, opts)
        print(f"-> PAL chose: {choice} (p≈{conf:.2f})")
        reward = 1.0 if choice == ans else 0.0
        pal.feedback(prompt, choice, ans, vec, reward)
        print(f"   {'✅ correct' if reward>0 else '❌ incorrect'} | mem={len(pal.memory)} ε={pal.epsilon:.2f}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=60)
    ap.add_argument("--curriculum", type=Path, default=None)
    ap.add_argument("--interactive", action="store_true")
    args = ap.parse_args()

    if args.interactive:
        run_interactive()
    else:
        curriculum = load_curriculum(args.curriculum) if args.curriculum else DEFAULT_CURR
        run_batch(args.episodes, curriculum)

if __name__ == "__main__":
    main()