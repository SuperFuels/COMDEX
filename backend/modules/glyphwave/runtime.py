"""
🧠 GlyphWaveRuntime – High-Level Runtime for GWIP Routing

Orchestrates:
    • GWIP encoding/decoding (via GWIPCodec)
    • Phase scheduling and envelope shaping (via PhaseScheduler)
    • Carrier I/O (in-memory or physical drivers)
    • Telemetry logging (via WaveScope)

Use this in:
    • SQI Event Bus hooks
    • GlyphNet symbolic routers
    • GHX broadcast engines
"""

from typing import Dict, Any, Optional
from .gwip_codec import GWIPCodec
from .scheduler import PhaseScheduler
from .carrier_memory import MemoryCarrier
from .wavescope import WaveScope


class GlyphWaveRuntime:
    def __init__(
        self,
        carrier: Optional[Any] = None,
        codec: Optional[GWIPCodec] = None,
        scheduler: Optional[PhaseScheduler] = None,
        scope: Optional[WaveScope] = None
    ):
        self.codec = codec or GWIPCodec()
        self.scheduler = scheduler or PhaseScheduler()
        self.carrier = carrier or MemoryCarrier()
        self.scope = scope or WaveScope()

    def send(self, gip_packet: Dict[str, Any]) -> None:
        """
        Encode, schedule, and emit a GIP packet via GlyphWave.

        Args:
            gip_packet (Dict[str, Any]): The symbolic packet to send.
        """
        upgraded = self.codec.upgrade(gip_packet)
        shaped = self.scheduler.schedule(upgraded)
        self.carrier.emit(shaped)
        self.scope.log_beam_event(
            event="emitted",
            signal_power=shaped["envelope"].get("freq", 1.0),
            noise_power=0.0001,  # TODO: dynamic noise model
            kind="gwip",
            tags=shaped["envelope"].get("tags", []),
            container_id=gip_packet.get("container_id"),
        )

    def recv(self) -> Optional[Dict[str, Any]]:
        """
        Capture and decode a GWIP packet.

        Returns:
            Optional[Dict[str, Any]]: The original GIP payload, if any.
        """
        gwip = self.carrier.capture()
        if not gwip:
            return None
        gip = self.codec.downgrade(gwip)
        self.scope.log_beam_event(
            event="received",
            signal_power=gwip["envelope"].get("freq", 1.0),
            noise_power=0.0001,  # TODO: dynamic noise model
            kind="gwip",
            tags=gwip["envelope"].get("tags", []),
            container_id=gip.get("container_id"),
        )
        return gip

    def metrics(self) -> Dict[str, Any]:
        """
        Return runtime metrics for carrier, scheduler, and throughput.

        Returns:
            Dict[str, Any]: Metric snapshot.
        """
        return {
            "scheduler": self.scheduler.metrics(),
            "carrier": self.carrier.stats(),
            "throughput": self.scope.track_throughput(),
        }

    def recent_logs(self, limit: int = 100) -> Any:
        """
        Return recent beam event logs.

        Args:
            limit (int): How many logs to return.

        Returns:
            List[Dict[str, Any]]: Telemetry events.
        """
        return self.scope.recent(limit)

    def close(self) -> None:
        """
        Cleanly shut down carrier and clear state.
        """
        self.carrier.close()
        self.scope.reset()