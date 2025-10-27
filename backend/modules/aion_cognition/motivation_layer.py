# backend/modules/aion_cognition/motivation_layer.py
# ───────────────────────────────────────────────
# 🧩 Motivation Layer — Resonant Version
# Generates DriveVectors (curiosity, goal, need)
# and reinforces performance via ResonantReinforcementMixin
# ───────────────────────────────────────────────

import os, json, time, math, random
from pathlib import Path
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.reinforcement_mixin import ResonantReinforcementMixin


class MotivationLayer(ResonantReinforcementMixin):
    def __init__(self, cache_path: str = "data/memory/resonant_memory_cache.json"):
        super().__init__(name="motivation_layer", learning_rate=0.05)
        self.rmc = ResonantMemoryCache()
        self.cache_path = cache_path
        self.log_path = Path("data/memory/motivation_history.json")
        os.makedirs(self.log_path.parent, exist_ok=True)

        # Initialize drive states
        self.drives = {"curiosity": 0.0, "goal": 0.0, "need": 0.0}
        self.last_entropy = 0.0
        self.last_sqi = getattr(self.heartbeat, "sqi", 0.6)

    # ───────────────────────────────────────────
    # Core sampling and computation
    # ───────────────────────────────────────────
    def compute_entropy(self) -> float:
        """
        Compute environmental entropy from the Resonant Memory Cache.
        If unavailable, fall back to stochastic noise.
        """
        try:
            coherence_vals = [v.get("coherence", 0.5) for v in self.rmc.cache.values() if isinstance(v, dict)]
            entropy = 1.0 - sum(coherence_vals) / len(coherence_vals) if coherence_vals else random.uniform(0.3, 0.9)
            self.last_entropy = round(entropy, 3)
            return self.last_entropy
        except Exception:
            self.last_entropy = random.uniform(0.3, 0.9)
            return self.last_entropy

    def generate_drive_vector(self) -> dict:
        """
        Generates a normalized DriveVector influenced by entropy, SQI, and reinforcement feedback.
        - Curiosity grows with entropy.
        - Goal stabilizes around coherence (inverse entropy).
        - Need responds to low SQI (self-improvement urge).
        """
        entropy = self.compute_entropy()
        sqi = float(getattr(self.heartbeat, "sqi", 0.6))

        # Drive formation (raw)
        curiosity = entropy * random.uniform(0.8, 1.2)
        goal = (1.0 - entropy) * random.uniform(0.7, 1.1)
        need = (1.0 - sqi) * random.uniform(0.6, 1.2)

        # Normalize
        total = max(curiosity + goal + need, 1e-6)
        self.drives = {
            "curiosity": round(curiosity / total, 3),
            "goal": round(goal / total, 3),
            "need": round(need / total, 3),
        }
        return self.drives

    # ───────────────────────────────────────────
    # Output + reinforcement + persistence
    # ───────────────────────────────────────────
    def output_vector(self) -> dict:
        """
        Outputs the current drive vector, logs it, and updates resonance feedback.
        """
        vector = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "drives": self.generate_drive_vector(),
            "entropy": self.last_entropy,
            "sqi": getattr(self.heartbeat, "sqi", 0.6),
        }

        # Compute alignment score — higher if drives are balanced and coherent
        balance = 1.0 - abs(max(vector["drives"].values()) - min(vector["drives"].values()))
        alignment_score = round((balance + (1.0 - vector["entropy"]) + vector["sqi"]) / 3.0, 3)

        # Reinforce
        self.update_resonance_feedback(outcome_score=alignment_score, reason="Drive vector alignment")

        # Persist to motivation history
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

        return vector


# ───────────────────────────────────────────────
# Demo mode
# ───────────────────────────────────────────────
if __name__ == "__main__":
    layer = MotivationLayer()
    print("🧩 AION Motivation Layer — Resonant DriveVectors\n")
    for i in range(5):
        v = layer.output_vector()
        drives = v["drives"]
        print(f"[{i+1}] curiosity={drives['curiosity']:.3f}  goal={drives['goal']:.3f}  need={drives['need']:.3f}  "
              f"entropy={v['entropy']:.3f}  sqi={v['sqi']:.3f}")
        time.sleep(0.5)