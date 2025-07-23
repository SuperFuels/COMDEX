# backend/modules/glyphnet/glyph_transmitter.py

import logging
from typing import List, Literal, Dict, Optional
import numpy as np

from backend.modules.glyphnet.glyphwave_encoder import glyphs_to_waveform, save_wavefile

try:
    import sounddevice as sd
except ImportError:
    sd = None

logger = logging.getLogger(__name__)

CHANNEL = Literal["audio", "led", "rf"]

def transmit_glyphs(symbols: List[str], channel: CHANNEL = "audio", gain: float = 0.7, duration: float = 2.0) -> Dict[str, any]:
    """
    Transmit symbolic glyphs through a selected physical channel.
    """
    try:
        waveform = glyphs_to_waveform(symbols, gain=gain)
        response = {"status": "ok", "channel": channel}

        if channel == "audio":
            if sd:
                sd.play(waveform, samplerate=44100)
                sd.wait()
                response["details"] = "Audio transmitted"
            else:
                response["error"] = "sounddevice not available"

        elif channel == "led":
            logger.info("[LED] Symbolic LED transmission not implemented in software mode.")
            response["warning"] = "LED not active in current environment"

        elif channel == "rf":
            logger.info("[RF] Symbolic RF transmission not implemented in current env.")
            response["warning"] = "RF hardware not active"

        else:
            return {"status": "error", "error": f"Unknown channel {channel}"}

        return response

    except Exception as e:
        logger.exception("[Transmitter] Failed to transmit glyphs")
        return {"status": "error", "error": str(e)}