# backend/modules/glyphnet/qkd_policy.py

"""
GlyphNet QKD Policy Adapter
---------------------------
Thin wrapper around the existing Glyphwave QKD policy enforcer so that
glyph_transport_switch can call a simple enforce_qkd_policy(packet, gkey).

For now we ignore `gkey` and defer entirely to the wave-level policy.
Later we can thread session-level keys through if needed.
"""

from __future__ import annotations
from typing import Any, Dict, Optional
import logging

from backend.modules.glyphwave.qkd.glyphnet_qkd_policy import QKDPolicyEnforcer

logger = logging.getLogger(__name__)


class QKDPolicyError(Exception):
    """Raised when a packet violates QKD policy."""
    pass


# Single shared enforcer instance is fine
_enforcer = QKDPolicyEnforcer()


def enforce_qkd_policy(packet: Dict[str, Any], gkey: Optional[Any] = None) -> None:
    """
    Adapter used by glyph_transport_switch._dispatch_packet.

    - `packet` is the .gip packet (or wave_packet-like dict)
    - `gkey` is currently ignored; enforcement is based on the packet's own
      qkd_policy metadata and the Glyphwave GKeyStore.

    Raises:
        QKDPolicyError if policy says the packet must NOT be sent.
    """
    try:
        ok = _enforcer.enforce_policy(packet)
    except Exception as e:
        logger.error(f"[QKD] Enforcer threw exception: {e}", exc_info=True)
        # Be conservative: block on unexpected errors
        raise QKDPolicyError(f"QKD enforcement crashed: {e}") from e

    if not ok:
        logger.warning("[QKD] Policy violation – blocking packet")
        raise QKDPolicyError("QKD policy violation (missing or invalid GKey)")

    logger.debug("[QKD] Policy check passed")