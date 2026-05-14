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
        self.state = {"epsilon": 0.0, "k": 10, "weight": 1.0, "stability": 0.0}
        # debounced lock counter (kept as attribute)
        self._stable_run = 0

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
        # NOTE: epsilon is currently managed in PAL core; keep this disabled for now.
        # self.state["epsilon"] = max(0.0, float(self.state["epsilon"]) + float(delta.get("epsilon_bias", 0.0)))

        self.state["weight"] *= (1 + gain_factor)
        self.state["weight"] *= adaptive_damp

        # Safety rail: don’t let weight decay to ~0 forever (keeps stability from flatlining)
        self.state["weight"] = float(min(max(self.state["weight"], 0.10), 5.00))

        # --- stability metric (approaches 1.0 at equilibrium) ---
        w = float(self.state.get("weight", 1.0))
        coh = float(delta.get("coherence", 1.0))
        # stability rises with coherence and reasonable weight; saturates near 1
        stability = 1.0 - math.exp(-max(0.0, (w * coh)) * 0.8)
        self.state["stability"] = round(stability, 3)

        print(
            f"🔁 SQI feedback applied -> w={self.state['weight']:.3f}, "
            f"damp={adaptive_damp:.3f}, gain={gain:.2f}, ⟲={self.state['stability']:.3f}"
        )

        # ------------------------------------------------------------------
        # NEW: Debounced equilibrium lock (prevents false-positive “one hit” locks)
        # Lock only if stable for last N pulses AND coherence is high.
        # ------------------------------------------------------------------
        self._stable_run = getattr(self, "_stable_run", 0)

        if self.state.get("stability", 0.0) > 0.97 and coh > 0.98:
            self._stable_run += 1
        else:
            self._stable_run = 0

        if self._stable_run >= 8:
            print("✅ Resonant equilibrium confirmed (debounced) - field stabilized.")
            self.save_checkpoint(tag="equilibrium_lock")
            # prevent repeated checkpoint spam
            self._stable_run = 0

        # ------------------------------------------------------------------
        # OLD: single-shot equilibrium lock (kept commented out as requested)
        # ------------------------------------------------------------------
        # # --- check for equilibrium lock ---
        # coh = float(delta.get("coherence", 1.0))
        # if self.state.get("stability", 0.0) > 0.975 and coh > 0.98:
        #     print("✅ Resonant equilibrium detected - field stabilized.")
        #     self.save_checkpoint(tag="equilibrium_lock")

    def sync_pal_state(self, epsilon_target: float, k: int, weight_bias: float, commit: bool = False):
        """Synchronize SQI parameters back into PAL."""
        self.state.update({
            "epsilon": epsilon_target,
            "k": k,
            "weight": round(self.state["weight"] + weight_bias, 3)
        })
        if commit:
            path = "data/prediction/pal_state.json"
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
    epsilon_eq = mean(epsilon_i), with damping zeta.

    IMPORTANT:
    - With only ONE real domain, mean(epsilon_i) == epsilon_i => delta == 0.
    - We therefore keep a persistent __global__ anchor entry so eps_eq is
      meaningful even when there's only one domain.
    """
    def __init__(
        self,
        zeta: float = 0.02,
        anchor: float = 0.245,          # pick your PAL operating center (was ~0.245 in logs)
        anchor_weight: float = 1.0,     # >1 makes anchor pull stronger vs domains
    ):
        self.zeta = float(zeta)
        self.anchor_domain = "__global__"
        self.anchor_weight = float(anchor_weight)

        # Default new domains to anchor (not 0.43)
        self.epsilon_by_domain: Dict[str, float] = defaultdict(lambda: float(anchor))

        # Seed the anchor (persistent, never overwritten by domains)
        self.epsilon_by_domain[self.anchor_domain] = float(anchor)

    def update(self, domain: str, epsilon_i: float) -> float:
        # Track domain epsilon
        eps_i = float(epsilon_i)
        self.epsilon_by_domain[domain] = eps_i

        # Weighted global mean including the anchor
        vals = []
        wts = []

        # anchor
        vals.append(self.epsilon_by_domain[self.anchor_domain])
        wts.append(self.anchor_weight)

        # domains (exclude anchor key)
        for k, v in self.epsilon_by_domain.items():
            if k == self.anchor_domain:
                continue
            vals.append(float(v))
            wts.append(1.0)

        wsum = sum(wts) if wts else 1.0
        eps_eq = sum(v * w for v, w in zip(vals, wts)) / wsum

        # F18 rule: d eps_i = -zeta (eps_i - eps_eq)
        delta = -self.zeta * (eps_i - eps_eq)

        # Log telemetry
        os.makedirs(os.path.dirname(META_STATE_PATH), exist_ok=True)
        rec = {
            "t": time.time(),
            "domain": domain,
            "epsilon_i": round(eps_i, 6),
            "epsilon_eq": round(eps_eq, 6),
            "zeta": self.zeta,
            "delta": round(delta, 9),          # keep more precision
            "spread": round(self._spread(), 9),
            "n_domains": max(0, len(self.epsilon_by_domain) - 1),
            "anchor": round(self.epsilon_by_domain[self.anchor_domain], 6),
            "anchor_weight": self.anchor_weight,
        }
        with open(META_STATE_PATH, "a") as f:
            f.write(json.dumps(rec) + "\n")

        return float(delta)  # add this to epsilon as a tiny bias

    def _spread(self) -> float:
        # Spread across REAL domains only (exclude anchor)
        vals = [v for k, v in self.epsilon_by_domain.items() if k != self.anchor_domain]
        if len(vals) <= 1:
            return 0.0
        m = sum(vals) / len(vals)
        return sum((float(v) - m) ** 2 for v in vals) / len(vals)

    def set_anchor(self, anchor: float):
        """Optionally retune the anchor at runtime (do NOT call every step)."""
        self.epsilon_by_domain[self.anchor_domain] = float(anchor)

# Singleton helper
_meta_eq = MetaEquilibrium(zeta=0.02, anchor=0.245, anchor_weight=2.0)

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
        self.epsilon_bias = epsilon_bias  # optional default

    def to_dict(self):
        return {
            "frequency": self.frequency,
            "coherence": self.coherence,
            "gain": self.gain,
            "damping": self.damping,
            "epsilon_bias": self.epsilon_bias
        }