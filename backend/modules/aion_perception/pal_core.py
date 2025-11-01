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
import json, math, os, random, time, importlib.util, sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import matplotlib.pyplot as plt
import numpy as np
import time
import json

import argparse

parser = argparse.ArgumentParser(description="Tessaris PAL Core - Perceptual Association Layer")
parser.add_argument("--mode", type=str, default="train", help="Mode: train | resonance-feedback")
parser.add_argument("--prompt", type=str, help="Prompt or symbolic label")
parser.add_argument("--max_rounds", type=int, default=250, help="Max tuning rounds")
args, _ = parser.parse_known_args()

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
DATA_DIR = Path("data/perception"); DATA_DIR.mkdir(parents=True, exist_ok=True)
MEM_PATH = DATA_DIR / "exemplars.jsonl"
METRICS_PATH = Path("data/learning/ral_metrics.jsonl")  # produced by RAL
EVENTS_PATH = Path("data/analysis/pal_events.jsonl")
EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
random.seed(42)

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
    
    # 🔧 added attributes for resonance feedback scaling
    memory_weight: float = 1.0     # reinforcement scaling factor
    feedback_scale: float = 1.0    # modulation of feedback strength

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
        w = [1.0, 1.0, 0.7, 0.5, 0.5]
        return math.sqrt(sum(w[i] * (a[i] - b[i]) ** 2 for i in range(len(a))))

    def _nearest_score(self, prompt: str, option: str, vec: List[float]) -> float:
        pool = [e for e in self.memory if (e.prompt == prompt or e.option == option)]
        if not pool:
            pool = self.memory
        if not pool:
            return 0.0
        dists = sorted(self._dist(vec, e.vec) for e in pool)
        dists = dists[:max(1, min(self.k, len(dists)))]
        sims = [1.0 / (1.0 + d) for d in dists]
        return sum(sims) / len(sims)

    def ask(self, prompt: str, options: List[str]) -> Tuple[str, float, List[float]]:
        vec = self.current_feature()
        if random.random() < self.epsilon or len(self.memory) < 5:
            choice = random.choice(options)
            conf = 1.0 / len(options)
            return choice, conf, vec
        scored = [(opt, self._nearest_score(prompt, opt, vec)) for opt in options]
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
            # Knowledge Graph logging...
            try:
                concept = prompt.split()[-1] if prompt else "unknown"
                add_triplet(f"prompt:{prompt}", "elicited_choice", f"glyph:{correct}", vec=vec, strength=reward)
                add_triplet(f"glyph:{correct}", "means", f"concept:{concept}", vec=vec, strength=reward)
                add_triplet(f"concept:{concept}", "reinforced_by", f"trial:{int(time.time())}", strength=reward)
            except Exception as e:
                print(f"⚠️ KG logging failed: {e}")
        else:
            # nudge exploration up briefly after errors
            self.epsilon = min(0.5, self.epsilon + 0.02)
        # decay ε gradually to reach perceptual stability
        self.epsilon = max(0.05, self.epsilon * 0.995)

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
        """
        Save a labeled PAL state checkpoint for SQI stabilization or later recovery.
        Example:
            pal_state.save_checkpoint(tag="SQI_Stabilized_v1")
        """
        import json, os, time

        # Gather state info
        state = {
            "epsilon": getattr(self, "epsilon", None),
            "k": getattr(self, "k", None),
            "w": getattr(self, "w", None),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "exemplar_count": len(self.memory) if hasattr(self, "memory") else None,
            "tag": tag,
        }

        # Construct path
        checkpoints_dir = os.path.join(os.path.dirname(__file__), "checkpoints")
        os.makedirs(checkpoints_dir, exist_ok=True)
        fname = f"pal_state_{tag}.json"
        path = os.path.join(checkpoints_dir, fname)

        # Save checkpoint
        with open(path, "w") as f:
            json.dump(state, f, indent=2)

        print(f"💾 Checkpoint saved -> {fname} | ε={state['epsilon']:.3f}, k={state['k']}, w={state['w']}")

    # ─────────────────────────────────────────────
    # Resonance Feedback Integration
    # ─────────────────────────────────────────────
    def apply_resonance_feedback(pal):
        """
        Integrate Predictive Bias -> PAL -> SQI resonance feedback loop.
        Reinforces PAL exemplars based on the latest predictive transitions.
        """
        from pathlib import Path
        import json
        from datetime import datetime

        print("🔁 Applying Aion Resonance Feedback Loop...")
        LOG_PATH = Path("data/analysis/resonance_feedback.log")
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Load predictive transitions
            from backend.modules.aion_prediction.predictive_bias_layer import PredictiveBias
            pb = PredictiveBias()
            pb.load_state()
            transitions = getattr(pb, "transitions", {})
            print(f"🔮 Loaded {len(transitions)} predictive transitions for feedback.")

            # Reinforce PAL memory based on predictions
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

                # Persist PAL state checkpoint
                from backend.modules.aion_perception.pal_core import PALState
                pal_state = PALState(
                    epsilon=pal.epsilon,
                    k=pal.k,
                    w=getattr(pal, "memory_weight", 1.0)
                )
                pal_state.save_checkpoint(tag="SQI_Stabilized_v2")
                print("💾 SQI checkpoint saved -> pal_state_SQI_Stabilized_v2.json")
            except Exception as e:
                print(f"⚠️ SQI feedback skipped or failed: {e}")

            # Log feedback cycle
            with open(LOG_PATH, "a") as logf:
                logf.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "reinforced_links": count,
                    "predictive_transitions": len(transitions),
                    "epsilon": pal.epsilon,
                    "k": pal.k,
                    "weight": getattr(pal, "memory_weight", 1.0)
                }) + "\n")

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
    max_rounds: int = 5000,  # ⟲ Extended for long equilibrium sessions
    target_acc: float = 0.97,
    momentum: float = 0.35,
    learning_rate: float = 0.12,
):
    """Resonant self-tuning loop (v5, SQI-integrated)"""
    print("🧩 Starting resonant self-tuning perceptual loop (SQI hybrid)...")

    # Load prior tuning state if available
    import os, json, time
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
    ε_floor, ε_ceiling = 0.05, 0.6
    acc_trace, eps_trace = [], []
    sqi_cooldown = 0
    plt.ion()

    if len(acc_trace) > 50:
    drift = abs(np.mean(acc_trace[-10:]) - np.mean(acc_trace[-30:-20]))
    if drift > 0.05:
        print(f"⚠️ Drift detected (Δ={drift:.3f}) -> triggering micro-feedback pulse.")
        from backend.modules.aion_perception.qwave import SQIField, ResonancePulse
        sqi_field = SQIField.load_last_state()
        sqi_field.apply(ResonancePulse(frequency=1.35, gain=0.28, damping=0.90))

    # ─────────────────────────────────────────────
    # SQI-style warmup - small pre-training loop
    # ─────────────────────────────────────────────
    print("🧠 SQI Feedback Warmup Sequence (3 cycles)")
    for i in range(3):
        for p in prompts:
            ans = correct_map.get(p, random.choice(options)) if correct_map else random.choice(options)
            vec = np.random.randn(8).tolist()
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
                    sqi_field.apply(ResonancePulse(frequency=1.35, gain=0.28, damping=0.90))
                    sqi_cooldown = 20  # wait 20 rounds before next drift pulse
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
        if acc < 0.3:
            pal.epsilon = min(ε_ceiling, pal.epsilon + learning_rate * 0.2)
        elif acc > 0.7:
            pal.epsilon = max(ε_floor, pal.epsilon - learning_rate * 0.3)
        else:
            pal.epsilon *= 0.99

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
            # Use a stable domain key (e.g., phase name or joined prompts)
            domain_key = "|".join(sorted(set(prompts)))
            eps_bias = meta_eq_bias(domain_key, pal.epsilon)
            pal.epsilon = max(0.05, min(0.60, pal.epsilon + eps_bias))
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
                json.dump({
                    "epsilon": pal.epsilon,
                    "k": pal.k,
                    "memory_weight": pal.memory_weight
                }, open(state_path, "w"), indent=2)
                if getattr(pal, "verbose", False):
                    print(f"💾 Saved PAL state -> ε={pal.epsilon:.3f}, k={pal.k}, w={pal.memory_weight:.2f}")
            except Exception as e:
                print(f"⚠️ Failed to save PAL state: {e}")

    if stable_rounds == 0:
        print(f"⚠️ Max rounds reached ({max_rounds}) without resonance equilibrium.")
    else:
        print("🎯 Tuning session complete - state persisted.")

