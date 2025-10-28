#!/usr/bin/env python3
"""
Tessaris AION Resonant Heartbeat Monitor (RHM)
Phase 6D — Stability Pulse & Self-Observation Layer
----------------------------------------------------
Periodically aggregates resonance telemetry (ΔΦ→Δν feedback)
and emits a summarized 'heartbeat' event to confirm system
stability and harmonic health.

Author: Tessaris Symbolic Intelligence Lab, 2025
"""

import os
import asyncio
import json
import logging
import statistics
from datetime import datetime, timezone
from pathlib import Path

# ────────────────────────────────────────────────────────────────
# 🔇 Silent Mode Handling
# ────────────────────────────────────────────────────────────────
SILENT = os.getenv("AION_SILENT_MODE", "0") == "1"

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.WARNING if SILENT else logging.INFO,
    format="%(asctime)s %(message)s"
)

# ────────────────────────────────────────────────────────────────
# File Paths and Constants
# ────────────────────────────────────────────────────────────────
TELEMETRY_FILE = Path("data/resonant_coupling_daemon.jsonl")
HEARTBEAT_FILE = Path("data/resonant_heartbeat.jsonl")
INTERVAL = 60.0  # seconds between heartbeats


# ────────────────────────────────────────────────────────────────
# 🫀 ResonanceHeartbeat Class
# ────────────────────────────────────────────────────────────────
class ResonanceHeartbeat:
    """
    🫀 ResonanceHeartbeat — live coherence monitor + feedback broadcaster
    Used by all AION/Tessaris subsystems for resonant feedback coupling.
    """

    def __init__(self, namespace="default"):
        self.namespace = namespace
        self.listeners = []
        self.running = False

        # 🩺 Resonance state attributes
        self.coherence = 0.85      # current Φ-coherence level (0–1)
        self.entropy = 0.15        # recent entropy snapshot (0–1)
        self.last_pulse = None

    # ------------------------------------------------------------
    def register_listener(self, callback):
        """Register a function to receive heartbeat pulse data."""
        if callable(callback):
            self.listeners.append(callback)

    # ------------------------------------------------------------
    def emit(self, delta: float = 0.0):
        """Emit a resonance heartbeat pulse to all listeners."""
        self.last_pulse = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resonance_delta": delta,
            "entropy": self.entropy,
        }
        for cb in self.listeners:
            try:
                cb(self.last_pulse)
            except Exception as e:
                if not SILENT:
                    print(f"[⚠️] Heartbeat listener error: {e}")

    # ------------------------------------------------------------
    def bind_jsonl(self, path: str):
        """Bind to a live JSONL stream of coherence readings."""
        self.jsonl_path = Path(path)
        if not self.jsonl_path.exists():
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            self.jsonl_path.touch()
        if not SILENT:
            print(f"🔗 Bound ResonanceHeartbeat to {path}")

    # ------------------------------------------------------------
    def start(self):
        """Begin emitting simulated heartbeats (background)."""
        import threading, time, math, random

        if self.running:
            return
        self.running = True

        def _loop():
            t0 = time.time()
            while self.running:
                t = time.time() - t0
                delta = math.sin(t / 20) * 0.05 + random.uniform(-0.02, 0.02)
                self.coherence = min(1.0, max(0.0, self.coherence + delta))
                self.entropy = max(0.0, min(1.0, abs(math.sin(t / 15)) * 0.3))
                self.emit(delta)
                time.sleep(5.0)

        threading.Thread(target=_loop, daemon=True).start()
        if not SILENT:
            print(f"💓 ResonanceHeartbeat[{self.namespace}] started.")

    # ------------------------------------------------------------
    def stop(self):
        """Stop the simulated heartbeat."""
        self.running = False
        if not SILENT:
            print(f"💤 ResonanceHeartbeat[{self.namespace}] stopped.")


# ────────────────────────────────────────────────────────────────
# 🧮 Telemetry Aggregation
# ────────────────────────────────────────────────────────────────
async def compute_heartbeat():
    """Read recent telemetry, compute mean stability and field variance."""
    if not TELEMETRY_FILE.exists():
        return None

    with TELEMETRY_FILE.open("r", encoding="utf-8") as f:
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
    HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with HEARTBEAT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(heartbeat) + "\n")

    return heartbeat


# ────────────────────────────────────────────────────────────────
# ♻️ Heartbeat Loop
# ────────────────────────────────────────────────────────────────
async def heartbeat_loop():
    if not SILENT:
        logger.info("💓 Starting Tessaris Resonant Heartbeat Monitor (RHM)...")
    while True:
        hb = await compute_heartbeat()
        if hb and not SILENT:
            logger.info(
                f"💓 Resonant heartbeat — stability={hb['mean_stability']:.4f}, "
                f"ΔΦ_coherence={hb['mean_coherence_delta']:+.4f}"
            )
        elif not hb and not SILENT:
            logger.info("💤 Waiting for telemetry...")
        await asyncio.sleep(INTERVAL)


# ────────────────────────────────────────────────────────────────
# 🏁 Entrypoint
# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        asyncio.run(heartbeat_loop())
    except KeyboardInterrupt:
        if not SILENT:
            logger.info("🧩 Resonant Heartbeat Monitor stopped manually.")