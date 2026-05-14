# File: backend/modules/runtime/hud_beam_visualizer.py

"""
hud_beam_visualizer.py
=======================

Real-time HUD / GHX visualization module for symbolic QWave beam processing.
Streams beam metadata (ID, SQI, collapse status, symbolic state) to the interface layer.

Supports:
- GHX overlays (QWave visual feedback)
- Beam trace timelines
- Entropy and SQI color mapping
- Error state display
"""

import logging
from typing import Union, List
from backend.modules.quantum.wave_state import WaveState
from backend.modules.ghx.ghx_broadcast import send_hud_overlay
from backend.modules.sqi.sqi_color_utils import get_sqi_color
from backend.modules.codex.codex_metrics import format_entropy_metric

logger = logging.getLogger(__name__)


def visualize_beam_on_hud(beam: Union[WaveState, List[WaveState]]) -> None:
    """
    Sends HUD visualization packet for one or more beams.
    """
    if isinstance(beam, list):
        for b in beam:
            _send_single_beam_visual(b)
    else:
        _send_single_beam_visual(beam)


def _send_single_beam_visual(beam: WaveState):
    try:
        hud_packet = {
            "type": "beam",
            "id": beam.id,
            "status": beam.status,
            "sqi_score": beam.sqi_score,
            "entropy": format_entropy_metric(beam.entropy),
            "symbol": _get_primary_symbol(beam),
            "color": get_sqi_color(beam.sqi_score),
            "trace": beam.to_dict().get("collapsed_state", {}),
            "origin": beam.origin or "unknown",
        }

        send_hud_overlay(hud_packet)
        logger.debug(f"[HUD] 📡 Beam {beam.id} HUD packet sent")

    except Exception as e:
        logger.error(f"[HUD] ❌ Failed to visualize beam {beam.id}: {e}", exc_info=True)


def _get_primary_symbol(beam: WaveState) -> str:
    """
    Attempt to extract the dominant symbol from the collapsed state.
    Used for icon display in the HUD.
    """
    try:
        if isinstance(beam.collapsed_state, dict):
            return beam.collapsed_state.get("symbol", "*")
        if isinstance(beam.collapsed_state, str):
            return beam.collapsed_state
    except Exception:
        pass
    return "*"  # Default fallback