# ─────────────────────────────────────────────
# (end of your self_tune() function)
# ─────────────────────────────────────────────
    if stable_rounds == 0:
        print(f"⚠️ Max rounds reached ({max_rounds}) without resonance equilibrium.")
    else:
        print("🎯 Tuning session complete - state persisted.")

    # === SQI RESONANCE STABILIZATION BLOCK (TESSARIS PAL AUGMENT) ===
    from backend.modules.aion_perception.qwave import SQIField, ResonancePulse

    # Initialize stabilizer
    sqi_field = SQIField.load_last_state()
    sqi_field.enable_feedback(True)

    # Inject micro-resonance alignment sequence
    pulse = ResonancePulse(
        frequency=1.37,      # derived from w=1.17 + Δres(0.20)
        coherence=0.992,     # phase-locked stability coefficient
        gain=0.33,
        damping=0.87,
        epsilon_bias=-0.045,
    )
    sqi_field.apply(pulse)  

    # Reinforce PAL adaptation loop
    pal_state = sqi_field.sync_pal_state(
        epsilon_target=0.43,
        k=10,
        weight_bias=+0.02,
        commit=True,
    )
    print(f"✅ SQI stabilization complete -> ε={pal_state.epsilon:.3f}, k={pal_state.k}, w={pal_state.weight:.2f}")

    # --- Ensure checkpoint persistence through proper PALState wrapper ---
    if not isinstance(pal_state, PALState):
        pal_state = PALState(
            epsilon=getattr(pal_state, "epsilon", 0.5),
            k=getattr(pal_state, "k", 10),
            w=getattr(pal_state, "weight", 1.0),
        )

    pal_state.save_checkpoint(tag="SQI_Stabilized_v1")
    # === END SQI RESONANCE STABILIZATION BLOCK ===


