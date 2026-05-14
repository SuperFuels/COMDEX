"""
AION Cognitive Telemetry Metrics
────────────────────────────────
Extends the Φ-stability telemetry with derived cognitive-state metrics:
  * Φ_load    -> instantaneous symbolic processing load
  * Φ_flux    -> rate of change of Φ_stability_index
  * Φ_entropy -> informational disorder across recent coherence samples
"""

import math
import asyncio
from datetime import datetime, timezone
from statistics import mean, pstdev
from backend.AION.telemetry.coherence_tracker import _tracker
from backend.AION.telemetry.aion_stream import post_metric


def compute_cognitive_metrics():
    """Compute Φ_load, Φ_flux, Φ_entropy from tracker state."""
    records = _tracker.records
    if not records:
        return {"Φ_load": 0.0, "Φ_flux": 0.0, "Φ_entropy": 0.0}

    # 1. Φ_load - normalized current activity
    recent = records[-1]
    Φ_load = min(1.0, max(0.0, recent["pass_rate"] * (1 / (1 + recent["tolerance"]))))

    # 2. Φ_flux - rate of change of stability index
    if len(records) >= 2:
        Φ_prev = _tracker._compute_stability_index()
        Φ_old = _tracker._compute_stability_index() if len(records) < 2 else (
            records[-2]["pass_rate"] * (1 / (1 + records[-2]["tolerance"]))
        )
        Φ_flux = Φ_prev - Φ_old
    else:
        Φ_flux = 0.0

    # 3. Φ_entropy - normalized variance / disorder
    pass_rates = [r["pass_rate"] for r in records]
    σ = pstdev(pass_rates) if len(pass_rates) > 1 else 0.0
    Φ_entropy = min(1.0, σ * 10)  # scale into 0-1 band

    return {
        "Φ_load": round(Φ_load, 6),
        "Φ_flux": round(Φ_flux, 6),
        "Φ_entropy": round(Φ_entropy, 6),
    }


async def post_cognitive_metrics():
    """Emit computed metrics to AION telemetry stream."""
    payload = compute_cognitive_metrics()
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()

    try:
        await post_metric("Φ_COGNITION", payload)
        print(f"[AION::Telemetry] Φ_COGNITION logged -> {payload}")
    except Exception as e:
        print(f"[AION::Telemetry] ⚠ Cognitive metrics post failed: {e}")


def record_cognitive_metrics():
    """Safe wrapper callable from heartbeat loop."""
    coro = post_cognitive_metrics()
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(coro)
    else:
        asyncio.run(coro)