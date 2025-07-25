# backend/modules/teleport/portal_manager.py

from typing import Dict, Optional
import uuid

from backend.modules.teleport.teleport_packet import TeleportPacket
from backend.modules.glyphvault.vault_manager import VAULT

# Lazy-loaded container runtime to prevent circular import
ContainerRuntimeClass = None


class PortalManager:
    """
    Manages symbolic portals between containers. Each portal has a unique ID,
    a source container, and a target destination.
    """

    def __init__(self):
        self.portal_map: Dict[str, Dict[str, str]] = {}  # portal_id → { source: container_id, target: container_id }

    def register_portal(self, source: str, target: str) -> str:
        portal_id = str(uuid.uuid4())
        self.portal_map[portal_id] = {
            "source": source,
            "target": target
        }
        return portal_id

    def resolve_target(self, portal_id: str) -> Optional[str]:
        mapping = self.portal_map.get(portal_id)
        return mapping.get("target") if mapping else None

    def resolve(self, portal_id: str) -> Optional[Dict[str, str]]:
        return self.portal_map.get(portal_id)

    def teleport(self, packet: TeleportPacket) -> bool:
        global ContainerRuntimeClass
        if ContainerRuntimeClass is None:
            from backend.modules.runtime.container_runtime import ContainerRuntime
            from backend.modules.consciousness.state_manager import STATE
            ContainerRuntimeClass = lambda: ContainerRuntime(state_manager=STATE)

        target_id = self.resolve_target(packet.portal_id)
        if not target_id:
            return False

        # Save the current state (compressed snapshot) before jumping
        filename = VAULT.save_snapshot(packet.container_id)

        # Load snapshot into new target container
        success = VAULT.load_snapshot(filename, avatar_state=None)
        if success:
            ContainerRuntimeClass().inject_payload(packet.payload)
            return True
        return False


# ✅ Global portal registry instance
PORTALS = PortalManager()