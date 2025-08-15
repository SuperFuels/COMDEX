# backend/modules/teleport/wormhole_manager.py

from typing import Dict, Any
from backend.modules.vault.container_vault_manager import ContainerVaultManager
from backend.modules.runtime.container_runtime import ContainerRuntime
from backend.modules.websocket.glyphnet_ws import broadcast_glyph_event

def teleport_to_container(container_id: str, source: str = "GHX") -> Dict[str, Any]:
    """
    Load and teleport into the specified container.
    Typically triggered by clicking an electron or from replay links.

    Args:
        container_id (str): ID of the .dc container to teleport to
        source (str): Optional metadata for logging or symbolic source tracing

    Returns:
        Dict[str, Any]: The full decrypted container data.
    """
    print(f"🚪 Teleporting to container: {container_id} (triggered by {source})")

    container_data = ContainerVaultManager.get_decrypted_container(container_id)
    if not container_data:
        raise ValueError(f"❌ Failed to load container: {container_id}")

    # Optional: update the runtime to make this the current active container
    ContainerRuntime.set_current_container(container_id)

    # Optionally broadcast to clients for sync
    broadcast_glyph_event({
        "event": "teleport",
        "container_id": container_id,
        "source": source,
        "isAtom": container_data.get("container_kind") == "atom",
        "electronCount": len(container_data.get("electrons", []))
    })

    return container_data