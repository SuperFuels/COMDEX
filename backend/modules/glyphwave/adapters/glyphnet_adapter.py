"""
🔌 GlyphWave Unified Adapter

Combines:
- GIP-compatible symbolic packet routing (Dict[str, Any])
- GWIP-compatible WaveState transmission (via GlyphNet)
- Automatic GlyphWave enablement toggle via `gw_enabled()`
- Fallback to legacy GIP handlers when GlyphWave is disabled
"""

import time
import uuid
from typing import Dict, Any, Optional

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.feature_flag import gw_enabled
from backend.modules.glyphwave.runtime import GlyphWaveRuntime
from backend.modules.glyphwave.core.entangled_wave import EntangledWave
from backend.modules.glyphwave.constants import DEFAULT_PHASE_RAD as DEFAULT_PHASE
DEFAULT_AMPLITUDE = 1.0  # define inline if not used elsewhere


# Legacy GIP fallback
from backend.modules.gip.gip_adapter_net import (
    legacy_send_gip_packet,
    legacy_recv_gip_packet
)

# GWIP transmit
from backend.modules.glyphnet.glyphnet_transceiver import transmit_gwave_packet

# Cached runtime instance
_runtime: Optional[GlyphWaveRuntime] = None

def get_runtime() -> GlyphWaveRuntime:
    global _runtime
    if _runtime is None:
        _runtime = GlyphWaveRuntime()
    return _runtime


# ═══════════════════════════════════════════════════
# ✴ GIP-Compatible Packet Router (Dict[str, Any])
# ═══════════════════════════════════════════════════

def send_packet(packet: Dict[str, Any]) -> None:
    """
    Sends a symbolic packet using GlyphWaveRuntime if enabled,
    otherwise falls back to legacy GIP sender.
    """
    if gw_enabled():
        get_runtime().send(packet)
    else:
        legacy_send_gip_packet(packet)


def recv_packet() -> Optional[Dict[str, Any]]:
    """
    Receives a symbolic packet using GlyphWaveRuntime if enabled,
    or from the legacy GIP receiver.
    """
    if gw_enabled():
        packet = get_runtime().recv()
        if packet:
            return packet
    return legacy_recv_gip_packet()


# ═══════════════════════════════════════════════════
# ✴ WaveState -> GWIP (GlyphNet Interchange Packet)
# ═══════════════════════════════════════════════════

def wave_to_gwip(wave: WaveState) -> Dict:
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
    return WaveState(
        id=gwip.get("id", str(uuid.uuid4())),
        phase=gwip.get("phase", DEFAULT_PHASE),
        amplitude=gwip.get("amplitude", DEFAULT_AMPLITUDE),
        coherence=gwip.get("coherence", 1.0),
        origin_trace=gwip.get("origin_trace", []),
        timestamp=gwip.get("timestamp", time.time()),
        metadata=gwip.get("metadata", {}),
    )


def send_wave(wave: WaveState) -> Optional[str]:
    """
    Sends a WaveState as a GlyphWave Interchange Packet (GWIP).
    Returns the packet ID if successful, or None.
    """
    if not gw_enabled():
        return None
    gwip = wave_to_gwip(wave)
    return transmit_gwave_packet(gwip)


def receive_wave() -> Optional[WaveState]:
    """
    Receives a GWIP and decodes it into a WaveState.
    """
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