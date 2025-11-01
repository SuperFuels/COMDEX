import json, time
from pathlib import Path
from statistics import mean
from backend.modules.aion_language.goal_motivation_calibrator import CAL
from backend.modules.aion_language.goal_reinforcement import REINF

LOG_PATH = Path("data/goals/motivation_resonance_log.json")
OUT_PATH = Path("data/goals/motivation_persistence_log.json")

class TemporalMotivationPersistence:
    def __init__(self):
        self.persistence_index = 0.0
        self.window_size = 10

    def compute_persistence(self):
        """Compute rolling persistence from last N calibration cycles."""
        if not LOG_PATH.exists():
            print("[MOTIVE] ⚠️ No motivation log found.")
            return None
        try:
            data = json.load(open(LOG_PATH))
        except Exception:
            print("[MOTIVE] ⚠️ Could not parse motivation log.")
            return None
        if not isinstance(data, list):
            return None
        records = data[-self.window_size:]
        if not records:
            return None

        stabilities = [r.get("stability", 0.5) for r in records]
        drifts = [r.get("drift", 0.0) for r in records]

        avg_stab = mean(stabilities)
        avg_drift = mean(drifts)
        self.persistence_index = round(avg_stab - 0.5 * avg_drift, 3)
        self._update_reinforcement()
        self._save(avg_stab, avg_drift)
        print(f"[MOTIVE] 🔄 Persistence index={self.persistence_index} (avg_stab={avg_stab:.2f}, avg_drift={avg_drift:.2f})")
        return self.persistence_index

    def _update_reinforcement(self):
        """Apply smoothing to REINF learning parameters."""
        if hasattr(REINF, "learning_rate"):
            REINF.learning_rate = round(REINF.learning_rate * (0.8 + 0.4 * self.persistence_index), 3)
            print(f"[MOTIVE] ⚙️ Adjusted learning_rate -> {REINF.learning_rate}")

    def _save(self, avg_stab, avg_drift):
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": time.time(),
            "persistence_index": self.persistence_index,
            "avg_stability": avg_stab,
            "avg_drift": avg_drift
        }
        if OUT_PATH.exists():
            try:
                data = json.load(open(OUT_PATH))
            except Exception:
                data = []
        else:
            data = []
        data.append(record)
        with open(OUT_PATH, "w") as f:
            json.dump(data[-50:], f, indent=2)

try:
    MOTIVE
except NameError:
    MOTIVE = TemporalMotivationPersistence()
    print("🧭 TemporalMotivationPersistence global instance initialized as MOTIVE")