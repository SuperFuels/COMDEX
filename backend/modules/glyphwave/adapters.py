"""
🔌 GlyphWave Adapters + GIP Compatibility Hooks

Drop-in helpers so callers can remain GIP-native while using GlyphWave runtime when enabled.
Routes symbolic packets via GlyphWave if enabled; otherwise falls back to legacy GIP handlers.
"""

from typing import Dict, Any, Optional
from .feature_flag import gw_enabled
from .runtime import GlyphWaveRuntime

# Legacy GIP fallback modules
from backend.modules.gip.gip_adapter_net import (
    legacy_send_gip_packet,
    legacy_recv_gip_packet
)

# Cached runtime instance
_runtime: Optional[GlyphWaveRuntime] = None

def get_runtime() -> GlyphWaveRuntime:
    """
    Returns a singleton instance of the GlyphWaveRuntime.
    """
    global _runtime
    if _runtime is None:
        _runtime = GlyphWaveRuntime()
    return _runtime


# ═══════════════════════════════════════════════════
# C1a: Send path → wrap send_packet(gip)
# ═══════════════════════════════════════════════════
def send_packet(packet: Dict[str, Any]) -> None:
    """
    Sends a symbolic packet using GlyphWave if enabled,
    or routes to the legacy GIP dispatcher as fallback.
    """
    if gw_enabled():
        get_runtime().send(packet)
    else:
        legacy_send_gip_packet(packet)


# ═══════════════════════════════════════════════════
# C1b: Recv path → call recv_packet() before legacy
# ═══════════════════════════════════════════════════
def recv_packet() -> Optional[Dict[str, Any]]:
    """
    Attempts to receive a packet via GlyphWave first (if enabled).
    Falls back to legacy GIP queue/socket if GlyphWave yields no packet.
    """
    if gw_enabled():
        gw_packet = get_runtime().recv()
        if gw_packet:
            return gw_packet
    return legacy_recv_gip_packet()