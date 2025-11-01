#!/usr/bin/env python3
# ============================================================
# ⚙️ Tessaris Resonant Optimizer Loop (ROL)
# Phase: Advisory Mode - Non-Mutating
# ============================================================
# Reads resonance telemetry (SQI, coherence, entropy)
# and emits advisory adjustments for subsystem tuning.
#
# 🧠 Purpose:
#   - Observe harmonic stability and entropy trends.
#   - Generate low-level advisories (no self-growth).
#   - Write results into ResonantMemoryCache (RMC).
#   - Optional future hook into DNA_SWITCH when stable.
#
# 🔒 Safety:
#   - No code or DNA mutations in this phase.
#   - Purely analytical + feedback emission.
#
# 🔁 Frequency: ~60s cycle
# ============================================================
import os

AION_SILENT = os.getenv("AION_SILENT_MODE", "0") == "1"
import asyncio
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.resonant_heartbeat_monitor import ResonanceHeartbeat

# 🧬 Placeholder for future integration
# from backend.modules.dna_chain.switchboard import DNA_SWITCH  # (currently inactive)

RMC_PATH = Path("data/memory/resonant_memory_cache.json")
ADVISORY_LIMIT = 50
INTERVAL = 60.0  # seconds

class ResonantOptimizerLoop:
    def __init__(self):
        self.rmc = ResonantMemoryCache()
        self.heartbeat = ResonanceHeartbeat(namespace="optimizer_loop")
        self.heartbeat.start()
        self.last_sqi = None
        self.last_entropy = None

    async def run(self):
        print("⚙️ [ROL] Resonant Optimizer Loop started (advisory mode).")
        while True:
            try:
                await self._cycle()
            except Exception as e:
                print(f"[ROL] ⚠️ Exception during optimizer cycle: {e}")
            await asyncio.sleep(INTERVAL)

    async def _cycle(self):
        """Run one advisory optimization cycle."""
        data = self.rmc.load_cache()

        sqi = data.get("sqi", 0.0)
        entropy = data.get("entropy", 0.0)
        coherence = data.get("coherence", 0.0)
        stability = data.get("stability", 0.0)
        timestamp = datetime.now(timezone.utc).isoformat()

        # Calculate simple deltas
        delta_sqi = (sqi - (self.last_sqi or sqi))
        delta_entropy = (entropy - (self.last_entropy or entropy))
        self.last_sqi, self.last_entropy = sqi, entropy

        # Generate advisory
        advisory = self._analyze_deltas(sqi, entropy, coherence, delta_sqi, delta_entropy)
        advisory_entry = {
            "timestamp": timestamp,
            "sqi": round(sqi, 3),
            "entropy": round(entropy, 3),
            "coherence": round(coherence, 3),
            "delta_sqi": round(delta_sqi, 4),
            "delta_entropy": round(delta_entropy, 4),
            "advisory": advisory,
        }

        # Save advisories list
        advisories = self.rmc.get("resonant_optimizer_advisories") or []
        advisories.append(advisory_entry)
        self.rmc.set("resonant_optimizer_advisories", advisories[-ADVISORY_LIMIT:])

        # Record last state
        self.rmc.set("resonant_optimizer_last", advisory_entry)

        # Emit soft heartbeat pulse
        self.heartbeat.emit(delta_sqi)
        print(f"[ROL] 💡 Advisory: {advisory} (SQI={sqi:.3f}, Δ={delta_sqi:+.3f})")

    def _analyze_deltas(self, sqi, entropy, coherence, delta_sqi, delta_entropy) -> str:
        """Produce an advisory text based on trends."""
        if abs(delta_sqi) < 0.001 and abs(delta_entropy) < 0.001:
            return "System stable - no adjustment needed."
        if delta_sqi < 0 and entropy > 0.4:
            return "Entropy rising - reduce exploration_rate slightly (-0.01)."
        if delta_sqi > 0.01 and coherence > 0.8:
            return "Coherence increasing - allow minor risk_bias expansion (+0.02)."
        if sqi < 0.5:
            return "Low SQI - consider increasing reflection weighting (+0.03)."
        if entropy < 0.2 and sqi > 0.7:
            return "Stable harmony - maintain current parameters."
        return "Minor fluctuations - monitor without change."

# ============================================================
# ⏯️ Launch Loop
# ============================================================
if __name__ == "__main__":
    import os
    if os.getenv("AION_SILENT_MODE", "0") == "1":
        print("⚙️ [ROL] Silent mode enabled - optimizer loop not started.")
    else:
        try:
            loop = ResonantOptimizerLoop()
            asyncio.run(loop.run())
        except KeyboardInterrupt:
            print("🧩 [ROL] Stopped manually.")