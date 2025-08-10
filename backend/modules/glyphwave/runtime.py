"""
High-level façade: orchestrates GWIP codec + scheduler + carrier.
Use this from SQI bus or GlyphNet routers.
"""
from typing import Dict, Any, Optional
from .gwip_codec import GWIPCodec
from .scheduler import PhaseScheduler
from .carrier_memory import MemoryCarrier
from .wavescope import WaveScope

class GlyphWaveRuntime:
    def __init__(self, carrier=None, codec=None, scheduler=None, scope=None):
        self.codec = codec or GWIPCodec()
        self.scheduler = scheduler or PhaseScheduler()
        self.carrier = carrier or MemoryCarrier()
        self.scope = scope or WaveScope()

    def send(self, gip_packet: Dict[str, Any]) -> None:
        gwip = self.codec.upgrade(gip_packet)
        gwip = self.scheduler.schedule(gwip)
        self.carrier.emit(gwip)
        self.scope.log("emit", kind="gwip", meta=gwip.get("envelope", {}))

    def recv(self) -> Optional[Dict[str, Any]]:
        gwip = self.carrier.capture()
        if not gwip:
            return None
        gip = self.codec.downgrade(gwip)
        self.scope.log("capture", kind="gwip", meta=gwip.get("envelope", {}))
        return gip

    def metrics(self) -> Dict[str, Any]:
        return {
            "scheduler": self.scheduler.metrics(),
            "carrier": self.carrier.stats(),
        }