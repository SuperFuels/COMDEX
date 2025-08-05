# 📁 backend/modules/teleport/portal_manager.py

from typing import Dict, Optional
import uuid

from backend.modules.glyphvault.vault_manager import VAULT

# Lazy-loaded ContainerRuntime to avoid circular imports
ContainerRuntimeClass = None


def create_teleport_packet(portal_id: str, container_id: str, payload: dict):
    """
    Lazily import TeleportPacket to avoid circular import between teleport_packet and portal_manager.
    """
    from backend.modules.teleport.teleport_packet import TeleportPacket
    return TeleportPacket(portal_id=portal_id, container_id=container_id, payload=payload)


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

    def teleport(self, packet) -> bool:
        """
        Teleport logic: saves current state, loads into target container, injects payload.
        """
        global ContainerRuntimeClass
        if ContainerRuntimeClass is None:
            from backend.modules.runtime.container_runtime import ContainerRuntime
            from backend.modules.consciousness.state_manager import STATE
            ContainerRuntimeClass = lambda: ContainerRuntime(state_manager=STATE)

        target_id = self.resolve_target(packet.portal_id)
        if not target_id:
            return False

        # Save snapshot of current state
        filename = VAULT.save_snapshot(packet.container_id)

        # Load snapshot into target container
        success = VAULT.load_snapshot(filename, avatar_state=None)
        if success:
            ContainerRuntimeClass().inject_payload(packet.payload)
            return True
        return False


# ✅ Global portal registry instance
PORTALS = PortalManager()