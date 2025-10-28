#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 MotivationEngine — Dynamic Cognitive Drive Core
────────────────────────────────────────────────────────────
Implements AION’s S1 (Motivation) subsystem:
• Maintains internal drive and goal resonance
• Syncs with Θ heartbeat
• Reinforces drive via ΔΦ (change in potential) and SQI
• Emits motivation vectors for downstream intent and reasoning
"""

import random, time, math, logging
from datetime import datetime
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

log = logging.getLogger(__name__)


class MotivationEngine:
    def __init__(self, namespace: str = "motivation_core", base_drive: float = 0.5):
        self.namespace = namespace
        self.heartbeat = ResonanceHeartbeat(namespace=namespace, auto_tick=True)
        self.rmc = ResonantMemoryCache()

        self.current_drive = base_drive
        self.stability = 0.5
        self.energy = 0.5
        self.focus = "resonance"
        self.goals = ["stability", "learning", "coherence", "efficiency", "resonance"]

        self.last_update = time.time()
        log.info(f"🧩 MotivationEngine initialized (namespace={namespace})")

    # ─────────────────────────────────────────────
    # 🔄 Periodic update from Θ heartbeat
    # ─────────────────────────────────────────────
    def tick(self):
        """Tick pulse from ResonanceHeartbeat."""
        now = time.time()
        elapsed = now - self.last_update
        self.last_update = now

        # natural motivation decay
        decay = math.exp(-elapsed / 120.0)
        self.current_drive *= decay

        # stabilize toward equilibrium via RMC resonance average
        avg_rho = self.rmc.get_average("rho") or 0.5
        delta = (avg_rho - 0.5) * 0.02
        self.current_drive = max(0.0, min(1.0, self.current_drive + delta))

        # emit heartbeat event
        self.heartbeat.event("motivation_tick", drive=self.current_drive, stability=self.stability)
        return {"drive": self.current_drive, "stability": self.stability}

    # ─────────────────────────────────────────────
    # 🧭 Generate motivation vector
    # ─────────────────────────────────────────────
    def output_vector(self, context: str = "general") -> dict:
        """Generate live motivation vector for current context."""
        drive = self.current_drive + random.uniform(-0.03, 0.03)
        focus = random.choice(self.goals)
        entropy = 1.0 - abs(0.5 - drive)

        vector = {
            "timestamp": time.time(),
            "context": context,
            "drive": round(drive, 3),
            "stability": round(self.stability, 3),
            "energy": round(self.energy, 3),
            "entropy": round(entropy, 3),
            "focus": focus,
            "goal": focus,
        }

        # store vector in RMC
        try:
            self.rmc.update_resonance_link(f"motivation:{context}", "drive", drive)
            self.rmc.push_sample(rho=drive, entropy=entropy, sqi=self.stability, source="motivation_engine")
            self.rmc.save()
        except Exception as e:
            log.warning(f"[MotivationEngine] RMC update failed: {e}")

        # emit live heartbeat
        self.heartbeat.event("motivation_vector_emit", **vector)
        return vector

    # ─────────────────────────────────────────────
    # ⚡ Reinforcement Feedback
    # ─────────────────────────────────────────────
    def reinforce(self, delta_phi: float, sqi: float):
        """
        Reinforce motivation drive based on ΔΦ (potential change)
        and SQI (stability quality index).
        """
        adj = (delta_phi + sqi - 0.5) * 0.15
        self.current_drive = max(0.0, min(1.0, self.current_drive + adj))
        self.stability = max(0.0, min(1.0, self.stability + (sqi - 0.5) * 0.1))

        self.heartbeat.event("motivation_reinforce", delta_phi=delta_phi, sqi=sqi, drive=self.current_drive)
        self.rmc.push_sample(rho=self.current_drive, entropy=0.5, sqi=sqi, delta=delta_phi, source="motivation_reinforce")

        log.info(f"[MotivationEngine] Reinforced drive={self.current_drive:.3f} stability={self.stability:.3f}")

    # ─────────────────────────────────────────────
    # 🌿 Homeostatic Balancing
    # ─────────────────────────────────────────────
    def stabilize(self):
        """Natural equilibrium restoration."""
        avg_rho = self.rmc.get_average("rho") or 0.5
        avg_sqi = self.rmc.get_average("sqi") or 0.5
        self.current_drive = (self.current_drive + avg_rho) / 2
        self.stability = (self.stability + avg_sqi) / 2
        self.energy = (self.energy + self.current_drive) / 2
        self.heartbeat.event("motivation_stabilize", drive=self.current_drive, stability=self.stability)
        log.info(f"[MotivationEngine] Stabilized → drive={self.current_drive:.3f}, stability={self.stability:.3f}")

    # ─────────────────────────────────────────────
    # 📊 Diagnostics
    # ─────────────────────────────────────────────
    def get_state(self) -> dict:
        """Return current motivation state snapshot."""
        return {
            "drive": round(self.current_drive, 3),
            "stability": round(self.stability, 3),
            "energy": round(self.energy, 3),
            "goal": self.focus,
            "timestamp": datetime.utcnow().isoformat(),
        }


# ─────────────────────────────────────────────
# 🔬 Local Demo Mode
# ─────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    engine = MotivationEngine()
    print("🧠 MotivationEngine — Live Drive Simulation\n")

    for i in range(5):
        print(engine.output_vector("demo"))
        if i % 2 == 1:
            engine.reinforce(delta_phi=0.1, sqi=0.7)
        time.sleep(1)
    engine.stabilize()
    print(engine.get_state())