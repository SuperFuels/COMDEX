"""
📡 telemetry_handler.py – Centralized Telemetry Dispatcher for GlyphWave

Purpose:
    • Logs beam activity via WaveScope
    • Pushes telemetry to CodexHUD / GHX WebSocket
    • Emits anomaly warnings (e.g. SNR/coherence issues)
    • Exposes live metrics for SQI / prediction / collapse overlays
"""

from typing import Optional, Dict, Any
from .wavescope import WaveScope

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
    """
    Return beam throughput + SNR statistics over recent time window.
    """
    return _wave_scope.track_throughput(window_sec=window_sec)


def get_recent_events(limit: int = 100) -> list:
    """
    Return recent beam events for display / replay / graphing.
    """
    return _wave_scope.recent(limit)


def reset_telemetry() -> None:
    """
    Clear all telemetry counters and logs.
    """
    _wave_scope.reset()


def get_wave_scope() -> WaveScope:
    """
    Return internal WaveScope instance for direct inspection or injection.
    """
    return _wave_scope