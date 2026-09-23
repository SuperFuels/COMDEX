# -*- coding: utf-8 -*-
"""
📡 telemetry_handler.py - Centralized Telemetry Dispatcher for GlyphWave + QWave Integration

Purpose:
    * Logs beam activity via WaveScope
    * Exposes live metrics for SQI / prediction / collapse overlays
    * Provides adaptive telemetry stream for CFE feedback loops
    * Supports both simulated telemetry and real/injected hardware telemetry
    * Archives telemetry snapshots to JSONL

Notes:
    * This version removes the dead/unreachable duplicate return path
    * This version supports live external metric injection via ingest_live_sample()
    * This version defaults to non-simulated mode unless explicitly enabled
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import random
import time
from collections import deque
from pathlib import Path
from typing import Optional, Dict, Any, Deque

from .wavescope import WaveScope

# ===============================================================
# Core WaveScope Telemetry (local beam logging)
# ===============================================================

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
    """
    meta = meta or {}
    _wave_scope.log_beam_event(
        event=event,
        signal_power=signal_power,
        noise_power=noise_power,
        dropped=dropped,
        **meta,
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
    Collects and smooths runtime telemetry for feedback loops.

    Sources:
        1. Live injected samples via ingest_live_sample()
        2. Derived metrics from WaveScope throughput/SNR
        3. Simulated fallback (only if explicitly enabled)

    Public contract:
        * async connect()
        * async disconnect()
        * async collect_metrics()
        * async stream_metrics()
        * export_jsonl()
        * ingest_live_sample()
        * set_simulation_mode()
    """

    def __init__(
        self,
        window: int = 32,
        simulate: Optional[bool] = None,
        export_path: str = "outputs/sle_telemetry.jsonl",
    ):
        self._collapse_window: Deque[float] = deque(maxlen=window)
        self._decoherence_window: Deque[float] = deque(maxlen=window)
        self._stability_window: Deque[float] = deque(maxlen=window)

        self._last_timestamp = time.time()
        self._connected = False

        # Default to live/non-sim mode unless explicitly enabled.
        if simulate is None:
            env_value = os.getenv("GLYPHWAVE_SIMULATE_TELEMETRY", "0").strip().lower()
            simulate = env_value in {"1", "true", "yes", "on"}
        self._simulate = simulate

        self._export_path = Path(export_path)
        self._latest_live_sample: Optional[Dict[str, Any]] = None
        self._sample_source = "uninitialized"

    # ---------------------------------------------------------------
    # Connection management
    # ---------------------------------------------------------------
    async def connect(self) -> None:
        """Connect to telemetry bus or initialize local telemetry state."""
        if self._connected:
            return
        await asyncio.sleep(0.05)
        self._connected = True
        mode = "simulation" if self._simulate else "live"
        print(f"[QWave] TelemetryHandler connected ({mode} mode)")

    async def disconnect(self) -> None:
        self._connected = False
        print("[QWave] TelemetryHandler disconnected")

    def set_simulation_mode(self, enabled: bool) -> None:
        """Explicitly enable or disable simulation mode."""
        self._simulate = bool(enabled)
        mode = "simulation" if self._simulate else "live"
        print(f"[QWave] TelemetryHandler mode -> {mode}")

    # ---------------------------------------------------------------
    # External hardware / runtime injection
    # ---------------------------------------------------------------
    def ingest_live_sample(self, sample: Dict[str, Any]) -> None:
        """
        Ingest externally measured telemetry.

        Expected optional keys:
            collapse_rate
            decoherence_rate
            coherence_stability
            throughput
            snr
            phase_drift
            entropy
            visibility
            pattern_sqi

        Any missing core fields will be derived later.
        """
        self._latest_live_sample = dict(sample)
        self._sample_source = "injected_live_sample"

    # ---------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------
    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, value))

    def _derive_live_metrics_from_scope(self) -> Dict[str, float]:
        """
        Derive approximate feedback metrics from WaveScope throughput/SNR.

        This is the default non-sim path when direct hardware telemetry has not
        yet been injected. It keeps the loop real-data-driven rather than using
        fixed placeholder constants.
        """
        snr_metrics = _wave_scope.track_throughput()
        throughput = float(snr_metrics.get("throughput", 0.0) or 0.0)
        snr = float(snr_metrics.get("snr", 0.0) or 0.0)

        # Map SNR into a bounded quality score.
        # Higher SNR => lower decoherence/collapse => higher stability.
        snr_quality = self._clamp(snr / 40.0, 0.0, 1.0)

        # Throughput contributes weakly to collapse pressure.
        # If throughput is low and SNR is poor, collapse pressure rises.
        throughput_quality = self._clamp(throughput / 10.0, 0.0, 1.0)

        decoherence = self._clamp(1.0 - snr_quality, 0.0, 1.0)
        collapse = self._clamp((1.0 - throughput_quality) * 0.35 + decoherence * 0.65, 0.0, 1.0)
        stability = self._clamp(1.0 - max(collapse, decoherence) * 0.85, 0.0, 1.0)

        return {
            "collapse_rate": collapse,
            "decoherence_rate": decoherence,
            "coherence_stability": stability,
            "throughput": throughput,
            "snr": snr,
        }

    def _get_raw_metrics(self) -> Dict[str, float]:
        """
        Return raw instantaneous metrics before smoothing.
        """
        if self._simulate:
            self._sample_source = "simulation"
            collapse = random.uniform(0.0, 0.05)
            decohere = random.uniform(0.0, 0.05)
            stability = max(0.0, 1.0 - (collapse + decohere))
            snr_metrics = _wave_scope.track_throughput()
            return {
                "collapse_rate": collapse,
                "decoherence_rate": decohere,
                "coherence_stability": stability,
                "throughput": float(snr_metrics.get("throughput", 0.0) or 0.0),
                "snr": float(snr_metrics.get("snr", 0.0) or 0.0),
            }

        if self._latest_live_sample:
            self._sample_source = "injected_live_sample"
            derived = self._derive_live_metrics_from_scope()
            merged = {**derived, **self._latest_live_sample}

            merged["collapse_rate"] = self._clamp(float(merged.get("collapse_rate", derived["collapse_rate"])))
            merged["decoherence_rate"] = self._clamp(float(merged.get("decoherence_rate", derived["decoherence_rate"])))
            merged["coherence_stability"] = self._clamp(float(merged.get("coherence_stability", derived["coherence_stability"])))
            merged["throughput"] = float(merged.get("throughput", derived["throughput"]) or 0.0)
            merged["snr"] = float(merged.get("snr", derived["snr"]) or 0.0)
            return merged

        self._sample_source = "wavescope_derived"
        return self._derive_live_metrics_from_scope()

    def _rolling_mean(self, values: Deque[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    def _append_windows(self, collapse: float, decohere: float, stability: float) -> None:
        self._collapse_window.append(collapse)
        self._decoherence_window.append(decohere)
        self._stability_window.append(stability)

    def _compute_sqi_composite(self) -> Dict[str, Any]:
        """
        Best-effort SQI composite metrics.
        """
        try:
            from backend.modules.symatics_lightwave.coherence_metrics import sqi_composite

            phases = [random.uniform(0.0, 2.0 * math.pi) for _ in range(10)]
            amplitudes = [random.uniform(0.5, 1.0) for _ in range(10)]
            result = sqi_composite(phases, amplitudes)
            return result if isinstance(result, dict) else {}
        except Exception as e:
            print(f"[TelemetryHandler] SQI composite error: {e}")
            return {}

    def _compute_pattern_sqi(self) -> Optional[float]:
        """
        Best-effort symbolic pattern SQI score.
        """
        try:
            from backend.modules.sqi.sqi_scorer import score_pattern_sqi

            score = score_pattern_sqi({"glyphs": ["⊕", "↔", "μ", "⟲", "π"]})
            return float(score)
        except Exception as e:
            print(f"[TelemetryHandler] SQI pattern scoring error: {e}")
            return None

    # ---------------------------------------------------------------
    # Metric Collection
    # ---------------------------------------------------------------
    async def collect_metrics(self) -> Dict[str, float]:
        """
        Return a smoothed snapshot of current telemetry metrics.

        Includes:
            * collapse_rate
            * decoherence_rate
            * coherence_stability
            * throughput
            * snr
            * optional SQI composite metrics
            * optional symbolic pattern SQI
        """
        if not self._connected:
            await self.connect()

        raw = self._get_raw_metrics()

        collapse = float(raw.get("collapse_rate", 0.0))
        decohere = float(raw.get("decoherence_rate", 0.0))
        stability = float(raw.get("coherence_stability", 1.0))

        self._append_windows(collapse, decohere, stability)

        collapse_avg = self._rolling_mean(self._collapse_window)
        decohere_avg = self._rolling_mean(self._decoherence_window)
        stability_avg = self._rolling_mean(self._stability_window)

        now = time.time()
        dt = max(now - self._last_timestamp, 1e-9)
        self._last_timestamp = now

        metrics: Dict[str, Any] = {
            "timestamp": now,
            "dt": round(dt, 6),
            "source": self._sample_source,
            "collapse_rate": round(collapse_avg, 4),
            "decoherence_rate": round(decohere_avg, 4),
            "coherence_stability": round(stability_avg, 4),
            "throughput": float(raw.get("throughput", 0.0) or 0.0),
            "snr": float(raw.get("snr", 0.0) or 0.0),
        }

        # Preserve any extra live sample fields that are not core metrics.
        for key, value in raw.items():
            if key not in metrics:
                metrics[key] = value

        sqi_metrics = self._compute_sqi_composite()
        if sqi_metrics:
            metrics.update(sqi_metrics)

        pattern_score = self._compute_pattern_sqi()
        if pattern_score is not None:
            metrics["pattern_sqi"] = pattern_score

        self.export_jsonl(metrics)
        return metrics

    def export_jsonl(self, metrics: Dict[str, Any], path: Optional[str] = None) -> None:
        """Append a telemetry snapshot to JSONL for archival."""
        output_path = Path(path) if path else self._export_path
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(metrics, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[TelemetryHandler] Warning: Failed to export JSONL -> {e}")

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