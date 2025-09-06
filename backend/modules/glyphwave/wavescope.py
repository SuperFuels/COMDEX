"""
📊 WaveScope – Telemetry + Signal Metrics for GlyphWave

Provides:
    • Beam event logging
    • Signal-to-noise ratio (SNR) tracking
    • Throughput stats (beams/sec, dropped %)
    • WebSocket HUD + GHX trace streaming
"""

from typing import Dict, Any, List
from time import time
from statistics import mean
from math import log10

# Optional: adjust if using a local websocket broadcast util
try:
    from hexcore.websocket import broadcast
except ImportError:
    broadcast = None  # fallback in environments without WS

class WaveScope:
    def __init__(self):
        self._events: List[Dict[str, Any]] = []
        self._timestamps: List[float] = []
        self._dropped_count = 0
        self._total_count = 0
        self._snr_samples: List[float] = []

    def log_beam_event(
        self,
        event: str,
        signal_power: float,
        noise_power: float = 1e-9,
        dropped: bool = False,
        **extra: Any
    ) -> None:
        """
        Log a beam transmission or reception event.

        Args:
            event (str): Type of event (e.g., 'emitted', 'received', 'dropped').
            signal_power (float): Signal strength (W).
            noise_power (float): Background noise level.
            dropped (bool): Whether the beam was dropped.
            extra (dict): Additional metadata.
        """
        timestamp = time()
        snr = self._calculate_snr(signal_power, noise_power)

        entry = {
            "timestamp": timestamp,
            "event": event,
            "signal": signal_power,
            "noise": noise_power,
            "snr": snr,
            "dropped": dropped,
            "meta": {
                "coherence": self._coherence_score(snr),
                **extra,
            }
        }

        self._events.append(entry)
        self._timestamps.append(timestamp)
        self._snr_samples.append(snr)
        self._total_count += 1
        if dropped:
            self._dropped_count += 1

        self._stream_to_hud(entry)

    def _calculate_snr(self, signal: float, noise: float) -> float:
        """Compute SNR (signal-to-noise ratio) in dB."""
        if noise <= 0.0:
            noise = 1e-9
        if signal <= 0.0:
            return 0.0
        return 10 * log10(signal / noise)

    def _coherence_score(self, snr: float) -> float:
        """
        Normalize SNR into a [0, 1] coherence score.
        Uses a sigmoid-like scale with saturation.
        """
        if snr <= 0:
            return 0.0
        elif snr >= 30:
            return 1.0
        else:
            return round(snr / 30.0, 4)

    def track_throughput(self, window_sec: float = 5.0) -> Dict[str, float]:
        """
        Compute throughput metrics over a time window.

        Args:
            window_sec (float): Duration in seconds to calculate throughput.

        Returns:
            Dict[str, float]: Metrics including beams/sec and drop rate.
        """
        now = time()
        windowed = [ts for ts in self._timestamps if ts >= now - window_sec]
        throughput = len(windowed) / window_sec if window_sec > 0 else 0.0
        drop_rate = self._dropped_count / self._total_count if self._total_count else 0.0
        avg_snr = mean(self._snr_samples[-len(windowed):]) if windowed else 0.0

        return {
            "beams_per_sec": round(throughput, 2),
            "drop_rate": round(drop_rate, 4),
            "avg_snr": round(avg_snr, 2),
        }

    def recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return recent beam events (latest first)."""
        return self._events[-limit:][::-1]

    def reset(self) -> None:
        """Clear all collected telemetry data."""
        self._events.clear()
        self._timestamps.clear()
        self._snr_samples.clear()
        self._total_count = 0
        self._dropped_count = 0

    def _stream_to_hud(self, log: Dict[str, Any]) -> None:
        """
        Push event to WebSocket clients for live HUD/Visualizer overlays.
        """
        if broadcast:
            try:
                broadcast("beam_event", log)
            except Exception:
                pass  # fail silently or log if needed