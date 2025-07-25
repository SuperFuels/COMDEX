"""
GlyphSocket: Symbolic Dispatch Layer for Container Teleportation
Bridges teleport packets with runtime logic: portal resolution, SEC/HSC boot, and dimension kernel dispatch.
"""

from backend.modules.teleport.teleport_packet import TeleportPacket
from backend.modules.glyphnet.container_bootstrap import ContainerBootstrap
from backend.modules.dimensions.dimension_kernel import DimensionKernel
from backend.modules.consciousness.state_manager import STATE
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.teleport.portal_manager import PORTALS

import traceback


class GlyphSocket:
    def __init__(self):
        self.portal_manager = PORTALS
        self.bootstrap = ContainerBootstrap()
        self.memory_engine = MemoryEngine()

    def dispatch(self, packet_data: dict) -> dict:
        """
        Main entry point. Accepts a raw teleport packet dict,
        decodes and routes it to the correct container/runtime.

        Returns result metadata or error.
        """
        try:
            # 📨 Decode teleportation packet
            packet = TeleportPacket.from_dict(packet_data)

            # 🌀 Resolve portal
            portal_info = self.portal_manager.resolve(packet.portal_id)
            if not portal_info:
                return {"status": "❌ Unknown portal_id", "portal_id": packet.portal_id}

            destination_id = portal_info.get("destination_container")
            if not destination_id:
                return {"status": "❌ No destination set in portal", "portal_id": packet.portal_id}

            # 🚀 Bootstrap or resume container
            container = self.bootstrap.resume_or_boot(destination_id)
            if not container:
                return {"status": "❌ Failed to bootstrap container", "container_id": destination_id}

            # 🌌 Inject into dimension kernel
            kernel: DimensionKernel = container.get("dimension_kernel")
            if not kernel:
                return {"status": "❌ No runtime kernel attached", "container_id": destination_id}

            # 🧭 Route data (if present)
            if packet.payload:
                x, y, z, t = packet.coords or (0, 0, 0, 0)
                for glyph in packet.payload.get("glyphs", []):
                    kernel.place_glyph(x, y, z, t, glyph)

                event = packet.payload.get("event")
                if event:
                    kernel.trigger_event(x, y, z, t, event)

                avatar = packet.payload.get("avatar_id")
                if avatar:
                    kernel.mark_avatar_location(avatar, {"x": x, "y": y, "z": z, "t": t})

            # 🔁 Sync memory state
            if packet.payload.get("memory") is not None:
                self.memory_engine.import_memory_block(packet.payload["memory"])

            # ✅ Done
            return {
                "status": "✅ Teleportation complete",
                "container_id": destination_id,
                "portal": packet.portal_id,
                "tick": kernel.runtime_ticks,
                "injected": bool(packet.payload)
            }

        except Exception as e:
            traceback.print_exc()
            return {
                "status": "❌ Dispatch error",
                "error": str(e),
                "trace": traceback.format_exc()
            }