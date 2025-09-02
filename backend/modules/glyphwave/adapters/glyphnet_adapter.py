# backend/modules/glyphwave/adapters/glyphnet_adapter.py

import time
import json
import uuid
from typing import Dict, Optional

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.feature_flag import gw_enabled
from backend.modules.glyphwave.core.entangled_wave import EntangledWave
from backend.modules.glyphwave.constants import DEFAULT_PHASE, DEFAULT_AMPLITUDE

# Placeholder transmit/receive interfaces — replace with real GlyphNet I/O
from backend.modules.glyphnet.glyphnet_transceiver import transmit_gwave_packet, receive_gwave_packet


def wave_to_gwip(wave: WaveState) -> Dict:
    """Convert WaveState to .gwip-compatible dict"""
    return {
        "id": wave.id,
        "phase": wave.phase,
        "amplitude": wave.amplitude,
        "coherence": wave.coherence,
        "origin_trace": wave.origin_trace,
        "timestamp": wave.timestamp,
        "metadata": wave.metadata or {},
    }


def gwip_to_wave(gwip: Dict) -> WaveState:
    """Convert .gwip dictionary to WaveState"""
    return WaveState(
        id=gwip.get("id", str(uuid.uuid4())),
        phase=gwip.get("phase", DEFAULT_PHASE),
        amplitude=gwip.get("amplitude", DEFAULT_AMPLITUDE),
        coherence=gwip.get("coherence", 1.0),
        origin_trace=gwip.get("origin_trace", []),
        timestamp=gwip.get("timestamp", time.time()),
        metadata=gwip.get("metadata", {}),
    )


def send_packet(wave: WaveState) -> Optional[str]:
    """Send a WaveState as a GlyphWave Interchange Packet (GWIP)"""
    if not gw_enabled():
        return None  # Fallback mode: do nothing

    gwip = wave_to_gwip(wave)
    packet_id = transmit_gwave_packet(gwip)
    return packet_id


def receive_packet() -> Optional[WaveState]:
    """Receive and decode a GWIP into a WaveState"""
    if not gw_enabled():
        return None

    packet = receive_gwave_packet()
    if not packet:
        return None

    try:
        return gwip_to_wave(packet)
    except Exception as e:
        print(f"[GlyphNetAdapter] Failed to parse GWIP: {e}")
        return None