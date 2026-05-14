# File: backend/modules/sqi/sqi_beam_logger.py

"""
sqi_beam_logger.py
===================

Symbolic audit logger for QWave beam processing lifecycle.
Logs collapse traces, mutations, SQI scores, SoulLaw status, entropy metrics,
and beam event timelines. Used for symbolic replay, debugging, and research.

Supports:
- File + console + GHX logging
- JSON packet generation for storage or broadcast
- Symbolic compression of beam events (optional)
"""

import json
import logging
from typing import Dict
from datetime import datetime

from backend.modules.quantum.wave_state import WaveState
from backend.modules.codex.codex_metrics import format_entropy_metric
from backend.modules.glyphvault.glyph_serializer import compress_symbolic_beam
from backend.modules.ghx.ghx_broadcast import send_hud_overlay

logger = logging.getLogger("SQI.BEAM")


def log_beam_event(beam: WaveState, stage: str = "final") -> None:
    """
    Log full symbolic beam processing event.
    `stage` = one of: init, collapsed, mutated, final, error
    """
    try:
        event = build_beam_log_packet(beam, stage)

        # Local console or log file
        logger.info(f"[SQI] [{stage.upper()}] Beam {beam.id} | SQI={beam.sqi_score:.3f} | State={beam.status}")

        # Optional: stream to HUD or GHX overlay
        send_hud_overlay({
            "type": "beam_event",
            "beam_id": beam.id,
            "stage": stage,
            "symbol": event["symbol"],
            "score": event["sqi_score"],
            "status": event["status"],
        })

        # Optional: JSON serialization for archive
        serialized = json.dumps(event, indent=2)
        with open(f"logs/beam_{beam.id}_{stage}.json", "w") as f:
            f.write(serialized)

    except Exception as e:
        logger.warning(f"[SQI] Logging failed for beam {beam.id}: {e}", exc_info=True)


def build_beam_log_packet(beam: WaveState, stage: str = "final") -> Dict:
    """
    Construct a structured symbolic log packet for a beam.
    """
    return {
        "id": beam.id,
        "timestamp": datetime.utcnow().isoformat(),
        "stage": stage,
        "symbol": _extract_symbol(beam),
        "collapsed_state": beam.collapsed_state,
        "mutation_trace": beam.mutation_trace,
        "sqi_score": beam.sqi_score,
        "entropy": format_entropy_metric(beam.entropy),
        "soullaw": {
            "status": beam.soullaw_status,
            "violations": beam.soullaw_violations,
        },
        "origin": beam.origin,
        "status": beam.status,
        "compressed": compress_symbolic_beam(beam),
    }


def _extract_symbol(beam: WaveState) -> str:
    try:
        if isinstance(beam.collapsed_state, dict):
            return beam.collapsed_state.get("symbol", "*")
        if isinstance(beam.collapsed_state, str):
            return beam.collapsed_state
    except Exception:
        pass
    return "*"