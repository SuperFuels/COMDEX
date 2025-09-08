from typing import Dict, Any, Optional
from ..feature_flag import gw_enabled
from ..runtime import GlyphWaveRuntime

from backend.modules.gip.gip_adapter_net import (
    legacy_send_gip_packet,
    legacy_recv_gip_packet
)

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
        legacy_send_gip_packet(packet)

def recv_packet() -> Optional[Dict[str, Any]]:
    if gw_enabled():
        gw_packet = get_runtime().recv()
        if gw_packet:
            return gw_packet
    return legacy_recv_gip_packet()