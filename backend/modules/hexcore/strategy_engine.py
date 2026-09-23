"""
🎯 StrategyEngine - Resonant Strategic Reasoning Core
──────────────────────────────────────────────────────────────
Phase 55 upgrade:
Integrates Θ resonance, context entropy, and ethics metrics into
planning evaluation and optimization.

Features:
  * Θ heartbeat coupling -> reasoning temperature modulation
  * RMC coherence feedback -> adaptive weighting
  * Ethics influence -> bias correction for moral alignment
  * Plan coherence scoring -> symbolic + semantic evaluation
"""
import time
import math
import random
import json
from datetime import datetime
from pathlib import Path

# ✅ DNA switch for upgrade tracking
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# ⚛ Resonance + ethics subsystems
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

# Optional ethics weighting (safe import)
try:
    from backend.modules.consciousness.ethics_engine import EthicsEngine
except Exception:
    EthicsEngine = None

STATE_FILE = Path("data/analysis/strategy_engine_state.json")
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


class StrategyEngine:
    def __init__(self):
        self.temperature = 0.5              # reasoning entropy temperature (0-1)
        self.last_eval = None
        self.last_resonance = 0.7
        self.last_ethics = 1.0
        self.rmc = ResonantMemoryCache()
        self.Θ = ResonanceHeartbeat(namespace="strategy_engine")
        self.ethics = EthicsEngine() if EthicsEngine else None
        self.Θ.register_listener(self._on_heartbeat)

    # ─────────────────────────────────────────────────────────────
    # 🔄 Resonance coupling
    def _on_heartbeat(self, metrics):
        """Dynamic adjustment from Θ feedback."""
        drift = metrics.get("resonance_drift", 0.0)
        sqi = metrics.get("sqi", 0.7)
        stability = metrics.get("stability", 0.6)
        # Adjust reasoning temperature using entropy drift
        delta_T = (0.5 - stability) * 0.1 + drift * 0.05
        self.temperature = max(0.1, min(1.0, self.temperature + delta_T))
        self.last_resonance = sqi
        self._save_state()

    # ─────────────────────────────────────────────────────────────
    # 🧭 Evaluation logic
    def evaluate(self, plan):
        """
        Evaluate a plan's symbolic and harmonic viability.
        Uses resonance, ethics, and entropy-adjusted scoring.
        """
        goal = plan.get("goal", "undefined")
        base_score = self._semantic_alignment(goal)
        resonance_score = self.rmc.get("last_exported_strategy", {}).get("count", 1) / 2500
        resonance_score = min(1.0, resonance_score)

        ethics_weight = 1.0
        if self.ethics:
            ethics_weight = self.ethics.evaluate_alignment(goal)
        ethics_weight = max(0.3, min(1.2, ethics_weight))

        temp_factor = 1 - abs(self.temperature - 0.5)
        final_score = (base_score * 0.5 + resonance_score * 0.3 + temp_factor * 0.2) * ethics_weight
        final_score = round(final_score, 3)
        self.last_eval = final_score

        self._log_evaluation(goal, final_score, base_score, resonance_score, ethics_weight)
        return final_score

    # ─────────────────────────────────────────────────────────────
    def _semantic_alignment(self, goal: str):
        """Deterministic advisory coherence score."""
        cache = self.rmc.lookup(goal)
        if cache and "sqi" in cache:
            return cache["sqi"]
        words = {word.strip(".,:;!?()[]{}").lower() for word in str(goal).split()}
        specificity = min(0.24, max(0, len(words) - 2) * 0.02)
        verification = 0.12 if words.intersection({"verify", "test", "measure", "evidence", "validate"}) else 0.0
        ambiguity = 0.12 if words.intersection({"anything", "somehow", "whatever"}) else 0.0
        return round(max(0.1, min(0.95, 0.46 + specificity + verification - ambiguity)), 3)

    # ─────────────────────────────────────────────────────────────
    def adjust_temperature(self, delta: float):
        self.temperature = max(0.1, min(1.0, self.temperature + delta))
        self._save_state()

    # ─────────────────────────────────────────────────────────────
    def choose_best(self, plans):
        """
        Evaluate a list of plans and choose the highest-resonance candidate.
        """
        if not plans:
            return None
        scored = [(p, self.evaluate(p)) for p in plans]
        best_plan, best_score = max(scored, key=lambda x: x[1])
        print(f"[🎯] Best plan selected -> {best_plan.get('goal')} (score={best_score:.3f})")
        return best_plan

    # ─────────────────────────────────────────────────────────────
    def _log_evaluation(self, goal, final, base, res, ethics):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "goal": goal,
            "base": base,
            "resonance": res,
            "ethics": ethics,
            "temperature": round(self.temperature, 3),
            "final": final
        }
        STATE_FILE.write_text(json.dumps(entry, indent=2))

    # ─────────────────────────────────────────────────────────────
    def _save_state(self):
        state = {
            "temperature": round(self.temperature, 3),
            "last_eval": self.last_eval,
            "last_resonance": self.last_resonance,
            "last_ethics": self.last_ethics
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    # ─────────────────────────────────────────────────────────────
    def get_state(self):
        return {
            "temperature": self.temperature,
            "last_eval": self.last_eval,
            "last_resonance": self.last_resonance,
            "last_ethics": self.last_ethics
        }

    def execute_plan(self, plan: dict, execution_adapter=None):
        """Execute only through an explicitly authorized, verifiable adapter.

        The former stub returned ``executed`` without doing anything.  A plan
        without an adapter now remains an honest proposal.
        """
        from backend.modules.hexcore.governed_cognitive_contract import (
            CognitiveActionContract,
            execute_with_authority,
        )

        contract = CognitiveActionContract.from_mapping({
            **dict(plan),
            "objective": plan.get("objective") or plan.get("goal") or "",
        })
        return execute_with_authority(contract, execution_adapter)

# 🧪 Local diagnostic run
if __name__ == "__main__":
    engine = StrategyEngine()
    plans = [
        {"goal": "optimize harmonic resonance"},
        {"goal": "increase stability of awareness feedback"},
        {"goal": "enhance moral alignment"}
    ]
    engine.choose_best(plans)
    print(engine.get_state())
