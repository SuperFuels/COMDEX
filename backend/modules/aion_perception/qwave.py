# ================================================================
# File: backend/modules/aion_perception/qwave.py
# Tessaris SQI Field Stub - Resonance Synchronization Layer (v1.4)
# ================================================================
import json
import os
import math
from datetime import datetime

class SQIField:
    """Adaptive SQI resonance feedback and PAL alignment layer."""
    def __init__(self):
        self.feedback_enabled = False
        # baseline state
        self.state = {"epsilon": 0.5, "k": 10, "weight": 1.0, "stability": 0.0}

    @classmethod
    def load_last_state(cls):
        """Load last known PAL/SQI state if available."""
        instance = cls()
        path = "data/pal_state.json"
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    instance.state = json.load(f)
                print(f"🔁 Loaded previous SQI state -> ε={instance.state.get('epsilon',0):.3f}, "
                      f"k={instance.state.get('k',0)}, w={instance.state.get('weight',1.0):.2f}")
            except Exception as e:
                print(f"⚠️ Failed to load SQI state: {e}")
        return instance

    def enable_feedback(self, enabled: bool = True):
        self.feedback_enabled = enabled
        print(f"🧠 SQI feedback {'enabled' if enabled else 'disabled'}")

    def apply(self, pulse):
        """Apply a resonance pulse to modify internal SQI state."""
        # Support both dict and ResonancePulse object
        if hasattr(pulse, "to_dict"):
            delta = pulse.to_dict()
        elif isinstance(pulse, dict):
            delta = pulse
        else:
            raise TypeError("pulse must be a ResonancePulse or dict-like")

        # --- adaptive damping factor (tuned for faster lock) ---
        base_damp = float(delta.get("damping", 0.9))
        adaptive_damp = base_damp + (0.07 * (1.0 - float(delta.get("coherence", 0.9))))
        adaptive_damp = min(max(adaptive_damp, 0.75), 0.98)

        # --- weighted gain adjustment (increased sensitivity) ---
        gain = float(delta.get("gain", 0.3))
        gain_factor = (gain - 0.5) * 0.12 * (1.0 + 0.5 * float(delta.get("coherence", 1.0)))

        # --- update epsilon & weight ---
        self.state["epsilon"] = max(0.0, float(self.state["epsilon"]) + float(delta.get("epsilon_bias", 0.0)))
        self.state["weight"] *= 1 + gain_factor
        self.state["weight"] *= adaptive_damp

        # --- stability metric (approaches 1.0 at equilibrium) ---
        stability = math.exp(-abs(self.state["epsilon"] - 0.43) * 10)
        self.state["stability"] = round(stability, 3)

        print(
            f"🔁 SQI feedback applied -> ε={self.state['epsilon']:.3f}, "
            f"w={self.state['weight']:.3f}, damp={adaptive_damp:.3f}, "
            f"gain={gain:.2f}, ⟲={self.state['stability']:.3f}"
        )

        # --- check for equilibrium lock ---
        if self.state["stability"] > 0.975 and 0.42 <= self.state["epsilon"] <= 0.44:
            print("✅ Resonant equilibrium detected - field stabilized.")
            self.save_checkpoint(tag="equilibrium_lock")

    def sync_pal_state(self, epsilon_target: float, k: int, weight_bias: float, commit: bool = False):
        """Synchronize SQI parameters back into PAL."""
        self.state.update({
            "epsilon": epsilon_target,
            "k": k,
            "weight": round(self.state["weight"] + weight_bias, 3)
        })
        if commit:
            path = "data/pal_state.json"
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                json.dump(self.state, f, indent=2)
            print(f"💾 SQI->PAL state committed -> ε={self.state['epsilon']:.3f}, "
                  f"k={self.state['k']}, w={self.state['weight']:.2f}")
        return type("PALState", (), self.state)

    def save_checkpoint(self, tag: str = "SQI_checkpoint"):
        path = f"data/sqi_checkpoint_{tag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.state, f, indent=2)
        print(f"💾 SQI checkpoint saved -> {path}")

# === Meta-Equilibrium Controller (F18) ======================================
import json, os, time
from collections import defaultdict
from typing import Dict

META_STATE_PATH = "data/resonance/meta_equilibrium_state.jsonl"

class MetaEquilibrium:
    """
    F18-style global equalizer: gently pulls per-domain epsilon_i toward
    epsilon_eq = mean(epsilon_i), with damping zeta (0.02 by default).
    """
    def __init__(self, zeta: float = 0.02):
        self.zeta = float(zeta)
        self.epsilon_by_domain: Dict[str, float] = defaultdict(lambda: 0.43)

    def update(self, domain: str, epsilon_i: float) -> float:
        # Track domain epsilon
        self.epsilon_by_domain[domain] = float(epsilon_i)

        # Global mean
        eps_eq = sum(self.epsilon_by_domain.values()) / max(1, len(self.epsilon_by_domain))

        # F18 rule: d eps_i = -zeta (eps_i - eps_eq)
        delta = -self.zeta * (epsilon_i - eps_eq)

        # Log a compact telemetry record
        os.makedirs(os.path.dirname(META_STATE_PATH), exist_ok=True)
        rec = {
            "t": time.time(),
            "domain": domain,
            "epsilon_i": round(epsilon_i, 6),
            "epsilon_eq": round(eps_eq, 6),
            "zeta": self.zeta,
            "delta": round(delta, 6),
            "spread": round(self._spread(), 9),
        }
        with open(META_STATE_PATH, "a") as f:
            f.write(json.dumps(rec) + "\n")

        return delta  # add this to epsilon as a tiny bias

    def _spread(self) -> float:
        vals = list(self.epsilon_by_domain.values())
        if len(vals) <= 1:
            return 0.0
        m = sum(vals) / len(vals)
        return sum((v - m) ** 2 for v in vals) / len(vals)

# Singleton helper
_meta_eq = MetaEquilibrium(zeta=0.02)

def meta_eq_bias(domain: str, epsilon_i: float) -> float:
    """Return a small epsilon bias to nudge domain -> global mean (F18)."""
    return _meta_eq.update(domain, epsilon_i)
# =========================================================================== 

class ResonancePulse:
    """Encapsulates SQI resonance parameters for feedback injection."""
    def __init__(self, frequency, coherence, gain, damping, epsilon_bias=0.0):
        self.frequency = frequency
        self.coherence = coherence
        self.gain = gain
        self.damping = damping
        self.epsilon_bias = epsilon_bias  # ✅ fix: make this optional default

    def to_dict(self):
        return {
            "frequency": self.frequency,
            "coherence": self.coherence,
            "gain": self.gain,
            "damping": self.damping,
            "epsilon_bias": self.epsilon_bias
        }