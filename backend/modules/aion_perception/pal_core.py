#!/usr/bin/env python3
"""
Perceptual Association Layer (PAL) - terminal-only core.
───────────────────────────────────────────────────────────────
- Stores (prompt, option, feature_vector, reward) exemplars in JSONL
- Chooses via k-NN over last resonance feature (ν, φ, A, S, H)
- ε-greedy exploration
- Reads latest feature from data/learning/ral_metrics.jsonl (if present)
- Logs successful exemplars into the Knowledge Graph (Aion brain)
- Emits per-trial events to data/analysis/pal_events.jsonl for snapshots
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

# ─────────────────────────────────────────────
# CLI (defined here; parsed only in __main__)
# ─────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Tessaris PAL Core - Perceptual Association Layer")
parser.add_argument("--mode", type=str, default="train", help="Mode: train | resonance-feedback")
parser.add_argument("--prompt", type=str, help="Prompt or symbolic label")
parser.add_argument("--max_rounds", type=int, default=250, help="Max tuning rounds")

# --- ensure repo root is on sys.path so `import backend...` works when run as a script ---
_REPO_ROOT = Path(__file__).resolve().parents[3]  # .../COMDEX
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ─────────────────────────────────────────────
# Robust KG import (auto-locates and loads dynamically)
# ─────────────────────────────────────────────
def _load_kg_add_triplet():
    KG_PATH = Path("backend/modules/aion_knowledge/knowledge_graph_core.py")
    if KG_PATH.exists():
        try:
            spec = importlib.util.spec_from_file_location("aion_knowledge.knowledge_graph_core", KG_PATH)
            kg = importlib.util.module_from_spec(spec)
            sys.modules["aion_knowledge.knowledge_graph_core"] = kg
            assert spec.loader is not None
            spec.loader.exec_module(kg)
            print("🧠 Knowledge Graph core loaded successfully.")
            return kg.add_triplet
        except Exception as e:
            print(f"⚠️ Failed to load KG core dynamically: {e}")
    else:
        print("⚠️ KG core not found at expected path.")
    return lambda *a, **kw: print("⚠️ KG not loaded; skipping triplet logging.")

add_triplet = _load_kg_add_triplet()

# ─────────────────────────────────────────────
# Setup paths
# ─────────────────────────────────────────────
_DATA_ROOT = Path(os.getenv("DATA_ROOT", "data"))  # e.g. .runtime/COMDEX_MOVE/data or ./data

DATA_DIR = _DATA_ROOT / "perception"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MEM_PATH = DATA_DIR / "exemplars.jsonl"

# produced by RAL (already correct in your version, just normalized)
METRICS_PATH = _DATA_ROOT / "learning" / "ral_metrics.jsonl"

EVENTS_PATH = _DATA_ROOT / "analysis" / "pal_events.jsonl"
EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)

random.seed(42)

# ─────────────────────────────────────────────
# Self-regulation thresholds (RAL-driven)
# ─────────────────────────────────────────────
EPS_FLOOR   = 0.05
EPS_CEILING = 0.25   # <- THIS is what stops the 0.597 pin
DAMP_EPS_MULT = 0.60   # stronger clamp (reduces exploration when unstable)
DAMP_K_BONUS  = 3      # widen neighbor smoothing when unstable
DAMP_W_MULT   = 0.90   # soften reinforcement when unstable
STABILITY_MIN = 0.75   # self-heal threshold
DAMP_COOLDOWN_STEPS = 10  # don't spam damping every ask()

# ─────────────────────────────────────────────
# ADR / feedback streams (Act 1: immune response)
# ─────────────────────────────────────────────
RESONANCE_STREAM_PATH = _DATA_ROOT / "feedback" / "resonance_stream.jsonl"
DRIFT_REPAIR_LOG_PATH = _DATA_ROOT / "feedback" / "drift_repair.log"
PAL_STATE_PATH = _DATA_ROOT / "prediction" / "pal_state.json"

# ─────────────────────────────────────────────
# ADR helpers (used by resonance-feedback mode)
# ─────────────────────────────────────────────
def _read_last_jsonl(path: Path) -> Optional[dict]:
    try:
        if not path.exists():
            return None
        txt = path.read_text().strip()
        if not txt:
            return None
        lines = txt.splitlines()
        return json.loads(lines[-1])
    except Exception:
        return None


def _write_json(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2))


def _append_jsonl(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(obj) + "\n")


def _adr_should_trigger(evt: dict) -> bool:
    # Spec: trigger when RSI < 0.6 (you’re using "stability" as RSI)
    rsi = float(evt.get("stability", 1.0))
    drift_ent = float(evt.get("drift_entropy", 0.0))
    # Keep drift_entropy as a secondary trigger so “entropy injection” works even if RSI key changes
    return (rsi < 0.60) or (drift_ent > 0.60)


def _apply_adr(pal: "PAL", evt: dict) -> bool:
    """Adaptive Drift Repair: autonomously reset epsilon/k and persist state + log."""
    try:
        pre = {
            "epsilon": float(getattr(pal, "epsilon", 0.2)),
            "k": int(getattr(pal, "k", 3)),
            "memory_weight": float(getattr(pal, "memory_weight", 1.0)),
        }

        # “Heal” parameters (safe defaults; tweak later once you like the feel)
        pal.pulse_boost = max(pal.pulse_boost, 0.35)
        pal.k = 7
        pal.memory_weight = max(1.0, float(getattr(pal, "memory_weight", 1.0)) * 0.95)

        post = {
            "epsilon": float(pal.epsilon),
            "k": int(pal.k),
            "memory_weight": float(getattr(pal, "memory_weight", 1.0)),
        }

        rec = {
            "timestamp": time.time(),
            "event": "ADR_TRIGGER",
            "source": evt.get("source", "resonance_stream"),
            "rsi": float(evt.get("stability", 1.0)),
            "drift_entropy": float(evt.get("drift_entropy", 0.0)),
            "pre": pre,
            "post": post,
        }

        _append_jsonl(DRIFT_REPAIR_LOG_PATH, rec)
        _write_json(
            PAL_STATE_PATH,
            {
                "epsilon": post["epsilon"],
                "k": post["k"],
                "memory_weight": post["memory_weight"],
                "timestamp": rec["timestamp"],
                "reason": "ADR_TRIGGER",
            },
        )

        print(
            f"🩸 ADR Activation: RSI={rec['rsi']:.2f}, drift_entropy={rec['drift_entropy']:.2f} "
            f"-> ε={pal.epsilon:.3f}, k={pal.k}"
        )
        return True
    except Exception as e:
        print(f"⚠️ ADR apply failed: {e}")
        return False


# ─────────────────────────────────────────────
# Core data structures
# ─────────────────────────────────────────────
@dataclass
class Exemplar:
    prompt: str
    option: str          # symbol/glyph/label
    vec: List[float]     # [nu, phi, amp, stability, entropy]
    reward: float = 1.0


@dataclass
class PAL:
    k: int = 3
    epsilon: float = 0.20
    max_mem: int = 5000
    memory: List[Exemplar] = field(default_factory=list)

    # resonance feedback scaling
    memory_weight: float = 1.0
    feedback_scale: float = 1.0
    # NEW: SQI/ADR pulse (0..1), decays each ask()
    pulse_boost: float = 0.0

    # damping control
    damp_cooldown: int = 0

    # ---------- IO ----------
    def load(self):
        self.memory.clear()
        if not MEM_PATH.exists():
            return
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
            f.flush()
            os.fsync(f.fileno())
        self.memory.append(ex)
        if len(self.memory) > self.max_mem:
            self.memory = self.memory[-self.max_mem:]
            with open(MEM_PATH, "w") as f:
                for e in self.memory:
                    f.write(json.dumps(e.__dict__) + "\n")
        if getattr(self, "verbose", False):
            print(f"💾 Stored exemplar -> ({ex.prompt} -> {ex.option}) | total={len(self.memory)}")

    # ---------- features ----------
    def current_feature(self) -> List[float]:
        """Use last RAL metrics if available; else a pseudo-resonant feature."""
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

        # fallback: slow drift pseudo-feature
        t = time.time()
        return [
            math.tanh(math.sin(t / 7.0)),              # ν
            math.tanh(math.cos(t / 11.0)),             # φ
            1.0 + 0.1 * math.sin(t / 5.0),             # A
            0.9 + 0.1 * abs(math.sin(t / 13.0)),       # S
            0.05 + 0.02 * abs(math.cos(t / 17.0)),     # H
        ]

    # ---------- distances / choice ----------
    @staticmethod
    def _dist(a: List[float], b: List[float]) -> float:
        # Expect 5D vectors; tolerate mismatch by clipping to min length.
        w = [1.0, 1.0, 0.7, 0.5, 0.5]
        n = min(len(a), len(b), len(w))
        return math.sqrt(sum(w[i] * (a[i] - b[i]) ** 2 for i in range(n)))

    def _nearest_score(self, prompt: str, option: str, vec: List[float]) -> float:
        pool = [e for e in self.memory if (e.prompt == prompt or e.option == option)]
        if not pool:
            pool = self.memory
        if not pool:
            return 0.0
        dists = sorted(self._dist(vec, e.vec) for e in pool)
        dists = dists[: max(1, min(self.k, len(dists)))]
        sims = [1.0 / (1.0 + d) for d in dists]
        return sum(sims) / len(sims)

    def apply_damping(self, stability: float, entropy: float) -> None:
        """
        Self-heal: clamp exploration down, smooth neighbor selection, soften reinforcement.
        (This is the “breathing” contraction when stability drops.)
        """
        self.epsilon = max(EPS_FLOOR, min(EPS_CEILING, self.epsilon * DAMP_EPS_MULT))
        self.k = max(3, min(10, self.k + DAMP_K_BONUS))
        self.memory_weight = max(1.0, self.memory_weight * DAMP_W_MULT)

        if getattr(self, "verbose", False):
            print(
                f"🫁 DAMPING applied | S={stability:.3f} H={entropy:.3f} -> "
                f"ε={self.epsilon:.3f} k={self.k} w={self.memory_weight:.3f}"
            )

    def ask(self, prompt: str, options: List[str]) -> Tuple[str, float, List[float]]:
        vec = self.current_feature()

        # NEW: pulse decays every decision
        self.pulse_boost *= 0.90

        # --- self-heal hook (uses RAL feature: [nu, phi, amp, stability, entropy]) ---
        stability = float(vec[3]) if len(vec) > 3 else 1.0
        entropy   = float(vec[4]) if len(vec) > 4 else 0.0

        if self.damp_cooldown > 0:
            self.damp_cooldown -= 1
        elif stability < STABILITY_MIN:
            self.apply_damping(stability=stability, entropy=entropy)
            self.damp_cooldown = DAMP_COOLDOWN_STEPS

        if random.random() < self.epsilon or len(self.memory) < 5:
            choice = random.choice(options)
            conf = 1.0 / len(options)
            return choice, conf, vec

        scored = [(opt, self._nearest_score(prompt, opt, vec) + self.pulse_boost) for opt in options]
        total = sum(max(s, 1e-6) for _, s in scored)
        probs = [(opt, max(s, 1e-6) / total) for opt, s in scored]
        probs.sort(key=lambda x: x[1], reverse=True)
        choice, conf = probs[0]
        return choice, conf, vec

    # ---------- feedback + KG integration ----------
    def feedback(self, prompt: str, chosen: str, correct: str, vec: List[float], reward: float):
        """Update learning memory and log correct associations into the Knowledge Graph."""
        if chosen == correct and reward > 0:
            self.append(Exemplar(prompt=prompt, option=correct, vec=vec, reward=reward * self.memory_weight))
            if getattr(self, "verbose", False):
                print(f"✅ Reinforced {prompt} -> {correct} (reward={reward:.2f}, ε={self.epsilon:.3f})")
            try:
                concept = prompt.split()[-1] if prompt else "unknown"
                add_triplet(f"prompt:{prompt}", "elicited_choice", f"glyph:{correct}", vec=vec, strength=reward)
                add_triplet(f"glyph:{correct}", "means", f"concept:{concept}", vec=vec, strength=reward)
                add_triplet(f"concept:{concept}", "reinforced_by", f"trial:{int(time.time())}", strength=reward)
            except Exception as e:
                print(f"⚠️ KG logging failed: {e}")
        else:
            # nudge exploration up briefly after errors (bounded)
            self.epsilon = min(EPS_CEILING, self.epsilon + 0.01)

        # decay ε gradually to reach perceptual stability
        self.epsilon = max(EPS_FLOOR, self.epsilon * 0.98)

    def _log_event(self, prompt, choice, correct, reward, acc):
        rec = {
            "timestamp": time.time(),
            "prompt": prompt,
            "choice": choice,
            "correct": correct,
            "reward": reward,
            "epsilon": self.epsilon,
            "k": self.k,
            "accuracy": acc,
        }
        EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(EVENTS_PATH, "a") as f:
            f.write(json.dumps(rec) + "\n")


# ─────────────────────────────────────────────
# PAL State Checkpoint Persistence
# ─────────────────────────────────────────────
class PALState:
    """Encapsulated PAL tuning state with checkpoint persistence."""
    def __init__(self, epsilon: float, k: int, w: float):
        self.epsilon = epsilon
        self.k = k
        self.w = w

    def save_checkpoint(self, tag: str = "checkpoint"):
        import json as _json
        import os as _os
        import time as _time

        state = {
            "epsilon": getattr(self, "epsilon", None),
            "k": getattr(self, "k", None),
            "w": getattr(self, "w", None),
            "timestamp": _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime()),
            "tag": tag,
        }

        checkpoints_dir = _os.path.join(_os.path.dirname(__file__), "checkpoints")
        _os.makedirs(checkpoints_dir, exist_ok=True)
        fname = f"pal_state_{tag}.json"
        path = _os.path.join(checkpoints_dir, fname)

        with open(path, "w") as f:
            _json.dump(state, f, indent=2)

        print(f"💾 Checkpoint saved -> {fname} | ε={state['epsilon']:.3f}, k={state['k']}, w={state['w']}")

    def apply_resonance_feedback(pal):
        from datetime import datetime

        print("🔁 Applying Aion Resonance Feedback Loop...")
        LOG_PATH = _DATA_ROOT / "analysis" / "resonance_feedback.log"
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        try:
            from backend.modules.aion_prediction.predictive_bias_layer import PredictiveBias
            pb = PredictiveBias()
            if hasattr(pb, "load_state"):
                pb.load_state()
            elif hasattr(pb, "load"):
                pb.load()
            transitions = getattr(pb, "transitions", {}) or {}
            print(f"🔮 Loaded {len(transitions)} predictive transitions for feedback.")

            count = 0
            for (a, b), weight in transitions.items():
                vec = pal.current_feature()
                pal.feedback(a, b, b, vec, reward=min(3.0, weight / 10))
                count += 1

            print(f"✅ Reinforced {count} predictive->perceptual associations.")

            # SQI stabilization pulse
            try:
                from backend.modules.aion_perception.qwave import SQIField, ResonancePulse
                sqi_field = SQIField.load_last_state()
                sqi_field.enable_feedback(True)
                pulse = ResonancePulse(frequency=1.33, coherence=0.991, gain=0.35, damping=0.88)
                sqi_field.apply(pulse)

                pal_state = PALState(
                    epsilon=pal.epsilon,
                    k=pal.k,
                    w=getattr(pal, "memory_weight", 1.0),
                )
                pal_state.save_checkpoint(tag="SQI_Stabilized_v2")
                print("💾 SQI checkpoint saved -> pal_state_SQI_Stabilized_v2.json")
            except Exception as e:
                print(f"⚠️ SQI feedback skipped or failed: {e}")

            with open(LOG_PATH, "a") as logf:
                logf.write(
                    json.dumps(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "reinforced_links": count,
                            "predictive_transitions": len(transitions),
                            "epsilon": pal.epsilon,
                            "k": pal.k,
                            "weight": getattr(pal, "memory_weight", 1.0),
                        }
                    )
                    + "\n"
                )

            print(f"🪶 Logged resonance feedback -> {LOG_PATH}")

        except Exception as e:
            print(f"⚠️ Resonance feedback failed: {e}")


# ─────────────────────────────────────────────
# Resonant self-tuning entry point (SQI-Integrated)
# ─────────────────────────────────────────────
def self_tune(
    pal: PAL,
    prompts: List[str],
    options: List[str],
    correct_map: Optional[Dict[str, str]] = None,
    max_rounds: int = 5000,
    target_acc: float = 0.97,
    momentum: float = 0.35,
    learning_rate: float = 0.12,
):
    """Resonant self-tuning loop (v5, SQI-integrated)"""
    print("🧩 Starting resonant self-tuning perceptual loop (SQI hybrid)...")

    # Load prior tuning state if available
    state_path = "data/prediction/pal_state.json"
    if os.path.exists(state_path):
        try:
            state = json.load(open(state_path))
            pal.epsilon = state.get("epsilon", pal.epsilon)
            pal.k = state.get("k", pal.k)
            pal.memory_weight = state.get("memory_weight", pal.memory_weight)
            print(f"🔁 Restored PAL tuning state -> ε={pal.epsilon:.3f}, k={pal.k}, w={pal.memory_weight:.2f}")
        except Exception as e:
            print(f"⚠️ Failed to load tuning state: {e}")

    stable_rounds = 0
    reward_momentum = 0.0
    ε_floor, ε_ceiling = EPS_FLOOR, EPS_CEILING  # recommended
    acc_trace, eps_trace = [], []
    sqi_cooldown = 0
    plt.ion()

    # ─────────────────────────────────────────────
    # SQI-style warmup - small pre-training loop
    # ─────────────────────────────────────────────
    print("🧠 SQI Feedback Warmup Sequence (3 cycles)")
    for i in range(3):
        for p in prompts:
            ans = correct_map.get(p, random.choice(options)) if correct_map else random.choice(options)
            vec = np.random.randn(5).tolist()
            pal.feedback(p, ans, ans, vec, 1.0)
        pal.epsilon = max(ε_floor, pal.epsilon * 0.9)
        print(f"🌀 Warmup {i+1}/3 complete -> ε={pal.epsilon:.3f}")
        time.sleep(0.2)

    # ─────────────────────────────────────────────
    # Main tuning loop
    # ─────────────────────────────────────────────
    for r in range(max_rounds):
        correct = 0
        total_reward = 0.0

        for p in prompts:
            choice, conf, vec = pal.ask(p, options)
            ans = correct_map.get(p, random.choice(options)) if correct_map else random.choice(options)
            reward = 1.0 if choice == ans else 0.0
            total_reward += reward
            pal.feedback(p, choice, ans, vec, reward)
            if reward > 0:
                correct += 1

        acc = correct / len(prompts)
        reward_momentum = momentum * reward_momentum + (1 - momentum) * acc
        pal._log_event(p, choice, ans, total_reward, acc)
        acc_trace.append(acc)
        eps_trace.append(pal.epsilon)

        print(f"[Round {r + 1}] Accuracy={acc:.3f}  ε={pal.epsilon:.3f}  k={pal.k}  ⟲={reward_momentum:.3f}")

        # ─────────────────────────────────────────────
        # Drift detection -> micro-feedback pulse
        # ─────────────────────────────────────────────
        if len(acc_trace) > 50 and sqi_cooldown == 0:
            drift = abs(np.mean(acc_trace[-10:]) - np.mean(acc_trace[-30:-20]))
            if drift > 0.05:
                print(f"⚠️ Drift detected (Δ={drift:.3f}) -> triggering micro-feedback pulse.")
                try:
                    from backend.modules.aion_perception.qwave import SQIField, ResonancePulse
                    sqi_field = SQIField.load_last_state()
                    sqi_field.apply(
                        ResonancePulse(
                            frequency=1.35,
                            coherence=0.985,  # ✅ FIX: required arg
                            gain=0.28,
                            damping=0.90,
                        )
                    )
                    sqi_cooldown = 20
                except Exception as e:
                    print(f"⚠️ SQI micro-feedback failed: {e}")

        # ─────────────────────────────────────────────
        # Live plotting (optional)
        # ─────────────────────────────────────────────
        if r % 20 == 0 and r > 0:
            plt.clf()
            plt.plot(acc_trace, label="Accuracy", linewidth=2)
            plt.plot(eps_trace, label="ε", linestyle="--")
            plt.xlabel("Rounds")
            plt.ylabel("Value")
            plt.title("Resonant Self-Tuning Dynamics (SQI Hybrid)")
            plt.legend()
            plt.pause(0.05)

        # ─────────────────────────────────────────────
        # Dynamic epsilon adaptation
        # ─────────────────────────────────────────────
        if acc > 0.7:
            pal.epsilon -= learning_rate * 0.3
        elif acc < 0.3:
            if pal.epsilon < 0.20:
                pal.epsilon += learning_rate * 0.1
        else:
            pal.epsilon *= 0.995

        pal.epsilon = max(ε_floor, min(ε_ceiling, pal.epsilon))

        # ─────────────────────────────────────────────
        # Asymmetric reinforcement scaling
        # ─────────────────────────────────────────────
        if acc > 0:
            pal.memory_weight = min(3.0, pal.memory_weight * (1.0 + 0.05 * acc))
        else:
            pal.memory_weight = max(1.0, pal.memory_weight * 0.95)
        pal.feedback_scale = pal.memory_weight

        # ─────────────────────────────────────────────
        # SQI-inspired drift and stagnation correction
        # ─────────────────────────────────────────────
        drift = 0.0
        if len(acc_trace) > 5:
            drift = abs(acc_trace[-1] - acc_trace[-5])

        if drift < 0.01 and sqi_cooldown == 0:
            print("🧠 Resonance stagnation detected -> SQI feedback pulse.")
            pal.memory_weight = min(3.0, pal.memory_weight * 1.15)
            pal.epsilon = max(ε_floor, pal.epsilon * 0.85)
            sqi_cooldown = 10
        else:
            sqi_cooldown = max(0, sqi_cooldown - 1)

        # --- F18 meta-equilibrium nudge (tiny, global equalizer) ---
        try:
            from backend.modules.aion_perception.qwave import meta_eq_bias
            domain_key = "|".join(sorted(set(prompts)))
            eps_bias = meta_eq_bias(domain_key, pal.epsilon)

            # ✅ meta-eq may only COOL epsilon (never heat it)
            if eps_bias > 0:
                eps_bias = 0.0

            pal.epsilon = pal.epsilon + eps_bias
            pal.epsilon = max(ε_floor, min(ε_ceiling, pal.epsilon))

            if getattr(pal, "verbose", False):
                print(f"⚙️  Meta-eq bias applied -> Δε={eps_bias:+.4f} -> ε={pal.epsilon:.3f}")
        except Exception as _e:
            if getattr(pal, "verbose", False):
                print(f"⚠️ meta_eq_bias skipped: {_e}")

        # ─────────────────────────────────────────────
        # Adaptive k compression / expansion
        # ─────────────────────────────────────────────
        if acc > 0.8 and pal.k > 4:
            pal.k = max(3, pal.k - 1)
        elif acc < 0.4 and pal.k < 10:
            pal.k += 1

        # ─────────────────────────────────────────────
        # Equilibrium check
        # ─────────────────────────────────────────────
        if acc >= target_acc:
            stable_rounds += 1
            if stable_rounds >= 5:
                print(f"✅ Resonant equilibrium reached ({acc:.2f}) after {r+1} rounds")
                try:
                    from backend.modules.aion_analysis import pal_snapshot
                    pal_snapshot.take_snapshot()
                except Exception:
                    pass
                break
        else:
            stable_rounds = 0

        # ─────────────────────────────────────────────
        # Periodic persistence of PAL tuning state
        # ─────────────────────────────────────────────
        if r % 25 == 0:
            try:
                os.makedirs("data/prediction", exist_ok=True)
                json.dump(
                    {
                        "epsilon": pal.epsilon,
                        "k": pal.k,
                        "memory_weight": pal.memory_weight,
                    },
                    open(state_path, "w"),
                    indent=2,
                )
                if getattr(pal, "verbose", False):
                    print(f"💾 Saved PAL state -> ε={pal.epsilon:.3f}, k={pal.k}, w={pal.memory_weight:.2f}")
            except Exception as e:
                print(f"⚠️ Failed to save PAL state: {e}")

    if stable_rounds == 0:
        print(f"⚠️ Max rounds reached ({max_rounds}) without resonance equilibrium.")
    else:
        print("🎯 Tuning session complete - state persisted.")

# ─────────────────────────────────────────────
# Multi-Phase Perceptual Resonance Entry (v3)
# Supports: --mode=train | --mode=resonance-feedback
# ─────────────────────────────────────────────
if __name__ == "__main__":
    from datetime import datetime

    args = parser.parse_args()

    print(f"\n🚀 Launching Tessaris PAL Core - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    pal = PAL(k=3, epsilon=0.08)
    pal.load()
    pal.verbose = True
    pal.trace = True

    # Try to restore last stabilized checkpoint
    try:
        last_ckpt = Path("backend/modules/aion_perception/checkpoints/pal_state_SQI_Stabilized_v2.json")
        if last_ckpt.exists():
            print(f"🔁 Loading last PAL checkpoint -> {last_ckpt.name}")
            state = json.load(open(last_ckpt))
            pal.epsilon = max(0.05, min(0.60, float(state.get("epsilon", pal.epsilon))))
            pal.k = state.get("k", pal.k)
            pal.memory_weight = state.get("w", pal.memory_weight)
    except Exception as e:
        print(f"⚠️ Could not restore checkpoint: {e}")

    # ─────────────────────────────────────────────
    # MODE 1 - Full Training Cycle (default)
    # ─────────────────────────────────────────────
    if args.mode == "train":
        print("🔹 Mode: Full Multi-Phase Training")

        # === Phase 1: Symbolic Shape Association ===
        print("\n🔹 Phase 1: Symbolic Shape Association")
        self_tune(
            pal,
            prompts=["select shape", "pick glyph", "choose pattern"],
            options=["■", "▲", "●", "◆"],
            correct_map={
                "select shape": "■",
                "pick glyph": "▲",
                "choose pattern": "●",
            },
            max_rounds=args.max_rounds,
            target_acc=0.92,
            momentum=0.3,
            learning_rate=0.15,
        )

        # === Phase 2: Abstract Concept Resonance ===
        print("\n🔹 Phase 2: Abstract Field Resonance")
        self_tune(
            pal,
            prompts=["align token", "stabilize field", "trace resonance", "harmonize pattern"],
            options=["Ω", "λ", "ψ", "Φ"],
            correct_map={
                "align token": "Ω",
                "stabilize field": "λ",
                "trace resonance": "ψ",
                "harmonize pattern": "Φ",
            },
            max_rounds=500,
            target_acc=0.95,
            momentum=0.35,
            learning_rate=0.12,
        )

        # === Phase 3: SQI Reinforcement ===
        print("\n🔹 Phase 3: SQI Reinforcement Pulse")
        try:
            from backend.modules.aion_perception.qwave import SQIField, ResonancePulse
            sqi_field = SQIField.load_last_state()
            sqi_field.enable_feedback(True)
            pulse = ResonancePulse(frequency=1.33, coherence=0.991, gain=0.35, damping=0.88)
            sqi_field.apply(pulse)

            pal_state = PALState(
                epsilon=pal.epsilon,
                k=pal.k,
                w=getattr(pal, "memory_weight", 1.0),
            )
            pal_state.save_checkpoint(tag="SQI_Stabilized_v2")
            print("✅ SQI stabilization complete - checkpoint v2 saved.")
        except Exception as e:
            print(f"⚠️ SQI phase skipped or failed: {e}")

        print("\n🏁 Tessaris PAL multi-phase training complete.")

    # ─────────────────────────────────────────────
    # MODE 2 - Resonance Feedback Integration
    # ─────────────────────────────────────────────
    elif args.mode == "resonance-feedback":
        print("🔹 Mode: Resonance Feedback Integration")

        # ─────────────────────────────────────────────
        # ADR: read resonance_stream + self-heal first
        # ─────────────────────────────────────────────
        adr_evt = _read_last_jsonl(RESONANCE_STREAM_PATH)
        adr_fired = False
        if adr_evt and _adr_should_trigger(adr_evt):
            adr_fired = _apply_adr(pal, adr_evt)

        pb = None
        transitions_count = 0
        applied_count = 0  # how many transitions we actually applied

        try:
            from backend.modules.aion_prediction.predictive_bias_layer import PredictiveBias
            pb = PredictiveBias()
            pb.load_state()
            # Ensure PredictiveBias reads the same data root as PAL
            # If you're using the runtime-moved data, export DATA_ROOT accordingly when launching PAL
            if os.getenv("DATA_ROOT"):
                os.environ["TESSARIS_DATA_ROOT"] = os.getenv("DATA_ROOT")

            transitions = getattr(pb, "transitions", {}) or {}
            transitions_count = len(transitions)
            print(f"🔮 Loaded PredictiveBias model with {transitions_count} transitions")

            for (a, b), weight in transitions.items():
                vec = pal.current_feature()
                pal.feedback(prompt=a, chosen=b, correct=b, vec=vec, reward=min(1.0, weight / 10.0))
                applied_count += 1

            print(f"✅ Applied resonance feedback for {applied_count} transitions.")

            # ─────────────────────────────────────────────
            # SQI pulse + checkpoint (keep your existing code here)
            # ─────────────────────────────────────────────
            # (rest of your SQI pulse + checkpoint code...)

        except Exception as e:
            print(f"⚠️ Resonance feedback failed: {e}")
            transitions_count = 0
            applied_count = 0

        # ─────────────────────────────────────────────
        # Log cycle ONLY if something happened (transitions OR ADR)
        # ─────────────────────────────────────────────
        if applied_count > 0 or adr_fired:
            log_path = _DATA_ROOT / "analysis" / "resonance_feedback.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a") as log:
                log.write(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"ADR={adr_fired} transitions={applied_count}/{transitions_count} "
                    f"ε={pal.epsilon:.3f} k={pal.k} w={pal.memory_weight:.3f}\n"
                )
            print(f"💾 Log entry written -> {log_path}")
        else:
            print("ℹ️ Skipping log entry (no predictive transitions applied, no ADR fired).")

        print("🏁 Tessaris PAL resonance-feedback cycle complete.")

    else:
        print(f"⚠️ Unknown mode '{args.mode}' - defaulting to train.")