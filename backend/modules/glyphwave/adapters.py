"""
Drop-in helpers so callers can stay GIP-native while benefiting from GW when enabled.
"""
from typing import Dict, Any, Optional
from .feature_flag import gw_enabled
from .runtime import GlyphWaveRuntime

_runtime: Optional[GlyphWaveRuntime] = None

def get_runtime() -> GlyphWaveRuntime:
    global _runtime
    if _runtime is None:
        _runtime = GlyphWaveRuntime()
    return _runtime

def send_packet(packet: Dict[str, Any]) -> None:
    if gw_enabled():
        get_runtime().send(packet)
    else:
        # legacy path: no-op hook or call your old GIP dispatcher
        # TODO: wire to backend.modules.gip.gip_adapter_net / http as needed
        pass

def recv_packet() -> Optional[Dict[str, Any]]:
    if gw_enabled():
        return get_runtime().recv()
    # legacy path would block on your classic queue/socket
    return None