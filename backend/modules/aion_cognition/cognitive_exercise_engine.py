# ================================================================
# 🧩 Phase 45G.4 — Adaptive Cognitive Exercise Engine (CEE+)
# ================================================================
"""
Manages adaptive cognitive sessions that self-tune difficulty and
emotional feedback based on resonance metrics (SQI) and memory stability.

Inputs:
    AION.brain.KGC
    backend/modules/aion_language/resonant_memory_cache.py

Outputs:
    data/learning/cee_sessions/<session_id>.json
    data/learning/cee_adaptive_metrics.json
"""

import json, time, logging, random
from pathlib import Path
from statistics import mean

from backend.modules.aion_knowledge import knowledge_graph_core as akg
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

logger = logging.getLogger(__name__)

SESSION_DIR = Path("data/learning/cee_sessions")
METRICS_PATH = Path("data/learning/cee_adaptive_metrics.json")


# ================================================================
# 🧠 Adaptive Cognitive Exercise Engine
# ================================================================
class CognitiveExerciseEngine:
    def __init__(self, mode: str = "lexical"):
        self.mode = mode
        self.session_id = f"CEE-{int(time.time())}"
        self.start_time = time.time()
        self.results = []
        self.active_atoms = []
        self.difficulty = 1.0  # base difficulty scale 1.0 = normal
        self.emotional_tone = 0.5  # 0=negative, 1=positive
        self.resonance_weight = 1.0
        self.rmc = ResonantMemoryCache()  # instantiate memory cache interface

    # ------------------------------------------------------------
    def load_atoms(self, limit: int = 5):
        """Pull lexical atoms (concepts) from AION.brain.KGC."""
        akg.load_knowledge()
        all_atoms = list({s for (s, _, _) in akg.triplets.keys()})
        if not all_atoms:
            logger.warning("[CEE] No atoms found in AION.brain.KGC — check AKG load.")
            return []
        self.active_atoms = random.sample(all_atoms, min(limit, len(all_atoms)))
        logger.info(f"[CEE] Loaded {len(self.active_atoms)} active atoms for session.")
        return self.active_atoms

    # ------------------------------------------------------------
    def simulate_emotional_tone(self):
        """Mock or integrate emotional state (placeholder for bio/affective sensors)."""
        self.emotional_tone = round(random.uniform(0.3, 0.9), 3)
        logger.info(f"[CEE] Emotional tone set to {self.emotional_tone}")
        return self.emotional_tone

    # ------------------------------------------------------------
    def adjust_difficulty(self, sqi: float):
        """Dynamically adjust difficulty based on SQI trend."""
        if sqi > 0.85:
            self.difficulty = max(0.5, self.difficulty - 0.05)
        elif sqi < 0.65:
            self.difficulty = min(1.5, self.difficulty + 0.05)
        self.difficulty = round(self.difficulty, 3)
        logger.info(f"[CEE] Adjusted difficulty → {self.difficulty}")

    # ------------------------------------------------------------
    def run_session(self):
        """Run an adaptive cognitive exercise session."""
        if not self.active_atoms:
            self.load_atoms()

        self.simulate_emotional_tone()

        for atom in self.active_atoms:
            engagement = random.uniform(0.5, 1.0)
            resonance = random.uniform(0.8, 1.2)
            sqi = round(mean([engagement, resonance, self.emotional_tone]), 3)

            self.adjust_difficulty(sqi)

            result = {
                "atom": atom,
                "engagement": engagement,
                "resonance": resonance,
                "emotion": self.emotional_tone,
                "difficulty": self.difficulty,
                "SQI": sqi,
                "timestamp": time.time(),
            }
            self.results.append(result)
            logger.info(f"[CEE] {atom} SQI={sqi} | tone={self.emotional_tone} | diff={self.difficulty}")

        return self.results

    # ------------------------------------------------------------
    def feedback(self):
        """Feed resonance/emotional data back into memory."""
        photons = []
        for r in self.results:
            photons.append({
                "λ": r["atom"],
                "φ": r["resonance"],
                "μ": r["SQI"],
            })
        self.rmc.update_from_photons(photons)
        logger.info("[CEE] Feedback propagated to ResonantMemoryCache.")

    # ------------------------------------------------------------
    def compute_adaptive_metrics(self):
        """Aggregate session-level metrics for telemetry."""
        sqis = [r["SQI"] for r in self.results]
        emotions = [r["emotion"] for r in self.results]
        diff = [r["difficulty"] for r in self.results]
        summary = {
            "session_id": self.session_id,
            "mode": self.mode,
            "avg_SQI": round(mean(sqis), 3) if sqis else 0,
            "avg_emotion": round(mean(emotions), 3) if emotions else 0,
            "avg_difficulty": round(mean(diff), 3) if diff else 0,
            "timestamp": time.time(),
        }

        METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(METRICS_PATH, "w") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"[CEE] Adaptive metrics exported → {METRICS_PATH}")
        return summary

    # ------------------------------------------------------------
    def export_session(self):
        """Export detailed session log."""
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        session_path = SESSION_DIR / f"{self.session_id}.json"
        with open(session_path, "w") as f:
            json.dump({
                "session_id": self.session_id,
                "mode": self.mode,
                "results": self.results,
                "timestamp": self.start_time,
            }, f, indent=2)
        logger.info(f"[CEE] Exported session log → {session_path}")

    # ------------------------------------------------------------
    def run_full_cycle(self):
        """Run complete adaptive session pipeline with GHX + Habit feedback."""
        logger.info(f"🧠 Starting adaptive CEE session [{self.session_id}]")

        # Phase 1 — Core adaptive session
        self.load_atoms()
        self.run_session()
        self.feedback()

        # Phase 2 — Compute metrics + export
        summary = self.compute_adaptive_metrics()
        self.export_session()

        # ------------------------------------------------------------
        # 🔭 Phase 45G.11 — GHX Telemetry Bridge (Resonance-Enhanced)
        # ------------------------------------------------------------
        try:
            from backend.bridges.ghx_telemetry_bridge import GHXTelemetryBridge
            from backend.quant.qtensor.qtensor_field import random_field
            from backend.quant.qgradient import collapse_gradient

            ghx = GHXTelemetryBridge()

            for r in self.results:
                # baseline resonance estimates
                ρ = r.get("resonance", random.uniform(0.7, 1.0))
                I = random.uniform(0.8, 1.1)
                φ = random.uniform(-3.14, 3.14)

                # gradient coherence from field simulation
                ψ = random_field((4, 4))
                grad_data = collapse_gradient(ψ)
                ρ_grad = grad_data.get("ρ", 0.8)

                ghx.emit({
                    "session_id": self.session_id,
                    "mode": self.mode,
                    "atom": r.get("atom"),
                    "SQI": r.get("SQI"),
                    "emotion": r.get("emotion"),
                    "difficulty": r.get("difficulty"),
                    "ρ": ρ,
                    "I": I,
                    "ρ∇ψ": ρ_grad,
                    "phase": φ,
                })

            ghx_summary = ghx.summarize()
            logger.info(f"[CEE] GHX Telemetry summary → {ghx_summary}")

        except Exception as e:
            logger.warning(f"[CEE] GHX Telemetry failed: {e}")
            ghx_summary = {}

        # ------------------------------------------------------------
        # 🌀 Phase 45G.8 — Auto-Habit Feedback Integration
        # ------------------------------------------------------------
        try:
            from backend.modules.aion_cognition.habit_engine_bridge import HabitEngineBridge
            habit = HabitEngineBridge()

            # detect available update method
            if hasattr(habit, "update_from_telemetry"):
                habit_state = habit.update_from_telemetry()
            elif hasattr(habit, "update_state"):
                habit_state = habit.update_state()
            else:
                habit_state = None
                logger.warning("[CEE] No valid habit update method found.")

            if habit_state:
                summary["habit_strength"] = habit_state.get("habit_strength", 0)
                logger.info(f"[CEE] HabitEngine auto-update → {habit_state}")
            else:
                logger.warning("[CEE] HabitEngine update skipped (no telemetry found).")

        except Exception as e:
            logger.warning(f"[CEE] HabitEngine integration failed: {e}")

# ================================================================
# CLI Entry
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cee = CognitiveExerciseEngine(mode="lexical")
    summary = cee.run_full_cycle()
    print("✅ Adaptive Cognitive Exercise Engine session complete.")
    print(json.dumps(summary, indent=2))