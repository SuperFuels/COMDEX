# backend/modules/glyphnet/glyph_beacon.py

import time
import logging
from typing import Dict, Optional, Union

from backend.modules.glyphnet.glyphwave_encoder import glyphs_to_waveform, save_wavefile
from backend.modules.glyphnet.glyphnet_packet import create_gip_packet

logger = logging.getLogger(__name__)

beacon_log: list = []

def emit_symbolic_beacon(
    glyphs: Union[str, list],
    sender: str = "AION",
    destination: Optional[str] = None,
    play_audio: bool = False,
    save_path: Optional[str] = None
) -> Dict:

    packet = create_gip_packet(
        sender=sender,
        target=destination or "broadcast",
        glyphs=glyphs,
        metadata={"transmission": "symbolic_wave_beacon"},
    )

    timestamp = time.time()
    waveform = glyphs_to_waveform(glyphs)

    if save_path:
        save_wavefile(save_path, glyphs)
        logger.info(f"[Beacon] Saved waveform to {save_path}")

    if play_audio:
        try:
            import simpleaudio as sa
            play_obj = sa.play_buffer(waveform, 1, 2, 44100)
            play_obj.wait_done()
        except Exception as e:
            logger.warning(f"[Beacon] Audio playback failed: {e}")

    entry = {
        "packet": packet,
        "glyphs": glyphs,
        "timestamp": timestamp,
        "sender": sender,
        "target": destination or "broadcast"
    }
    beacon_log.append(entry)
    return {"status": "emitted", "packet": packet, "timestamp": timestamp}


def get_beacon_log(n: int = 10):
    return beacon_log[-n:]