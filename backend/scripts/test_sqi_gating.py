"""
Test Script: SQI-Gated Scheduler Diagnostic
Simulates GWIP packets passing through the PhaseScheduler
with dynamic SQI values, demonstrating gating behavior.
"""

import random
import time
from backend.modules.glyphwave.scheduler import PhaseScheduler

# --- Fake TelemetryHandler monkeypatch ---
class FakeTelemetryHandler:
    """Simulate SQI telemetry values that fluctuate over time."""
    _last_metrics = {"sqi_score": 1.0}

    @classmethod
    def update_sqi(cls, value: float):
        cls._last_metrics["sqi_score"] = value

# Inject fake TelemetryHandler into runtime namespace
import backend.modules.glyphwave.scheduler as scheduler_module
scheduler_module.TelemetryHandler = FakeTelemetryHandler

# --- Test Execution ---
if __name__ == "__main__":
    print("\n🌐 Starting SQI Gating Diagnostic...\n")

    scheduler = PhaseScheduler()
    scheduler.set_policy({"sqi_min_threshold": 0.35})

    # Simulate 10 GWIP packets with changing SQI values
    for tick in range(10):
        # Simulate SQI oscillation between 0.1 and 0.9
        sqi_value = round(random.uniform(0.1, 0.9), 3)
        FakeTelemetryHandler.update_sqi(sqi_value)

        gwip = {"id": f"gwip_{tick}", "payload": f"data_{tick}"}
        scheduled = scheduler.schedule(gwip)

        env = scheduled.get("envelope", {})
        status = "🚫 GATED" if env.get("gated") else "✅ TRANSMITTED"
        reason = env.get("reason", "")
        print(f"[Tick {tick}] SQI={sqi_value:.3f} -> {status} | {reason}")

        time.sleep(0.5)

    print("\n📊 Final Scheduler Metrics:")
    print(scheduler.metrics())

    print("\n✅ SQI gating test complete.\n")