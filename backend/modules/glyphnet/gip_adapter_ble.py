# backend/modules/glyphnet/gip_adapter_ble.py

import logging
import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class GIPBluetoothAdapter:
    """
    Stub Bluetooth adapter for Glyph Internet Protocol (GIP).

    This is a placeholder:
      - logs outgoing packets,
      - provides a simple in-memory receive_loop so we can
        test integration without OS-level BLE yet.
    """

    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id or "ble_stub_device"
        self._running = False
        self._inbound: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()

    async def send_packet(self, packet: Dict[str, Any]) -> None:
        """
        Serialize and send a GIP packet over BLE.

        Stub behaviour:
          - log the packet
          - (later) call into native BLE layer
        """
        logger.info(
            "[BLE] (stub) send_packet from %s: type=%s",
            self.device_id,
            packet.get("type") or packet.get("event") or "unknown",
        )
        # TODO: integrate with native BLE (BlueZ/CoreBluetooth/etc.)

    async def receive_loop(
        self,
        on_packet: Callable[[Dict[str, Any]], Awaitable[None]],
    ) -> None:
        """
        Listen for incoming BLE frames and decode into GIP packets.

        Stub behaviour:
          - waits on an in-memory queue that tests can push into
            using inject_test_packet().
        """
        logger.info("[BLE] (stub) receive_loop started for %s", self.device_id)
        self._running = True
        try:
            while self._running:
                pkt = await self._inbound.get()
                await on_packet(pkt)
        except asyncio.CancelledError:
            logger.info("[BLE] receive_loop cancelled for %s", self.device_id)
        finally:
            self._running = False
            logger.info("[BLE] receive_loop stopped for %s", self.device_id)

    async def scan_peers(self) -> List[str]:
        """
        Scan for nearby BLE peers.

        Stub behaviour:
          - returns empty list.
        """
        logger.info("[BLE] (stub) scan_peers called for %s", self.device_id)
        return []

    async def inject_test_packet(self, packet: Dict[str, Any]) -> None:
        """
        Test helper: push a packet into the receive_loop queue.
        """
        await self._inbound.put(packet)

    async def close(self) -> None:
        """
        Stop the adapter and any receive loops.
        """
        logger.info("[BLE] (stub) closing adapter for %s", self.device_id)
        self._running = False