# ================================================================
# 🧩 Phase 45G.5 — Dual-Mode Cognitive Exercise Engine (Lexical + QMath)
# ================================================================
"""
Extends the adaptive CEE runtime to dual-mode operation.
Alternates between lexical-semantic and symbolic QMath exercises,
computes combined SQI metrics, and feeds results back to RMC.

Inputs:
    AION.brain.KGC (lexical atoms)
    backend.quant.qmath_core (symbolic generator)
    backend/modules/aion_language/resonant_memory_cache.py

Outputs:
    data/learning/cee_dual_sessions/<session_id>.json
    data/learning/cee_dual_metrics.json
"""

import json, time, logging, random
from pathlib import Path
from statistics import mean

from backend.modules.aion_knowledge import knowledge_graph_core as akg
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

# Optional: symbolic path
try:
    from backend.quant.qmath_core import QMath
except Exception:
    QMath = None  # fallback if symbolic backend not yet merged

logger = logging.getLogger(__name__)

SESSION_DIR = Path("data/learning/cee_dual_sessions")
METRICS_PATH = Path("data/learning/cee_dual_metrics.json")

RMC = ResonantMemoryCache()

# ================================================================
# 🧠 Dual-Mode Cognitive Exercise Engine
# ================================================================
class DualModeCEE:
    def __init__(self, mode: str = "dual"):
        self.mode = mode
        self.session_id = f"CEE-DUAL-{int(time.time())}"
        self.start_time = time.time()
        self.results = []
        self.active_atoms = []
        self.active_equations = []
        self.difficulty = 1.0
        self.emotional_tone = 0.6

    # ------------------------------------------------------------
    def load_atoms(self, limit: int = 5):
        """Pull lexical atoms from AION.brain.KGC."""
        nodes = [t["subject"] for t in akg.search()]  # fallback universal query
        self.active_atoms = random.sample(nodes, min(limit, len(nodes))) if nodes else []
        logger.info(f"[CEE-Dual] Loaded {len(self.active_atoms)} lexical atoms.")
        return self.active_atoms

    # ------------------------------------------------------------
    def generate_symbolic_tasks(self, count: int = 5):
        """Generate symbolic QMath tasks (placeholder / random templates)."""
        if not QMath:
            logger.warning("[CEE-Dual] QMath not available — symbolic mode skipped.")
            return []
        for _ in range(count):
            expr = QMath.random_equation(depth=2)  # assume generator exists
            self.active_equations.append(expr)
        logger.info(f"[CEE-Dual] Generated {len(self.active_equations)} symbolic tasks.")
        return self.active_equations

    # ------------------------------------------------------------
    def simulate_emotional_tone(self):
        """Simulated affective response."""
        self.emotional_tone = round(random.uniform(0.3, 0.9), 3)
        return self.emotional_tone

    # ------------------------------------------------------------
    def adjust_difficulty(self, sqi: float):
        if sqi > 0.85:
            self.difficulty = max(0.5, self.difficulty - 0.05)
        elif sqi < 0.65:
            self.difficulty = min(1.5, self.difficulty + 0.05)
        self.difficulty = round(self.difficulty, 3)

    # ------------------------------------------------------------
    def run_lexical_round(self):
        """Run lexical engagement tests."""
        self.simulate_emotional_tone()
        for atom in self.active_atoms:
            engagement = random.uniform(0.5, 1.0)
            resonance = random.uniform(0.8, 1.2)
            sqi = round(mean([engagement, resonance, self.emotional_tone]), 3)
            self.adjust_difficulty(sqi)
            self.results.append({
                "type": "lexical",
                "target": atom,
                "engagement": engagement,
                "resonance": resonance,
                "emotion": self.emotional_tone,
                "difficulty": self.difficulty,
                "SQI": sqi,
                "timestamp": time.time(),
            })
            logger.info(f"[CEE-Dual:Lex] {atom} SQI={sqi}")

    # ------------------------------------------------------------
    def run_symbolic_round(self):
        """Run symbolic (QMath) exercises."""
        if not self.active_equations:
            self.generate_symbolic_tasks()
        for eq in self.active_equations:
            coherence = random.uniform(0.7, 1.0)
            intensity = random.uniform(0.8, 1.1)
            symbolic_sqi = round(mean([coherence, intensity, self.emotional_tone]), 3)
            self.adjust_difficulty(symbolic_sqi)
            self.results.append({
                "type": "symbolic",
                "target": str(eq),
                "coherence": coherence,
                "intensity": intensity,
                "emotion": self.emotional_tone,
                "difficulty": self.difficulty,
                "SQI": symbolic_sqi,
                "timestamp": time.time(),
            })
            logger.info(f"[CEE-Dual:Sym] {eq} SQI={symbolic_sqi}")

    # ------------------------------------------------------------
    def feedback(self):
        """Feed results back into RMC."""
        photons = []
        for r in self.results:
            photons.append({
                "λ": r["target"],
                "φ": r.get("resonance", r.get("coherence", 1.0)),
                "μ": r["SQI"],
            })
        RMC.update_from_photons(photons)
        logger.info(f"[CEE-Dual] Feedback → ResonantMemoryCache ({len(photons)} entries)")

    # ------------------------------------------------------------
    def compute_metrics(self):
        sqis = [r["SQI"] for r in self.results]
        lex = [r for r in self.results if r["type"] == "lexical"]
        sym = [r for r in self.results if r["type"] == "symbolic"]
        summary = {
            "session_id": self.session_id,
            "mode": self.mode,
            "lexical_count": len(lex),
            "symbolic_count": len(sym),
            "avg_SQI": round(mean(sqis), 3) if sqis else 0,
            "timestamp": time.time(),
        }
        METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        json.dump(summary, open(METRICS_PATH, "w"), indent=2)
        logger.info(f"[CEE-Dual] Metrics exported → {METRICS_PATH}")
        return summary

    # ------------------------------------------------------------
    def export_session(self):
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        session_path = SESSION_DIR / f"{self.session_id}.json"
        json.dump({
            "session_id": self.session_id,
            "mode": self.mode,
            "results": self.results,
            "timestamp": self.start_time,
        }, open(session_path, "w"), indent=2)
        logger.info(f"[CEE-Dual] Session exported → {session_path}")

    # ------------------------------------------------------------
    def run_full_cycle(self):
        """Run complete dual-mode adaptive session with GHX + Habit feedback."""
        logger.info(f"🧠 Starting Dual-Mode CEE session [{self.session_id}]")

        # Phase 1 — Dual-Mode Cognitive Execution
        self.load_atoms()
        self.generate_symbolic_tasks()
        self.run_lexical_round()
        self.run_symbolic_round()
        self.feedback()

        # Phase 2 — Metrics & Session Export
        summary = self.compute_metrics()
        self.export_session()

        # ------------------------------------------------------------
        # 🔭 Phase 45G.11 — GHX Telemetry Bridge (Resonance & Gradient Metrics)
        # ------------------------------------------------------------
        try:
            from backend.bridges.ghx_telemetry_bridge import GHXTelemetryBridge
            from backend.quant.qgradient import collapse_gradient
            from backend.quant.qtensor.qtensor_field import random_field

            ghx = GHXTelemetryBridge()

            for r in self.results:
                # Default resonance placeholders
                ρ = r.get("coherence", random.uniform(0.7, 1.0))
                I = r.get("intensity", random.uniform(0.8, 1.1))
                φ = random.uniform(-3.14, 3.14)

                # Simulate gradient coherence (ρ∇ψ)
                ψ = random_field((4, 4))
                grad_data = collapse_gradient(ψ)
                ρ_grad = grad_data.get("ρ", 0.8)

                ghx.emit({
                    "session_id": self.session_id,
                    "mode": self.mode,
                    "atom": r.get("target"),
                    "type": r.get("type"),
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


    # ------------------------------------------------------------
    def generate_exercise(self, term: str, level: int = 1):
        """Generate a simple lexical or symbolic exercise for a term."""
        qset = [
            {
                "prompt": f"What is the meaning or symbolic association of '{term}'?",
                "answer": f"{term} relates to {random.choice(['energy', 'motion', 'balance', 'structure'])}",
                "feedback": "Good reflection on resonance meaning."
            },
            {
                "prompt": f"Express '{term}' in symbolic QMath (level {level})",
                "answer": f"Ψ({term}) = ρ⊕Ī",
                "feedback": "Resonance symbol recognized."
            },
        ]
        return {"term": term, "level": level, "questions": qset}

    # ------------------------------------------------------------
    def evaluate_answer(self, question: dict, answer: str):
        """Evaluate an answer and produce feedback with SQI."""
        sqi = round(random.uniform(0.6, 0.95), 3)
        feedback = random.choice([
            "Excellent associative clarity.",
            "Moderate symbolic linkage.",
            "Needs stronger resonance mapping."
        ])
        return {"SQI": sqi, "feedback": feedback}

    # ------------------------------------------------------------
    def simulate_session(self, level: int = 1):
        """Simulate a full cognitive session (Wordwall style)."""
        self.run_full_cycle()
        summary = self.compute_metrics()
        return {"session": self.session_id, "level": level, "avg_SQI": summary.get("avg_SQI", 0)}

    # ------------------------------------------------------------
    def query(self, question: str):
        """Lightweight semantic answer generator for cognitive Q&A."""
        concept = random.choice(self.active_atoms or ["resonance", "energy", "coherence"])
        return f"{concept.capitalize()} oscillates around the idea: '{question}'."

# ================================================================
# CLI Entry
# ================================================================
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    cee = DualModeCEE()
    summary = cee.run_full_cycle()
    print(json.dumps(summary, indent=2))