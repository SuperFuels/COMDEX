#!/usr/bin/env python3
"""
Perceptual Association Layer (PAL v2) - with Knowledge Graph recall.
───────────────────────────────────────────────────────────────
- Builds on PAL v1 with bidirectional memory retrieval.
- Uses the Knowledge Graph to bias selections by reinforced glyphs.
- Stores (prompt, option, feature_vector, reward) exemplars in JSONL.
- Chooses via k-NN + KG recall weighting.
- ε-greedy exploration with adaptive decay.
"""

from __future__ import annotations
import json, math, os, random, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Tuple

# ─────────────────────────────────────────────
# Optional KG import (non-fatal)
# ─────────────────────────────────────────────
try:
    from aion_knowledge.knowledge_graph_core import add_triplet, get_related
except Exception:
    def add_triplet(*a, **kw):
        print("⚠️ KG not loaded; skipping triplet logging.")
    def get_related(*a, **kw):
        return []

# ─────────────────────────────────────────────
# Setup paths
# ─────────────────────────────────────────────
DATA_DIR = Path("data/perception"); DATA_DIR.mkdir(parents=True, exist_ok=True)
MEM_PATH = DATA_DIR / "exemplars.jsonl"
METRICS_PATH = Path("data/learning/ral_metrics.jsonl")
random.seed(42)

# ─────────────────────────────────────────────
# Core data structures
# ─────────────────────────────────────────────
@dataclass
class Exemplar:
    prompt: str
    option: str
    vec: List[float]         # [ν, φ, A, S, H]
    reward: float = 1.0


@dataclass
class PAL:
    k: int = 3
    epsilon: float = 0.20
    max_mem: int = 5000
    memory: List[Exemplar] = field(default_factory=list)

    # ---------- IO ----------
    def load(self):
        self.memory.clear()
        if not MEM_PATH.exists(): return
        with open(MEM_PATH) as f:
            for line in f:
                try:
                    j = json.loads(line)
                    self.memory.append(Exemplar(**j))
                except Exception:
                    continue

    def append(self, ex: Exemplar):
        with open(MEM_PATH, "a") as f:
            f.write(json.dumps(ex.__dict__) + "\n")
        self.memory.append(ex)
        if len(self.memory) > self.max_mem:
            self.memory = self.memory[-self.max_mem:]
            with open(MEM_PATH, "w") as f:
                for e in self.memory:
                    f.write(json.dumps(e.__dict__) + "\n")

    # ---------- features ----------
    def current_feature(self) -> List[float]:
        if METRICS_PATH.exists():
            try:
                *_, last = METRICS_PATH.read_text().strip().splitlines()
                j = json.loads(last)
                return [
                    float(j.get("mean_nu", 0.0)),
                    float(j.get("mean_phi", 0.0)),
                    float(j.get("mean_amp", 0.0)),
                    float(j.get("stability", 1.0)),
                    float(j.get("drift_entropy", 0.0)),
                ]
            except Exception:
                pass
        t = time.time()
        return [
            math.tanh(math.sin(t/7.0)),
            math.tanh(math.cos(t/11.0)),
            1.0 + 0.1*math.sin(t/5.0),
            0.9 + 0.1*abs(math.sin(t/13.0)),
            0.05 + 0.02*abs(math.cos(t/17.0)),
        ]

    # ---------- distances / choice ----------
    @staticmethod
    def _dist(a: List[float], b: List[float]) -> float:
        w = [1.0, 1.0, 0.7, 0.5, 0.5]
        return math.sqrt(sum(w[i]*(a[i]-b[i])**2 for i in range(len(a))))

    def _nearest_score(self, prompt: str, option: str, vec: List[float]) -> float:
        pool = [e for e in self.memory if (e.prompt == prompt or e.option == option)]
        if not pool: pool = self.memory
        if not pool: return 0.0
        dists = sorted(self._dist(vec, e.vec) for e in pool)
        dists = dists[:max(1, min(self.k, len(dists)))]
        sims = [1.0/(1.0 + d) for d in dists]
        return sum(sims)/len(sims)

    # ---------- ask with KG recall ----------
    def ask(self, prompt: str, options: List[str]) -> Tuple[str, float, List[float]]:
        vec = self.current_feature()
        # exploration
        if random.random() < self.epsilon or len(self.memory) < 5:
            choice = random.choice(options)
            conf = 1.0/len(options)
            return choice, conf, vec

        # base exploitation via memory
        scored = [(opt, self._nearest_score(prompt, opt, vec)) for opt in options]

        # add KG recall weighting
        try:
            kg_links = get_related(f"prompt:{prompt}", relation="elicited_choice")
            for opt, s in scored:
                for link in kg_links:
                    if link["target"].endswith(opt):
                        s += float(link.get("strength", 0.0)) * 0.2
            scored = [(opt, s) for opt, s in scored]
        except Exception:
            pass

        total = sum(max(s, 1e-6) for _, s in scored)
        probs = [(opt, max(s,1e-6)/total) for opt, s in scored]
        probs.sort(key=lambda x: x[1], reverse=True)
        choice, conf = probs[0]
        return choice, conf, vec

    # ---------- feedback + KG integration ----------
    def feedback(self, prompt: str, chosen: str, correct: str, vec: List[float], reward: float):
        if chosen == correct and reward > 0:
            self.append(Exemplar(prompt=prompt, option=correct, vec=vec, reward=reward))
            try:
                concept = prompt.split()[-1] if prompt else "unknown"
                add_triplet(f"prompt:{prompt}", "elicited_choice", f"glyph:{correct}", vec=vec, strength=reward)
                add_triplet(f"glyph:{correct}", "means", f"concept:{concept}", vec=vec, strength=reward)
                add_triplet(f"concept:{concept}", "reinforced_by", f"trial:{int(time.time())}", strength=reward)
            except Exception as e:
                print(f"⚠️ KG logging failed: {e}")
        else:
            self.epsilon = min(0.5, self.epsilon + 0.02)
        self.epsilon = max(0.05, self.epsilon * 0.995)