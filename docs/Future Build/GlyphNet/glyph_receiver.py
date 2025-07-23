# backend/modules/glyphnet/glyph_receiver.py

import logging
from typing import List, Dict
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

from backend.modules.glyphnet.glyph_signal_reconstructor import reconstruct_gip_signal

logger = logging.getLogger(__name__)

def receive_glyphs_from_audio(duration: float = 3.0, threshold: float = 0.01) -> Dict[str, any]:
    """
    Records audio and attempts to decode symbolic glyphs from the input.
    """
    try:
        if not sd:
            return {"status": "error", "error": "sounddevice not available"}

        samplerate = 44100
        logger.info(f"[Receiver] Listening for {duration} seconds...")
        audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='float32')
        sd.wait()

        waveform = audio.flatten()

        if np.max(np.abs(waveform)) < threshold:
            return {"status": "ok", "message": "No signal detected", "glyphs": []}

        logger.info("[Receiver] Signal detected, attempting reconstruction...")
        result = reconstruct_gip_signal(waveform.tolist())

        return {"status": "ok", "glyphs": result.get("glyphs", []), "raw": result}

    except Exception as e:
        logger.exception("[Receiver] Glyph reception failed")
        return {"status": "error", "error": str(e)}