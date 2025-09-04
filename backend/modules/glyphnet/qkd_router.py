# ✅ Q1c: QKD Policy Enforcement in GlyphNet Router

import logging
from backend.modules.qkd.qkd_handshake import verify_handshake, renegotiate_gkey
from backend.modules.qkd.qkey_model import GKey

logger = logging.getLogger(__name__)

class QKDPolicyError(Exception):
    pass

def enforce_qkd_policy(packet: dict, gkey: GKey) -> bool:
    """
    Enforces QKD requirements for a given GlyphNet packet.
    If the packet is marked as requiring QKD, the presence and
    validity of the GKey is enforced.

    Returns True if the packet passes QKD policy.
    Raises QKDPolicyError if it fails.
    """
    metadata = packet.get("metadata", {})
    qkd_required = metadata.get("qkd_required", False)

    if not qkd_required:
        return True  # No QKD policy for this message

    if gkey is None:
        raise QKDPolicyError("Missing GKey for QKD-required packet.")

    if not verify_handshake(gkey):
        logger.warning("❌ QKD verification failed for wave_id=%s", gkey.wave_id)
        gkey.verified = False
        gkey.compromised = True
        raise QKDPolicyError("GKey verification failed – possible tamper or decoherence.")

    logger.info("✅ QKD passed for wave_id=%s", gkey.wave_id)
    return True

def route_packet(packet: dict, gkey: GKey) -> bool:
    """
    Main GlyphNet router interface.
    Applies QKD policy enforcement before allowing packet routing.
    """
    try:
        if enforce_qkd_policy(packet, gkey):
            logger.info("📡 Routing packet: %s", packet.get("id"))
            # Actual transmission logic would be here
            return True
    except QKDPolicyError as e:
        logger.error("Routing blocked: %s", str(e))
        # Optional: quarantine or mutate route
        return False

    return False