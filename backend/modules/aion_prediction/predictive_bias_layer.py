#!/usr/bin/env python3
"""
AION Phase 31 — Predictive Bias Layer
───────────────────────────────────────────────
Learns short-term temporal transitions between perceptual events.
Builds a Markov-style model predicting next glyph or concept.
Feeds predictions back into PAL for resonance feedback / reinforcement.

Inputs:
  data/analysis/pal_events.jsonl
Outputs:
  data/prediction/temporal_model.json
"""

import json, time, random
from pathlib import Path
from collections import defaultdict, Counter
from statistics import mean

DATA_DIR = Path("data")
ANALYSIS_DIR = DATA_DIR / "analysis"
PRED_DIR = DATA_DIR / "prediction"; PRED_DIR.mkdir(parents=True, exist_ok=True)
EVENTS_PATH = ANALYSIS_DIR / "pal_events.jsonl"
MODEL_PATH = PRED_DIR / "temporal_model.json"

class PredictiveBias:
    def __init__(self):
        self.transitions = defaultdict(Counter)
        self.last_symbol = None

    def observe(self, symbol: str):
        """Record symbol transition."""
        if self.last_symbol is not None:
            self.transitions[self.last_symbol][symbol] += 1
        self.last_symbol = symbol

    def train_from_events(self, path=EVENTS_PATH):
        """Train transition graph from pal_events.jsonl."""
        if not path.exists():
            print(f"⚠️ No PAL events found at {path}")
            return
        valid_syms = {"■","▲","●","◆","⬟","⬢"}  # extendable
        for line in path.read_text().splitlines():
            try:
                j = json.loads(line)
                sym = j.get("choice") or j.get("correct")
                # filter for glyph-like symbols
                if not sym or len(sym) > 2 or sym not in valid_syms:
                    continue
                self.observe(sym)
            except Exception:
                continue
        self.save()
        print(f"🧩 Learned {len(self.transitions)} unique transitions across {sum(sum(v.values()) for v in self.transitions.values())} events.")
        
    def predict_next(self, current: str):
        """Predict next likely symbol."""
        dist = self.transitions.get(current, {})
        if not dist:
            return random.choice(list(self.transitions.keys())) if self.transitions else None
        total = sum(dist.values())
        ranked = sorted(dist.items(), key=lambda x: x[1], reverse=True)
        choice, count = ranked[0]
        prob = count / total
        return choice, prob

    def save(self, path=MODEL_PATH):
        out = {k: dict(v) for k,v in self.transitions.items()}
        with open(path, "w") as f:
            json.dump(out, f, indent=2)
        print(f"🧮 Temporal model saved → {path}")

    def load(self, path=MODEL_PATH):
        if not path.exists(): return
        with open(path) as f:
            self.transitions = defaultdict(Counter, json.load(f))

# ─────────────────────────────────────────────
# Demonstration utility
# ─────────────────────────────────────────────
def run_predictive_cycle(n=10):
    pb = PredictiveBias(); pb.train_from_events()
    if not pb.transitions:
        print("⚠️ No transitions learned yet.")
        return
    keys = list(pb.transitions.keys())
    cur = random.choice(keys)
    print(f"🔹 Starting symbol: {cur}")
    for i in range(n):
        nxt = pb.predict_next(cur)
        if not nxt: break
        sym, prob = nxt
        print(f"→ predicts {sym}  (p≈{prob:.2f})")
        cur = sym

if __name__ == "__main__":
    run_predictive_cycle(12)