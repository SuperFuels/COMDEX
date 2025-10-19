"""
QQC Resonant Memory Channel
────────────────────────────
Maintains a temporal record of resonance state evolution (Φ_stability,
ε tolerance, and audit cadence). Enables predictive adjustments by
analyzing drift trends and coherence decay velocity.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from statistics import mean

MEMORY_PATH = Path("backend/state/qqc_resonant_memory.jsonl")
MAX_MEMORY = 100  # sliding window of last N entries

class ResonantMemory:
    def __init__(self):
        self.records = []
        MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._load_existing()

    # ──────────────────────────────────────────────
    def _load_existing(self):
        if MEMORY_PATH.exists():
            try:
                with open(MEMORY_PATH, "r") as f:
                    lines = f.readlines()[-MAX_MEMORY:]
                    self.records = [json.loads(line) for line in lines]
                print(f"[QQC::ResonantMemory] Restored {len(self.records)} prior entries.")
            except Exception as e:
                print(f"[QQC::ResonantMemory] ⚠ Failed to load history: {e}")

    # ──────────────────────────────────────────────
    def update(self, Φ_stability: float, tolerance: float, audit_freq: int):
        """Append a new record and compute predictive trends."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "Φ_stability": Φ_stability,
            "tolerance": tolerance,
            "audit_freq": audit_freq,
        }
        self.records.append(record)
        if len(self.records) > MAX_MEMORY:
            self.records.pop(0)

        with open(MEMORY_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")

        return self._analyze_trend()

    # ──────────────────────────────────────────────
    def _analyze_trend(self):
        """Compute ΔΦ, Δε, and predictive signal."""
        if len(self.records) < 3:
            return {"ΔΦ": 0.0, "Δε": 0.0, "prediction": "neutral"}

        short = self.records[-5:]
        long = self.records[-30:]

        Φ_short = mean(r["Φ_stability"] for r in short)
        Φ_long = mean(r["Φ_stability"] for r in long)
        ε_short = mean(r["tolerance"] for r in short)
        ε_long = mean(r["tolerance"] for r in long)

        ΔΦ = Φ_short - Φ_long
        Δε = ε_short - ε_long

        if ΔΦ < -0.02:
            prediction = "incoming_drift"
        elif ΔΦ > 0.05 and Δε < 0.2:
            prediction = "stabilizing"
        else:
            prediction = "steady"

        print(f"[QQC::ResonantMemory] ΔΦ={ΔΦ:+.4f}, Δε={Δε:+.4f} → {prediction}")
        return {"ΔΦ": ΔΦ, "Δε": Δε, "prediction": prediction}

    # ──────────────────────────────────────────────
    def summary(self):
        if not self.records:
            return {"entries": 0}
        last = self.records[-1]
        return {
            "entries": len(self.records),
            "last_Φ": last["Φ_stability"],
            "last_ε": last["tolerance"],
            "last_N": last["audit_freq"],
        }


# Singleton instance
_memory = ResonantMemory()

def record_memory(Φ_stability: float, tolerance: float, audit_freq: int):
    """Public callable for AION governor or telemetry modules."""
    return _memory.update(Φ_stability, tolerance, audit_freq)

def get_memory_summary():
    return _memory.summary()