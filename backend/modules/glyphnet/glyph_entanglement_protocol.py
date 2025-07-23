# backend/modules/glyphnet/glyph_entanglement_protocol.py

import time
import logging
from typing import Dict, Any, Optional

from backend.modules.glyphos.symbolic_entangler import entangle_glyphs
from backend.modules.hexcore.memory_engine import get_memory_by_keys, merge_memory_patch
from backend.modules.glyphnet.glyph_signal_reconstructor import reconstruct_gip_signal
from backend.modules.glyphnet.glyphnet_packet import push_symbolic_packet

logger = logging.getLogger(__name__)


def establish_entangled_link(source_id: str, target_id: str, keys: Optional[list] = None) -> Dict[str, Any]:
    """
    Establishes symbolic ↔ entanglement between two remote nodes.
    Optionally syncs memory keys or logic fragments.
    """
    if not source_id or not target_id:
        return {"status": "error", "message": "Missing source or target"}

    try:
        link = entangle_glyphs(source_id, target_id)

        shared_data = {}
        if keys:
            memory_patch = get_memory_by_keys(keys)
            shared_data["memory"] = memory_patch
            logger.info(f"[Entangle] Sharing memory keys: {keys}")

        packet = {
            "type": "entanglement_link",
            "source": source_id,
            "target": target_id,
            "timestamp": time.time(),
            "link": link,
            "shared": shared_data
        }

        push_symbolic_packet(packet)
        logger.info(f"[Entangle] ↔ Link sent between {source_id} and {target_id}")

        return {"status": "ok", "link": link, "shared": shared_data}

    except Exception as e:
        logger.exception("[Entangle] Failed to establish link")
        return {"status": "error", "message": str(e)}


def receive_entangled_signal(packet: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handles incoming entangled packet: apply memory sync or trigger replay.
    """
    try:
        source = packet.get("source")
        shared = packet.get("shared", {})
        link = packet.get("link", {})

        if "memory" in shared:
            merge_memory_patch(shared["memory"])
            logger.info(f"[Entangle] Merged memory from {source}")

        return {"status": "ok", "link": link, "source": source}

    except Exception as e:
        logger.exception("[Entangle] Receive failed")
        return {"status": "error", "message": str(e)}


def recover_entangled_state(fragment: str) -> Dict[str, Any]:
    """
    Attempts to rebuild logic from a broken entangled state using reconstructor.
    """
    try:
        return reconstruct_gip_signal({"payload": fragment, "sender": "↔_recovery"})
    except Exception as e:
        return {"status": "error", "message": str(e)}