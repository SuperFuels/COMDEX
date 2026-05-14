#!/usr/bin/env python3
# ============================================================
# ⚡ ReflexExecutor - Phase 63 Reflex-Reasoner Fusion
# ============================================================
# Handles rapid micro-actions triggered by ReflexArc or sensors.
#   * Executes or simulates reflex-scale responses.
#   * Measures SQI / ΔΦ / entropy drift post-action.
#   * Sends results to ReflexMemory + TessarisReasoner.
#   * Emits Θ-pulse feedback via ResonanceHeartbeat.
#   * (Now) Emits SCI photon capsules for reflex cognition trace
# ============================================================

import json, time, random, logging
from pathlib import Path
from typing import Dict, Any
from statistics import mean

from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_reasoning.tessaris_reasoner import TessarisReasoner
from backend.modules.aion_cognition.reflex_memory import ReflexMemory

# ✅ SCI hook - safe fallback if overlay unavailable or in lite mode
try:
    from backend.modules.aion_language.sci_overlay import sci_emit
except Exception:
    def sci_emit(*a, **k): pass

log = logging.getLogger(__name__)


class ReflexExecutor:
    def __init__(self):
        self.rmc = ResonantMemoryCache()
        self.heartbeat = ResonanceHeartbeat(namespace="reflex", base_interval=0.8)
        self.reasoner = TessarisReasoner()
        self.memory = ReflexMemory()
        self.log_path = Path("data/reflex/reflex_executor_trace.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("⚡ ReflexExecutor initialized (Phase 63 Fusion)")

    # ------------------------------------------------------------
    def execute_reflex(self, stimulus: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core reflex execution cycle.
        stimulus -> micro-response -> measure resonance -> record feedback
        """
        action = stimulus.get("action", "undefined")
        intensity = float(stimulus.get("intensity", random.uniform(0.2, 0.8)))

        # - Simulate reflex response
        response_time = max(0.05, random.gauss(0.25, 0.05))
        sqi = round(max(0.0, min(1.0, 0.6 + random.uniform(-0.1, 0.1))), 3)
        delta_phi = round(random.uniform(-0.05, 0.05) * intensity, 3)
        entropy = round(abs(delta_phi) * 2 + random.uniform(0.3, 0.6), 3)

        result = {
            "action": action,
            "intensity": intensity,
            "sqi": sqi,
            "delta_phi": delta_phi,
            "entropy": entropy,
            "response_time": response_time,
            "timestamp": time.time(),
        }

        # - Persist to ReflexMemory + RMC
        self.memory.record(action, stimulus, decision={"allowed": True}, outcome=result)
        self.rmc.push_sample(sqi=sqi, delta=delta_phi, entropy=entropy, source="reflex_executor")
        self.rmc.save()

        # ✅ SCI symbolic trace: reflex event
        try:
            msg = (
                f"Reflex executed: {action} | "
                f"sqi={sqi}, ΔΦ={delta_phi}, entropy={entropy}"
            )
            sci_emit("reflex_executor", msg)
        except Exception:
            pass

        # - Emit Θ feedback + Reasoner update
        self.heartbeat.tick()
        self.reasoner.feedback_from_reflex(result)

        # ✅ SCI symbolic trace: resonance heartbeat tick
        try:
            sci_emit("reflex_theta_tick", f"Θ pulse after reflex: {action}")
        except Exception:
            pass

        # - Log trace
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(result) + "\n")

        log.info(f"[ReflexExecutor] action={action} SQI={sqi:.3f} ΔΦ={delta_phi:.3f} entropy={entropy:.3f}")
        return result

    # ------------------------------------------------------------
    def stress_test(self, n: int = 10):
        """Run synthetic reflex cycles for testing and profiling."""
        for i in range(n):
            stimulus = {"action": f"auto_test_{i}", "intensity": random.uniform(0.3, 0.9)}
            self.execute_reflex(stimulus)
            time.sleep(0.1)


# ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    re = ReflexExecutor()
    print("⚡ Running ReflexExecutor demo...")
    re.stress_test(5)