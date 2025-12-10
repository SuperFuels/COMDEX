# File: backend/modules/glyphnet/glyphwave_simulator.py

import time
import logging
from typing import List, Dict, Any, Optional

from backend.modules.glyphnet.glyphwave_encoder import (
    glyphs_to_waveform,
    save_wavefile,
    decode_waveform_to_glyphs,
)
from backend.modules.glyphnet.glyphnet_packet import create_gip_packet

logger = logging.getLogger(__name__)

# Internal simulation trace log
simulation_log: List[Dict[str, Any]] = []


def simulate_waveform_transmission(
    glyphs: str,
    sender: str = "simulator",
    save_path: str = "simulated_output.wav",
    loopback: bool = True,
) -> Dict[str, Any]:
    """
    Simulates the full transmission of a glyph string into waveform.
    - Encodes glyphs into waveform
    - Saves .wav file
    - Builds GIP packet
    - Optionally decodes waveform back into glyphs (loopback check)
    - Logs transmission trace with fidelity confidence
    """
    try:
        # Encode
        waveform = glyphs_to_waveform(glyphs)
        save_wavefile(save_path, glyphs)

        # Create simulated GIP packet
        packet = create_gip_packet(
            sender=sender,
            target="loopback",
            glyphs=glyphs,
            metadata={"simulation": "glyphwave_simulator"},
        )

        # Optional round-trip decode
        decoded: List[str] = []
        confidence: Optional[float] = None
        error: Optional[str] = None

        if loopback:
            try:
                decoded = decode_waveform_to_glyphs(waveform)
                if decoded:
                    matches = sum(1 for a, b in zip(glyphs, decoded) if a == b)
                    confidence = matches / max(len(glyphs), 1)
                logger.debug(f"[Simulator] Loopback decoded glyphs: {decoded}, confidence={confidence}")
            except Exception as dec_err:
                error = f"Decode failed: {dec_err}"
                logger.warning(f"[Simulator] Loopback decode failed: {dec_err}")

        # Build trace log
        trace: Dict[str, Any] = {
            "timestamp": time.time(),
            "status": "ok" if error is None else "error",
            "type": "simulation",
            "glyphs": glyphs,
            "decoded": decoded,
            "confidence": confidence,
            "error": error,
            "sender": sender,
            "file": save_path,
            "packet": packet,
        }

        simulation_log.append(trace)
        logger.info(f"[Simulator] Glyphs encoded -> {save_path}, loopback={loopback}, status={trace['status']}")
        return {"status": trace["status"], "trace": trace}

    except Exception as e:
        logger.exception("[Simulator] Simulation failed")
        trace = {
            "timestamp": time.time(),
            "status": "error",
            "type": "simulation",
            "glyphs": glyphs,
            "decoded": [],
            "confidence": None,
            "error": str(e),
            "sender": sender,
            "file": save_path,
            "packet": None,
        }
        simulation_log.append(trace)
        return {"status": "error", "message": str(e), "trace": trace}


def get_simulation_log(
    n: int = 10,
    sender: Optional[str] = None,
    glyph: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve the last n simulation traces with optional filters.
    - sender: filter by sender id
    - glyph: filter if glyph is present in trace["glyphs"]
    - status: filter by "ok" / "error"
    """
    logs = simulation_log

    if sender:
        logs = [l for l in logs if l.get("sender") == sender]
    if glyph:
        logs = [l for l in logs if glyph in l.get("glyphs", "")]
    if status:
        logs = [l for l in logs if l.get("status") == status]

    return logs[-n:]


def simulate_waveform_transmission(
    glyphs: List[Any],
    sender: str = "local",
) -> Dict[str, Any]:
    """
    Dev / test helper used by glyph_transport_switch for 'local' transport.
    Returns a simple trace structure; no real I/O.
    """
    trace = {
        "sender": sender,
        "glyph_count": len(glyphs),
        "file": "simulated_local_waveform.wav",  # keep shape that caller expects
    }
    logger.info(
        "[GlyphWaveSim] simulate_waveform_transmission: sender=%s glyphs=%d",
        sender,
        len(glyphs),
    )
    return {"trace": trace}


def simulate_waveform_loopback(glyphs: List[Any]) -> None:
    """
    Fallback no-op loopback used when simulate_waveform_transmission fails.
    """
    logger.info(
        "[GlyphWaveSim] simulate_waveform_loopback: glyphs=%d (no-op)",
        len(glyphs),
    )