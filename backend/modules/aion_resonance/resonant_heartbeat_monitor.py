"""
Tessaris AION Resonant Heartbeat Monitor (RHM)
Phase 6D — Stability Pulse & Self-Observation Layer
----------------------------------------------------
Periodically aggregates resonance telemetry (ΔΦ→Δν feedback)
and emits a summarized 'heartbeat' event to confirm system
stability and harmonic health.

Author: Tessaris Symbolic Intelligence Lab, 2025
"""

import asyncio
import json
import logging
import statistics
from datetime import datetime, timezone
from pathlib import Path

TELEMETRY_FILE = Path("data/resonant_coupling_daemon.jsonl")
HEARTBEAT_FILE = Path("data/resonant_heartbeat.jsonl")
INTERVAL = 60.0  # seconds between heartbeats

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")


async def compute_heartbeat():
    """Read recent telemetry, compute mean stability and field variance."""
    if not TELEMETRY_FILE.exists():
        return None

    with TELEMETRY_FILE.open() as f:
        lines = f.readlines()[-60:]  # last ~6 min (if 6 s intervals)
    if not lines:
        return None

    stabilities = []
    coherence_vals = []
    for line in lines:
        try:
            j = json.loads(line)
            stabilities.append(j.get("stability", 0))
            coherence_vals.append(j.get("delta_phi", {}).get("Φ_coherence", 0))
        except Exception:
            continue

    if not stabilities:
        return None

    mean_stability = statistics.mean(stabilities)
    var_stability = statistics.pvariance(stabilities)
    mean_coherence = statistics.mean(coherence_vals)

    heartbeat = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mean_stability": round(mean_stability, 6),
        "variance": round(var_stability, 6),
        "mean_coherence_delta": round(mean_coherence, 6),
    }

    # persist heartbeat
    with HEARTBEAT_FILE.open("a") as f:
        f.write(json.dumps(heartbeat) + "\n")

    return heartbeat


async def heartbeat_loop():
    logger.info("💓 Starting Tessaris Resonant Heartbeat Monitor (RHM)...")
    while True:
        hb = await compute_heartbeat()
        if hb:
            logger.info(
                f"💓 Resonant heartbeat — stability={hb['mean_stability']:.4f}, "
                f"ΔΦ_coherence={hb['mean_coherence_delta']:+.4f}"
            )
        else:
            logger.info("💤 Waiting for telemetry...")
        await asyncio.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(heartbeat_loop())
    except KeyboardInterrupt:
        logger.info("🧩 Resonant Heartbeat Monitor stopped manually.")