import os
import json
from datetime import datetime
from copy import deepcopy
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import measure_harmonic_coherence

class BestStateModule:
    def __init__(self, engine):
        self.engine = engine

    def _compute_score(self):
        """
        Computes a performance score based on:
        • Drift stability (lower = better)
        • Exhaust penalty (lower = better)
        • SQI correction effectiveness (bonus if SQI reduces drift)
        • Harmonic coherence (bonus for phase alignment)
        """
        drift_window = self.engine.resonance_filtered[-10:]
        drift_penalty = (max(drift_window) - min(drift_window)) if drift_window else 0.0
        exhaust_penalty = sum(e.get("impact_speed", 0) for e in self.engine.exhaust_log[-5:]) / max(len(self.engine.exhaust_log[-5:]), 1)
        harmonic_bonus = measure_harmonic_coherence(self.engine) * 0.5  # Weight harmonic coherence

        # ✅ SQI bonus: reward effective corrections
        sqi_bonus = 0.0
        if getattr(self.engine, "last_sqi_adjustments", {}):
            prev_drift = getattr(self.engine, "_prev_drift_for_score", drift_penalty)
            if drift_penalty < prev_drift:
                sqi_bonus = 0.3  # Drift improved since last SQI adjustment
            self.engine._prev_drift_for_score = drift_penalty

        # Clamp penalties to avoid runaway scores
        drift_penalty = min(drift_penalty, 5.0)
        exhaust_penalty = min(exhaust_penalty, 10.0)

        # Final weighted score
        score = -(drift_penalty * 1.5 + exhaust_penalty) + sqi_bonus + harmonic_bonus
        print(f"🏆 [Score] Drift={drift_penalty:.3f}, Exhaust={exhaust_penalty:.2f}, SQI Bonus={sqi_bonus:.2f}, Harmonics={harmonic_bonus:.2f} → Score={score:.4f}")
        return score

    def _update_best_state(self):
        """
        Updates engine.best_* if the current state outperforms the previous best.
        """
        score = self._compute_score()
        if self.engine.best_score is None or score > self.engine.best_score:
            self.engine.best_score = score
            self.engine.best_fields = deepcopy(self.engine.fields)
            self.engine.best_particles = deepcopy(self.engine.particles)
            print(f"🌟 New best state recorded: Score={score:.4f}")
            self._export_best_state()

    def _export_best_state(self):
        """
        Exports the engine's best-known state to a JSON file for persistence.
        Includes SQI state, harmonic snapshot, and timestamp.
        """
        os.makedirs(self.engine.LOG_DIR, exist_ok=True)
        best_path = os.path.join(self.engine.LOG_DIR, "qwave_best_state.json")
        data = {
            "fields": self.engine.best_fields,
            "particles": deepcopy(self.engine.best_particles),
            "score": self.engine.best_score,
            "sqi_enabled": self.engine.sqi_enabled,
            "last_sqi_adjustments": getattr(self.engine, "last_sqi_adjustments", {}),
            "harmonic_phase": self.engine.resonance_phase,
            "timestamp": datetime.utcnow().isoformat()
        }
        with open(best_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"💾 Best state exported: {best_path}")

    def auto_evaluate_and_export(self):
        """
        Auto-evaluate current engine state and export if improved.
        This can be called every tick or after stability checks.
        """
        self._update_best_state()