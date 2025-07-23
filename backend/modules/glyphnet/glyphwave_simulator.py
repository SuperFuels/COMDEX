# backend/modules/glyphnet/glyphwave_simulator.py

import time
import logging
from typing import List, Dict

from backend.modules.glyphnet.glyphwave_encoder import glyphs_to_waveform, save_wavefile
from backend.modules.glyphnet.glyphnet_packet import create_gip_packet

logger = logging.getLogger(__name__)

simulation_log: List[Dict] = []


def simulate_waveform_transmission(glyphs: str, sender="simulator", save_path="simulated_output.wav") -> Dict:
    """
    Simulates the full transmission of a glyph string into waveform.
    Saves to .wav and logs the transmission.
    """
    try:
        waveform = glyphs_to_waveform(glyphs)
        save_wavefile(save_path, glyphs)

        packet = create_gip_packet(
            sender=sender,
            target="loopback",
            glyphs=glyphs,
            metadata={"simulation": "glyphwave_simulator"},
        )

        trace = {
            "timestamp": time.time(),
            "type": "simulation",
            "glyphs": glyphs,
            "sender": sender,
            "file": save_path,
            "packet": packet,
        }

        simulation_log.append(trace)
        logger.info(f"[Simulator] Glyphs encoded and saved to {save_path}")
        return {"status": "ok", "trace": trace}

    except Exception as e:
        logger.exception("[Simulator] Simulation failed")
        return {"status": "error", "message": str(e)}


def get_simulation_log(n: int = 10) -> List[Dict]:
    return simulation_log[-n:]