# File: backend/modules/glyphos/remote_glyph_router.py

import asyncio
from backend.modules.hexcore.memory_engine import MEMORY
from backend.modules.dna_chain.teleport import TeleportEngine
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.glyphos.glyph_parser import StructuredGlyph

class RemoteGlyphRouter:
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.teleport_engine = TeleportEngine(state_manager)

    async def route_remote_glyph(self, glyph_str: str, x: int, y: int, z: int):
        """
        Parse ⧉: glyph and route it to appropriate container or agent.
        Example:
            ⧉:⟦ Memory | Partner : AION -> Reflect ⟧
        """
        if not glyph_str.startswith("⧉:"):
            return

        payload = glyph_str[2:].strip()

        try:
            sg = StructuredGlyph(payload)
            glyph_data = sg.to_dict()
        except Exception as e:
            MEMORY.store({
                "role": "system",
                "type": "glyph_router_error",
                "content": f"❌ Failed to parse remote glyph at ({x},{y},{z}): {e}",
                "data": {"raw": glyph_str}
            })
            return

        # Destination
        target = glyph_data.get("target", "Unknown")
        action = glyph_data.get("action", "Reflect")
        metadata = {
            "origin": {"x": x, "y": y, "z": z},
            "glyph": glyph_str,
            "parsed": glyph_data
        }

        if target == "Unknown":
            MEMORY.store({
                "role": "system",
                "type": "glyph_router_warning",
                "content": f"⚠️ Remote glyph has no valid target at ({x},{y},{z})",
                "data": metadata
            })
            return

        # Route via symbolic teleport
        try:
            success = await self.teleport_engine.send_remote_intent(
                target_container_id=target,
                glyph_payload=glyph_data,
                origin_coord=(x, y, z)
            )

            if success:
                MEMORY.store({
                    "role": "system",
                    "type": "glyph_routed",
                    "content": f"🌐 Routed remote glyph ⧉ at ({x},{y},{z}) -> {target}:{action}",
                    "data": metadata
                })
            else:
                MEMORY.store({
                    "role": "system",
                    "type": "glyph_routing_failed",
                    "content": f"🚫 Remote glyph ⧉ routing failed at ({x},{y},{z}) -> {target}:{action}",
                    "data": metadata
                })

        except Exception as e:
            MEMORY.store({
                "role": "system",
                "type": "glyph_router_exception",
                "content": f"🔥 Exception during ⧉ routing at ({x},{y},{z}): {e}",
                "data": metadata
            })