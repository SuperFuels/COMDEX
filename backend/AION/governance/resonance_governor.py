"""
AION Resonance Governor
────────────────────────
Adaptive control layer linking Φ-stability and Φ-cognition metrics to
QQC tuning parameters. When coherence drift or cognitive disorder rises,
the governor tightens RLK tolerance and increases audit frequency until
stability recovers.

Now includes:
 * Live updates to QQC RLK runtime parameters (ε, audit interval)
 * Persistent state caching (`backend/state/qqc_rlk_state.json`)
 * Governance log tracking for every decision
 * Resonant Memory integration (ΔΦ, Δε predictive trend)
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.AION.telemetry.coherence_tracker import _tracker
from backend.AION.telemetry.cognitive_metrics import compute_cognitive_metrics
from backend.QQC.core.rlk_state import set_tolerance, set_audit_interval, get_state
from backend.QQC.core.resonant_memory import record_memory  # <- NEW

LOG_PATH = Path("backend/logs/governance/resonance_governor.jsonl")

# ──────────────────────────────────────────────
DEFAULT_TOLERANCE = 1.0
DEFAULT_AUDIT_FREQ = 10


class ResonanceGovernor:
    def __init__(self):
        self.current_tolerance = DEFAULT_TOLERANCE
        self.current_audit_freq = DEFAULT_AUDIT_FREQ
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────
    def evaluate(self):
        """Evaluate Φ-stability and Φ-cognition metrics, then apply live corrections."""
        Φ_state = _tracker.summary()
        cog = compute_cognitive_metrics()

        Φ_stab = Φ_state.get("Φ_stability_index", 0.0)
        Φ_load = cog.get("Φ_load", 0.0)
        Φ_entropy = cog.get("Φ_entropy", 0.0)

        # Default action
        action = "steady"

        # ─── Decision Heuristics ─────────────────────
        if Φ_stab < 0.05 or Φ_entropy > 0.5:
            # tighten: less tolerance, more frequent audits
            self.current_tolerance *= 0.5
            self.current_audit_freq = max(5, int(self.current_audit_freq / 2))
            action = "tighten"

        elif Φ_stab > 0.8 and Φ_entropy < 0.2:
            # relax: increase tolerance, reduce audit load
            self.current_tolerance *= 1.05
            self.current_audit_freq = min(20, int(self.current_audit_freq * 1.5))
            action = "relax"

        # Clamp bounds
        self.current_tolerance = min(max(self.current_tolerance, 1e-4), 2.0)

        # ─── Apply Live Updates ──────────────────────
        try:
            set_tolerance(self.current_tolerance)
            set_audit_interval(self.current_audit_freq)
        except Exception as e:
            print(f"[AION::Governor] ⚠ Failed to update QQC live state: {e}")

        # ─── Compose Summary Record ──────────────────
        state_snapshot = get_state()
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "Φ_stability": Φ_stab,
            "Φ_load": Φ_load,
            "Φ_entropy": Φ_entropy,
            "tolerance": state_snapshot.get("tolerance", self.current_tolerance),
            "audit_freq": state_snapshot.get("audit_interval", self.current_audit_freq),
            "action": action,
        }

        # ─── Persist Log ─────────────────────────────
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(summary) + "\n")

        # ─── Record into Resonant Memory (Task 10) ───
        try:
            record_memory(Φ_stab, self.current_tolerance, self.current_audit_freq)
        except Exception as e:
            print(f"[AION::Governor] ⚠ ResonantMemory update failed: {e}")

        print(f"[AION::Governor] action={action}, ε={self.current_tolerance:.4f}, N={self.current_audit_freq}")
        return summary


# ──────────────────────────────────────────────
# Singleton Governor Interface
# ──────────────────────────────────────────────
_governor = ResonanceGovernor()

def regulate():
    """Public helper callable from heartbeat loop."""
    return _governor.evaluate()