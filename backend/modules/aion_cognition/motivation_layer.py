#!/usr/bin/env python3
# ───────────────────────────────────────────────
# 🧩 Motivation Layer — Phase 63: Harmonic-Coupled Resonant Cognition
# Generates DriveVectors (curiosity, goal, need)
# Integrates Harmony feedback (ΔH) from Θ and reflection fields.
# Persists MotivationHistory.json for long-term learning trends.
# ───────────────────────────────────────────────

import os, json, time, math, random
from pathlib import Path
from statistics import mean
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.reinforcement_mixin import ResonantReinforcementMixin
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat

class MotivationLayer(ResonantReinforcementMixin):
    def __init__(self, cache_path: str = "data/memory/resonant_memory_cache.json"):
        super().__init__(name="motivation_layer", learning_rate=0.05)
        self.rmc = ResonantMemoryCache()
        self.cache_path = cache_path
        self.log_path = Path("data/memory/motivation_history.json")
        os.makedirs(self.log_path.parent, exist_ok=True)

        # Heartbeat reference for SQI + Θ feedback coupling
        self.Theta = ResonanceHeartbeat(namespace="motivation", base_interval=1.0)

        # Initialize drive states
        self.drives = {"curiosity": 0.0, "goal": 0.0, "need": 0.0}
        self.last_entropy = 0.0
        self.last_sqi = 0.6
        self.last_harmony = 0.5

        # Path to harmonic memory (for ΔH tracking)
        self.hmf_path = Path("data/analysis/harmonic_memory.json")

    # ───────────────────────────────────────────
    # Compute entropy + harmony feedback
    # ───────────────────────────────────────────
    def compute_entropy(self) -> float:
        """Compute environmental entropy from RMC (fallback to stochastic noise)."""
        try:
            coherence_vals = [
                v.get("coherence", 0.5)
                for v in self.rmc.cache.values()
                if isinstance(v, dict)
            ]
            entropy = 1.0 - sum(coherence_vals) / len(coherence_vals) if coherence_vals else random.uniform(0.3, 0.9)
            self.last_entropy = round(entropy, 3)
        except Exception:
            self.last_entropy = random.uniform(0.3, 0.9)
        return self.last_entropy

    def get_harmony_delta(self) -> float:
        """Get ΔH (change in harmony) from harmonic_memory.json."""
        try:
            if self.hmf_path.exists():
                js = json.loads(self.hmf_path.read_text())
                new_h = float(js.get("harmony_integral", 0.5))
                delta_h = round(new_h - self.last_harmony, 3)
                self.last_harmony = new_h
                return delta_h
        except Exception:
            pass
        return 0.0

    # ───────────────────────────────────────────
    # Drive Vector computation
    # ───────────────────────────────────────────
    def generate_drive_vector(self) -> dict:
        """
        Generates a normalized DriveVector influenced by entropy, SQI, ΔH, and reinforcement feedback.
        - Curiosity grows with entropy + positive ΔH.
        - Goal stabilizes with coherence (inverse entropy).
        - Need rises when SQI is low or ΔH < 0 (harmonic drift).
        """
        entropy = self.compute_entropy()
        sqi = float(getattr(self.Theta, "_last_pulse", {}).get("sqi", 0.6))
        delta_h = self.get_harmony_delta()

        curiosity = (entropy + max(delta_h, 0)) * random.uniform(0.8, 1.2)
        goal = (1.0 - entropy) * random.uniform(0.7, 1.1)
        need = ((1.0 - sqi) + abs(min(delta_h, 0))) * random.uniform(0.6, 1.2)

        total = max(curiosity + goal + need, 1e-6)
        self.drives = {
            "curiosity": round(curiosity / total, 3),
            "goal": round(goal / total, 3),
            "need": round(need / total, 3),
        }
        self.last_sqi = sqi
        return self.drives

    # ───────────────────────────────────────────
    # Output vector + reinforcement loop
    # ───────────────────────────────────────────
    def output_vector(self) -> dict:
        """
        Outputs DriveVector, logs it, updates resonance feedback, and
        emits Θ.event() for synchronization monitoring.
        """
        vector = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "drives": self.generate_drive_vector(),
            "entropy": self.last_entropy,
            "sqi": self.last_sqi,
            "ΔH": self.get_harmony_delta(),
        }

        # Balance-based alignment score
        balance = 1.0 - abs(max(vector["drives"].values()) - min(vector["drives"].values()))
        alignment_score = round((balance + (1.0 - vector["entropy"]) + vector["sqi"]) / 3.0, 3)

        # Reinforce behavior
        self.update_resonance_feedback(outcome_score=alignment_score, reason="Drive vector alignment")

        # Emit event to Θ field
        try:
            self.Theta.event("motivation_update",
                             drives=vector["drives"],
                             alignment=alignment_score,
                             entropy=vector["entropy"],
                             sqi=vector["sqi"],
                             delta_h=vector["ΔH"])
        except Exception as e:
            print(f"[MotivationLayer] ⚠ Θ event emission failed: {e}")

        # Persist motivation history
        try:
            history = []
            if self.log_path.exists():
                with open(self.log_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    if not isinstance(history, list):
                        history = []
            history.append(vector)
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(history[-500:], f, indent=2)
        except Exception as e:
            print(f"[MotivationLayer] ⚠ Failed to record drive vector: {e}")

        print(f"[🧩 Motivation] curiosity={vector['drives']['curiosity']:.3f}  "
              f"goal={vector['drives']['goal']:.3f}  need={vector['drives']['need']:.3f}  "
              f"SQI={vector['sqi']:.3f}  ΔH={vector['ΔH']:.3f}")
        return vector


# ───────────────────────────────────────────────
# Demo mode
# ───────────────────────────────────────────────
if __name__ == "__main__":
    layer = MotivationLayer()
    print("🧩 AION Motivation Layer — Resonant DriveVectors (Phase 63)\n")
    for i in range(5):
        v = layer.output_vector()
        time.sleep(0.6)