# ─────────────────────────────────────────────
# Multi-Phase Perceptual Resonance Entry (v3)
# Supports: --mode=train | --mode=resonance-feedback
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    from datetime import datetime
    from pathlib import Path
    import json

    parser = argparse.ArgumentParser(description="Tessaris PAL Core Launcher")
    parser.add_argument("--mode", type=str, default="train", help="Mode: train | resonance-feedback")
    parser.add_argument("--prompt", type=str, default=None, help="Optional prompt for training focus")
    parser.add_argument("--max_rounds", type=int, default=400, help="Number of training rounds")
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
            pal.epsilon = state.get("epsilon", pal.epsilon)
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
                w=getattr(pal, "memory_weight", 1.0)
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

        try:
            from backend.modules.aion_prediction.predictive_bias_layer import PredictiveBias
            pb = PredictiveBias()
            pb.load_state()
            print(f"🔮 Loaded PredictiveBias model with {len(pb.transitions)} transitions")

            # Feedback loop - reinforce PAL exemplars based on predictive transitions
            count = 0
            for (a, b), weight in pb.transitions.items():
                vec = pal.current_feature()
                pal.feedback(prompt=a, chosen=b, correct=b, vec=vec, reward=min(1.0, weight / 10.0))
                count += 1
            print(f"✅ Applied resonance feedback for {count} transitions.")

            # Apply SQI reinforcement lock-in
            from backend.modules.aion_perception.qwave import SQIField, ResonancePulse
            sqi_field = SQIField.load_last_state()
            sqi_field.enable_feedback(True)
            pulse = ResonancePulse(frequency=1.37, coherence=0.992, gain=0.33, damping=0.87)
            sqi_field.apply(pulse)

            pal_state = PALState(
                epsilon=pal.epsilon,
                k=pal.k,
                w=getattr(pal, "memory_weight", 1.0)
            )
            pal_state.save_checkpoint(tag="SQI_Stabilized_v2")
            print("💾 Checkpoint saved after feedback -> pal_state_SQI_Stabilized_v2.json")

        except Exception as e:
            print(f"⚠️ Resonance feedback failed: {e}")

        # ─────────────────────────────────────────────
        # Log resonance feedback cycle
        # ─────────────────────────────────────────────
        from pathlib import Path
        import time
        log_path = Path("data/analysis/resonance_feedback.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a") as log:
            log.write(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Applied resonance feedback for "
                f"{len(pb.transitions)} transitions - ε={pal.epsilon:.3f}, "
                f"k={pal.k}, w={pal.memory_weight:.3f}\n"
            )

        print(f"💾 Log entry written -> {log_path}")

        print("🏁 Tessaris PAL resonance-feedback cycle complete.")

    else:
        print(f"⚠️ Unknown mode '{args.mode}' - defaulting to train.")