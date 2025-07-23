# backend/modules/glyphnet/glyph_io_controller.py

import logging
from typing import Dict, Any, List, Optional

from backend.modules.glyphnet.glyphwave_encoder import glyphs_to_waveform, save_wavefile
from backend.modules.glyphnet.glyph_receiver import receive_glyphs_from_audio
from backend.modules.glyphnet.glyph_beacon import emit_glyph_beacon
from backend.modules.glyphnet.glyphnet_packet import create_gip_packet, push_symbolic_packet

logger = logging.getLogger(__name__)

class GlyphIOController:
    """
    Manages symbolic glyph I/O across various channels:
    - Audio (waveform output, microphone input)
    - Beacon broadcast
    - Local packet push
    """

    def __init__(self):
        self.active_mode = "idle"

    def output_glyphs_as_audio(self, glyphs: List[str], filename: Optional[str] = None) -> Dict[str, Any]:
        try:
            waveform = glyphs_to_waveform(glyphs)
            if filename:
                save_wavefile(waveform, filename)
                return {"status": "ok", "saved": filename}
            else:
                return {"status": "ok", "waveform": waveform.tolist()}
        except Exception as e:
            logger.exception("[IOController] Audio output failed")
            return {"status": "error", "error": str(e)}

    def listen_for_glyphs(self, duration: float = 3.0) -> Dict[str, Any]:
        return receive_glyphs_from_audio(duration)

    def emit_beacon(self, glyphs: List[str], mode: str = "audio", metadata: Optional[Dict] = None) -> Dict[str, Any]:
        try:
            return emit_glyph_beacon(glyphs, mode=mode, metadata=metadata)
        except Exception as e:
            logger.exception("[IOController] Beacon emit failed")
            return {"status": "error", "error": str(e)}

    def push_packet(self, glyphs: List[str], destination: str) -> Dict[str, Any]:
        try:
            packet = create_gip_packet(glyphs, destination=destination)
            result = push_symbolic_packet(packet)
            return {"status": "ok", "result": result}
        except Exception as e:
            logger.exception("[IOController] Packet push failed")
            return {"status": "error", "error": str(e)}