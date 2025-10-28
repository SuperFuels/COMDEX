#!/usr/bin/env python3
# ================================================================
# ⚖️ Tessaris Reasoner Bridge — Phase 64 (Core Pulse Closure)
# ================================================================
# Unifies Tessaris Engine (outer cognition) with TessarisReasoner
# (inner symbolic reasoner). Handles state exchange between:
#   • ReflexMemory (fast feedback)
#   • Motivation + Intent engines (slow reasoning input)
#   • ReflectionEngine (long-term modulation)
#   • ResonantHeartbeat (Θ-coupling)
# ================================================================

import json, time, logging
from pathlib import Path
from typing import Dict, Any

from backend.modules.aion_reasoning.tessaris_reasoner import TessarisReasoner
from backend.modules.aion_cognition.reflex_memory import ReflexMemory
from backend.modules.aion_cognition.motivation_layer import MotivationLayer
from backend.modules.aion_cognition.intent_engine import IntentEngine
from backend.modules.aion_reflection.reflection_engine import ReflectionEngine
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat

log = logging.getLogger(__name__)
OUT = Path("data/analysis/reasoner_bridge_state.json")


class ReasonerBridge:
    """
    Connects the inner TessarisReasoner to the outer cognitive system.
    Aggregates motivation, intent, reflex, and reflection into unified
    reasoning context; produces updated reasoning pulses.
    """

    def __init__(self):
        self.reasoner = TessarisReasoner()
        self.reflex_mem = ReflexMemory()
        self.motivation = MotivationLayer()
        self.intent_engine = IntentEngine()
        self.reflection = ReflectionEngine()
        self.heartbeat = ResonanceHeartbeat(namespace="reasoner_bridge")
        self.last_state: Dict[str, Any] = {}
        log.info("⚖️ ReasonerBridge initialized (Phase 64 Core Pulse Closure)")

    # ------------------------------------------------------------
    def gather_inputs(self) -> Dict[str, Any]:
        """Collects harmonized cognitive signals for reasoning update."""
        motive = self.motivation.output_vector()
        intent = self.intent_engine.current_intent() if hasattr(self.intent_engine, "current_intent") else {}
        reflex_state = self.reflex_mem.get_last_state() or {}
        reflection_trend = self.reflection.get_reflection_trend(window=25)
        pulse = self.heartbeat.tick()

        inputs = {
            "motivation": motive,
            "intent": intent,
            "reflex": reflex_state,
            "reflection": reflection_trend,
            "pulse": pulse,
        }
        log.debug(f"[ReasonerBridge] Inputs gathered: {list(inputs.keys())}")
        return inputs

    # ------------------------------------------------------------
    def update_reasoner(self):
        """Perform a single reasoning synchronization step with Θ feedback and logging."""
        inputs = self.gather_inputs()
        decision = self.reasoner.integrate(inputs)

        # Build state snapshot
        self.last_state = {
            "timestamp": time.time(),
            "decision": decision,
            "inputs": inputs,
        }

        # 🧬 Feed reasoning metrics back into ResonantMemoryCache (self-stabilizing loop)
        try:
            from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
            rmc = ResonantMemoryCache()
            sqi = float(decision.get("reasoning_score", 0.5))
            delta = abs(0.5 - sqi)
            entropy = 1.0 - sqi
            rho = 1.0 - abs(delta - entropy)  # approximate harmonic density for now
            rmc.push_sample(sqi=sqi, rho=rho, delta=delta, entropy=entropy, source="reasoner_bridge")
            rmc.save()
        except Exception as e:
            log.warning(f"[ReasonerBridge] ⚠ Failed RMC feedback injection: {e}")

        # 🧾 Export decision state (append-mode for full cycle history)
        try:
            OUT.parent.mkdir(parents=True, exist_ok=True)
            with open(OUT, "a", encoding="utf-8") as f:
                f.write(json.dumps(self.last_state) + "\n")
            log.info(f"[ReasonerBridge] ✅ State appended → {OUT}")
        except Exception as e:
            log.warning(f"[ReasonerBridge] ⚠ Failed to export state: {e}")

        theta_val = decision.get("reasoning_score", 0.0)
        log.info(f"[ReasonerBridge] Reasoning cycle complete — Θ={theta_val:.3f}")
        return decision

    # ------------------------------------------------------------
    def run_continuous(self, cycles: int = 10, delay: float = 1.5):
        """Run continuous reasoning–feedback synchronization loop."""
        for i in range(cycles):
            log.info(f"[ReasonerBridge] Cycle {i+1}/{cycles}")
            self.update_reasoner()
            time.sleep(delay)
        log.info("✅ ReasonerBridge run complete")


# ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    rb = ReasonerBridge()
    print("⚖️ Running ReasonerBridge demonstration...")
    rb.run_continuous(5, 1.0)