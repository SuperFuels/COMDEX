# backend/modules/glyphnet/gip_adapter_wave.py

import base64
import json
from typing import Dict, Any

WAVE_HEADER = b'GLYPHWAVE_START'
WAVE_FOOTER = b'GLYPHWAVE_END'

def encode_gip_to_waveform(gip_packet: Dict[str, Any], compress: bool = False) -> bytes:
    """
    Encodes a GIP packet into a waveform-safe byte stream.
    Optionally compresses the payload.
    """
    raw_json = json.dumps(gip_packet).encode("utf-8")
    payload = base64.b64encode(raw_json)
    return WAVE_HEADER + payload + WAVE_FOOTER

def decode_waveform_to_gip(data: bytes) -> Dict[str, Any]:
    """
    Decodes waveform byte stream back into a GIP packet.
    """
    if not data.startswith(WAVE_HEADER) or not data.endswith(WAVE_FOOTER):
        raise ValueError("Invalid waveform packet")

    payload = data[len(WAVE_HEADER):-len(WAVE_FOOTER)]
    raw_json = base64.b64decode(payload)
    return json.loads(raw_json.decode("utf-8"))