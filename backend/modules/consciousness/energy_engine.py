#!/usr/bin/env python3
"""
⚛ EnergyEngine - Phase 54 Resonant Amplitude Regulator
───────────────────────────────────────────────────────────────
Maintains AION's harmonic vitality - simulating fatigue, recovery,
and cognitive resource balance based on Θ-field resonance dynamics.

Features
* Θ-Amplitude regulation (fatigue ↔ recovery)
* Integration with ResonantMemoryCache (RMC)
* Coherence-driven energy state, not token economics
* Entropy feedback from ContextEngine + other modules
* Logs harmonic vitality pulses for dashboard telemetry
"""

import random
import time
import json
from datetime import datetime
from pathlib import Path
from statistics import mean

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# ⚛ Resonance Coupling
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

# 🌐 Optional coupling to ContextEngine for environmental entropy
try:
    from backend.modules.consciousness.context_engine import ContextEngine
except Exception:
    ContextEngine = None


class EnergyEngine:
    """
    Regulates harmonic amplitude and cognitive energy equilibrium.
    Energy now represents Θ-field coherence rather than survival fuel.
    """

    def __init__(self):
        # "Energy" is harmonic coherence (0 - 1 -> fatigue - vitality)
        self.energy_level = 1.0
        self.stability = 1.0
        self.last_update = datetime.utcnow()
        self.context = ContextEngine() if ContextEngine else None

        # ⚛ Resonance Components
        self.Θ = ResonanceHeartbeat(namespace="energy", base_interval=1.2)
        self.RMC = ResonantMemoryCache()
        self.resonance_log = Path("data/analysis/energy_resonance_feed.jsonl")
        self.resonance_log.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------
    def _sample_environment_entropy(self) -> float:
        """Obtain contextual entropy for environmental modulation."""
        if not self.context:
            return 0.5
        ctx = self.context.get_context()
        return float(ctx.get("entropy", 0.5))

    # ------------------------------------------------------------
    def tick(self):
        """
        Called periodically to update harmonic amplitude.
        * High entropy -> coherence decay (fatigue)
        * Low entropy -> recovery
        """
        env_entropy = self._sample_environment_entropy()
        rho_base = 0.7 + random.uniform(-0.05, 0.05)
        rho = max(0.3, min(1.0, rho_base * (1 - 0.3 * env_entropy)))
        sqi = round(mean([self.energy_level, rho, 1 - env_entropy]), 3)
        delta_phi = round(abs(rho - env_entropy), 3)

        # Harmonic energy update
        decay = 0.05 + 0.15 * env_entropy
        recovery = 0.08 * (1 - env_entropy)
        change = recovery - decay
        self.energy_level = max(0.0, min(1.0, self.energy_level + change))
        self.stability = round((1 - abs(delta_phi - 0.25)) * 0.8 + 0.2, 3)
        self.last_update = datetime.utcnow()

        # Adjust Θ amplitude based on coherence
        new_amplitude = max(0.4, min(1.2, 0.8 + (self.energy_level - 0.5)))
        self.Θ.set_amplitude(new_amplitude)

        # Feedback & persistence
        self.Θ.feedback("energy", delta_phi)
        self.RMC.push_sample(rho=rho, entropy=env_entropy, sqi=sqi, delta=delta_phi)
        self.RMC.save()

        # Logging
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ρ": rho,
            "Ī": env_entropy,
            "SQI": sqi,
            "ΔΦ": delta_phi,
            "energy_level": self.energy_level,
            "stability": self.stability,
            "Θ_amplitude": new_amplitude
        }
        with open(self.resonance_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        print(
            f"[Θ⚡] Energy tick -> ρ={rho:.3f}, entropy={env_entropy:.2f}, "
            f"energy={self.energy_level:.2f}, stability={self.stability:.2f}"
        )
        return entry

    # ------------------------------------------------------------
    def boost(self, delta: float = 0.1):
        """Manual harmonic boost (reflection, optimization, etc.)."""
        old = self.energy_level
        self.energy_level = min(1.0, self.energy_level + abs(delta))
        print(f"[⚡] Energy boosted {old:.2f} -> {self.energy_level:.2f}")

    def drain(self, delta: float = 0.1):
        """Simulated energy drain (heavy computation or resonance drift)."""
        old = self.energy_level
        self.energy_level = max(0.0, self.energy_level - abs(delta))
        print(f"[💤] Energy drained {old:.2f} -> {self.energy_level:.2f}")

    # ------------------------------------------------------------
    def get_status(self) -> dict:
        """Return structured energy/coherence state."""
        return {
            "energy_level": self.energy_level,
            "stability": self.stability,
            "last_update": self.last_update.isoformat(),
            "Θ_amplitude": self.Θ.amplitude,
        }

    def describe(self) -> str:
        """Readable snapshot for logs."""
        return (
            f"AION harmonic energy: {self.energy_level:.2f}, "
            f"stability: {self.stability:.2f}, "
            f"Θ amplitude: {self.Θ.amplitude:.2f}"
        )


# 🧪 Local diagnostic
if __name__ == "__main__":
    engine = EnergyEngine()
    for _ in range(5):
        engine.tick()
        time.sleep(0.5)
    engine.boost(0.15)
    print(json.dumps(engine.get_status(), indent=2))