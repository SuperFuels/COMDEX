"""
📡 telemetry_handler.py - Centralized Telemetry Dispatcher for GlyphWave + QWave Integration

Purpose:
    * Logs beam activity via WaveScope
    * Pushes telemetry to CodexHUD / GHX WebSocket
    * Emits anomaly warnings (e.g. SNR/coherence issues)
    * Exposes live metrics for SQI / prediction / collapse overlays
    * Provides adaptive telemetry stream for CFE Feedback Loop
"""
import math
import asyncio
import random
import time
from collections import deque
from typing import Optional, Dict, Any

from .wavescope import WaveScope

# ===============================================================
# Core WaveScope Telemetry (local beam logging)
# ===============================================================

# Singleton instance of WaveScope
_wave_scope = WaveScope()


def log_beam(
    event: str,
    signal_power: float,
    noise_power: float = 1e-9,
    dropped: bool = False,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log a beam event and stream telemetry to HUD if enabled.

    Args:
        event (str): Type of beam event (e.g. 'emitted', 'dropped')
        signal_power (float): Beam signal strength
        noise_power (float): Background noise
        dropped (bool): Whether the beam was dropped
        meta (dict): Additional metadata
    """
    meta = meta or {}
    _wave_scope.log_beam_event(
        event=event,
        signal_power=signal_power,
        noise_power=noise_power,
        dropped=dropped,
        **meta
    )


def get_throughput_metrics(window_sec: float = 5.0) -> Dict[str, float]:
    """Return beam throughput + SNR statistics over recent time window."""
    return _wave_scope.track_throughput(window_sec=window_sec)


def get_recent_events(limit: int = 100) -> list:
    """Return recent beam events for display / replay / graphing."""
    return _wave_scope.recent(limit)


def reset_telemetry() -> None:
    """Clear all telemetry counters and logs."""
    _wave_scope.reset()


def get_wave_scope() -> WaveScope:
    """Return internal WaveScope instance for direct inspection or injection."""
    return _wave_scope


# ===============================================================
# Extended QWave Telemetry Integration (for CFE Feedback Loop)
# ===============================================================

class TelemetryHandler:
    """
    Collects and smooths QWave runtime telemetry for feedback loops.

    Combines physical beam logs (WaveScope) with simulated or live
    coherence/collapse metrics to provide unified runtime telemetry.
    """

    def __init__(self, window: int = 32):
        self._collapse_window = deque(maxlen=window)
        self._decoherence_window = deque(maxlen=window)
        self._stability_window = deque(maxlen=window)
        self._last_timestamp = time.time()
        self._connected = False
        self._simulate = True  # can be switched off when live QWave integration is ready

    # ---------------------------------------------------------------
    # Connection management
    # ---------------------------------------------------------------
    async def connect(self):
        """Connect to QWave telemetry bus (or initialize simulation)."""
        await asyncio.sleep(0.05)
        self._connected = True
        print("[QWave] TelemetryHandler connected to QWave bus")

    async def disconnect(self):
        self._connected = False
        print("[QWave] TelemetryHandler disconnected")

    # ---------------------------------------------------------------
    # Metric Collection
    # ---------------------------------------------------------------

    async def collect_metrics(self) -> Dict[str, float]:
        """
        Return a snapshot of current telemetry metrics.
        Combines WaveScope throughput with coherence statistics.
        Automatically archives each snapshot to outputs/sle_telemetry.jsonl
        and includes SQI composite metrics (Δφ, entropy, visibility)
        and symbolic pattern SQI (⊕ ↔ μ ⟲ π).
        """
        if not self._connected:
            await self.connect()

        if self._simulate:
            # Simulated coherence / collapse dynamics
            collapse = random.uniform(0.0, 0.05)
            decohere = random.uniform(0.0, 0.05)
            stability = max(0.0, 1.0 - (collapse + decohere))
        else:
            # Placeholder for live QWave event subscription
            collapse, decohere, stability = 0.01, 0.02, 0.97

        # Store rolling averages
        self._collapse_window.append(collapse)
        self._decoherence_window.append(decohere)
        self._stability_window.append(stability)

        collapse_avg = sum(self._collapse_window) / len(self._collapse_window)
        decohere_avg = sum(self._decoherence_window) / len(self._decoherence_window)
        stability_avg = sum(self._stability_window) / len(self._stability_window)

        # Include WaveScope throughput data
        snr_metrics = _wave_scope.track_throughput()

        # Base telemetry metrics
        metrics = {
            "timestamp": time.time(),
            "collapse_rate": round(collapse_avg, 4),
            "decoherence_rate": round(decohere_avg, 4),
            "coherence_stability": round(stability_avg, 4),
            "throughput": snr_metrics.get("throughput", 0.0),
            "snr": snr_metrics.get("snr", 0.0),
        }

        # ===============================================================
        # 🧠 SQI Composite (phase_drift, entropy, visibility)
        # ===============================================================
        try:
            import math
            from backend.modules.symatics_lightwave.coherence_metrics import sqi_composite
            phases = [random.uniform(0, 2 * math.pi) for _ in range(10)]
            amplitudes = [random.uniform(0.5, 1.0) for _ in range(10)]
            sqi_metrics = sqi_composite(phases, amplitudes)
            metrics.update(sqi_metrics)
        except Exception as e:
            print(f"[TelemetryHandler] SQI composite error: {e}")

        # ===============================================================
        # 🔤 Symbolic Pattern SQI (⊕ ↔ μ ⟲ π)
        # ===============================================================
        try:
            from backend.modules.sqi.sqi_scorer import score_pattern_sqi
            pattern_score = score_pattern_sqi({"glyphs": ["⊕", "↔", "μ", "⟲", "π"]})
            metrics["pattern_sqi"] = pattern_score
        except Exception as e:
            print(f"[TelemetryHandler] SQI pattern scoring error: {e}")

        # ===============================================================
        # 💾 Persist telemetry snapshot
        # ===============================================================
        try:
            import json, os
            path = "outputs/sle_telemetry.jsonl"
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a") as f:
                f.write(json.dumps(metrics) + "\n")
        except Exception as e:
            print(f"[TelemetryHandler] Warning: Failed to export JSONL -> {e}")

        return metrics

        # ===============================================================
        # 🧠 SQI Composite Integration (lazy import, second-chance import protection)
        # ===============================================================
        try:
            # Try lazy import (avoids circulars during early init)
            import math
            try:
                from backend.modules.symatics_lightwave.coherence_metrics import sqi_composite
            except Exception as e1:
                sqi_composite = None
                print(f"[TelemetryHandler] Deferred import of sqi_composite due to init timing: {e1}")

            if sqi_composite:
                phases = [random.uniform(0, 2 * math.pi) for _ in range(10)]
                amplitudes = [random.uniform(0.5, 1.0) for _ in range(10)]
                sqi_metrics = sqi_composite(phases, amplitudes)
                metrics.update(sqi_metrics)
            else:
                print("[TelemetryHandler] SQI composite not available yet (skipped this tick).")

        except Exception as e:
            print(f"[TelemetryHandler] SQI computation error: {e}")

        # ===============================================================
        # 📡 Persist telemetry snapshot to JSONL log
        # ===============================================================
        try:
            import json, os
            path = "outputs/sle_telemetry.jsonl"
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a") as f:
                f.write(json.dumps(metrics) + "\n")
        except Exception as e:
            print(f"[TelemetryHandler] Warning: Failed to export JSONL -> {e}")

        return metrics

    def export_jsonl(self, metrics: Dict[str, Any], path: str = "outputs/sle_telemetry.jsonl"):
        """Append a telemetry snapshot to JSONL for archival."""
        import json, os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(metrics) + "\n")    

    # ---------------------------------------------------------------
    # Continuous Stream (for GHX / CFE loops)
    # ---------------------------------------------------------------
    async def stream_metrics(self, interval: float = 1.0):
        """Continuously yield metrics for visualization or feedback."""
        await self.connect()
        while self._connected:
            metrics = await self.collect_metrics()
            yield metrics
            await asyncio.sleep(interval)