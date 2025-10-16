# ============================================================
# 📁 backend/modules/teleport/wormhole_manager.py
# ============================================================

"""
WormholeManager — symbolic teleportation and inter-container state transport.
Part of the Tessaris Quantum Quad Core (QQC) teleportation subsystem.

Handles creation, stabilization, and transfer of symbolic container states
through holographic or beam-linked wormholes.
"""

from typing import Dict, Any, Optional
import logging
from backend.modules.glyphvault.container_vault_manager import ContainerVaultManager
from backend.modules.runtime.container_runtime import ContainerRuntime
from backend.routes.ws.glyphnet_ws import broadcast_glyph_event

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# 🔊 Safe bridge between teleport and WebSocket broadcast
# ---------------------------------------------------------------------
def broadcast_glyph_event(event_type_or_dict, payload=None):
    """
    Safe bridge between teleport events and the GlyphNet WebSocket broadcast layer.
    Works with both single-dict and (event_type, payload) formats.
    """
    try:
        # 🔍 Import the correct handler
        from backend.routes.ws.glyphnet_ws import throttled_broadcast

        if payload is None and isinstance(event_type_or_dict, dict):
            # already structured
            event_type = event_type_or_dict.get("type", "unknown")
            payload = event_type_or_dict
        else:
            event_type = event_type_or_dict

        # ✅ call with both args (new signature)
        throttled_broadcast(event_type, payload)

        print(f"[WormholeManager] Broadcasted → {event_type} | {payload}")
    except Exception as e:
        import logging
        logging.warning(f"[⚠️ Wormhole Broadcast] Failed to send event: {e}")

# ---------------------------------------------------------------------
# 🚪 Teleportation Core
# ---------------------------------------------------------------------
def teleport_to_container(container_id: str, source: str = "GHX") -> Dict[str, Any]:
    """
    Load and teleport into the specified container.
    Typically triggered by symbolic or quantum link interactions.

    Args:
        container_id (str): Target container ID (without .dc.json)
        source (str): Name of the initiator or system trigger (default: GHX)

    Returns:
        dict: Parsed container JSON after teleportation
    """
    print(f"🚪 Teleporting to container: {container_id} (triggered by {source})")

    # -----------------------------------------------------------------
    # 1. Load container data from Vault
    # -----------------------------------------------------------------
    try:
        vault = ContainerVaultManager(encryption_key=b"dev_static_key")
        container_data = vault.load_container_by_id(container_id)
        logger.info(f"[Teleport] Loaded container '{container_id}' successfully.")
    except Exception as e:
        logger.error(f"[Teleport] ❌ Failed to load container '{container_id}': {e}")
        raise ValueError(f"❌ Failed to load container '{container_id}': {e}")

    # -----------------------------------------------------------------
    # 2. Update UCS runtime state
    # -----------------------------------------------------------------
    try:
        from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime
        ucs = get_ucs_runtime()
        ucs.set_current_container(container_id)
        logger.info(f"[Teleport] UCS runtime updated to container '{container_id}'.")
    except Exception as e:
        logger.warning(f"[Teleport] ⚠️ Failed to update UCS current container: {e}")

    # -----------------------------------------------------------------
    # 3. Broadcast teleportation event via GlyphNet
    # -----------------------------------------------------------------
    target = container_data.get("id", container_id)
    event_payload = {
        "status": "ok",
        "source": source,
        "target": target,
        "timestamp": time.time(),
        "metadata": {
            "container_type": container_data.get("type", "unknown"),
            "glyph_count": len(container_data.get("glyphs", [])),
        },
    }

    broadcast_glyph_event("wormhole_transfer", event_payload)

    # -----------------------------------------------------------------
    # 4. Update Vault runtime state (if supported)
    # -----------------------------------------------------------------
    try:
        if hasattr(ContainerVaultManager, "update_container_state"):
            ContainerVaultManager.update_container_state(container_id, container_data)
            logger.info(f"[VaultBridge] 🔄 Updated runtime state for container '{container_id}'")
        else:
            logger.debug("[VaultBridge] No update_container_state() available — skipping.")
    except Exception as e:
        logger.warning(f"[Teleport] ⚠️ Vault update failed: {e}")

    # -----------------------------------------------------------------
    # 5. Return the container data for further processing
    # -----------------------------------------------------------------
    return container_data

# ──────────────────────────────────────────────
#  WormholeManager Class
# ──────────────────────────────────────────────
class WormholeManager:
    """
    Orchestrates teleportation and state transfer between symbolic containers.
    Used by QQC to stabilize inter-container coherence.
    """

    def __init__(self):
        self.active_links: Dict[str, Dict[str, Any]] = {}
        self.teleport_history: list[Dict[str, Any]] = []
        logger.info("[WormholeManager] Initialized wormhole subsystem.")

    def stabilize_links(self) -> None:
        """
        Routine maintenance of active wormhole connections.
        Removes stale or broken teleportation links.
        """
        stale = [k for k, v in self.active_links.items() if not v.get("active")]
        for k in stale:
            del self.active_links[k]
        if stale:
            logger.debug(f"[WormholeManager] Cleaned up stale links: {stale}")

    def transfer_state(self, state: Dict[str, Any], dst_container: str) -> Dict[str, Any]:
        """
        Transfers symbolic state to another container.
        """
        try:
            from backend.modules.consciousness.state_manager import StateManager
            runtime = ContainerRuntime(state_manager=StateManager())
            runtime.set_active_container(container_id=dst_container)
            ContainerVaultManager.update_container_state(dst_container, state)
            broadcast_glyph_event({
                "event": "wormhole_transfer",
                "target": dst_container,
                "payload_size": len(str(state)),
            })
            link_id = f"wormhole_{dst_container}"
            self.active_links[link_id] = {"target": dst_container, "active": True}
            self.teleport_history.append({"target": dst_container, "state": state})
            logger.info(f"[WormholeManager] ↯ State transferred to {dst_container}")
            return {"status": "ok", "target": dst_container}
        except Exception as e:
            logger.error(f"[WormholeManager] ❌ Transfer failed: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    def extract_state(self, src_container: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves symbolic state from a container for teleportation.
        """
        try:
            state = ContainerVaultManager.get_decrypted_container(src_container)
            if not state:
                raise ValueError(f"Source container not found: {src_container}")
            logger.info(f"[WormholeManager] Extracted state from {src_container}")
            return state
        except Exception as e:
            logger.error(f"[WormholeManager] ❌ Extraction failed: {e}")
            return None

    def teleport(self, src_container: str, dst_container: str, source: str = "QQC") -> Dict[str, Any]:
        """
        High-level teleport operation: extract → transfer → verify.
        """
        state = self.extract_state(src_container)
        if not state:
            return {"status": "error", "error": f"Source {src_container} missing"}

        result = self.transfer_state(state, dst_container)
        if result.get("status") == "ok":
            teleport_to_container(dst_container, source)
            logger.info(f"[WormholeManager] 🌀 Teleport successful: {src_container} → {dst_container}")
        return result