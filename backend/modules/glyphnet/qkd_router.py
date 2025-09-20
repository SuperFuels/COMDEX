# ✅ Q1c: QKD Policy Enforcement in GlyphNet Router

import logging
from backend.modules.qkd.qkd_handshake import verify_handshake, renegotiate_gkey
from backend.modules.qkd.qkey_model import GKey
from backend.modules.glyphnet.qkd_fingerprint import verify_wave_state_integrity, FingerprintMismatchError

logger = logging.getLogger(__name__)


class QKDPolicyError(Exception):
    """Raised when QKD enforcement fails."""


# ───────────────────────────────────────────────
# 🔒 QKD Policy Enforcement
# ───────────────────────────────────────────────
def enforce_qkd_policy(packet: dict, gkey: GKey) -> bool:
    """
    Enforces QKD requirements for a given GlyphNet packet.
    If the packet is marked as requiring QKD, both the GKey handshake
    and wave state integrity checks (fingerprint + collapse hash)
    must succeed.

    Modes:
        - qkd_required=False → bypass (no enforcement).
        - qkd_required=True  → must verify GKey + integrity.
        - qkd_required="strict" → must verify GKey + integrity, else renegotiate.

    Returns:
        bool: True if the packet passes QKD policy.

    Raises:
        QKDPolicyError: If QKD enforcement fails.
    """
    metadata = packet.get("metadata", {})
    qkd_required = metadata.get("qkd_required", False)

    if not qkd_required:
        return True  # No QKD policy required

    if gkey is None:
        raise QKDPolicyError("Missing GKey for QKD-required packet.")

    # 🔐 First: verify GKey handshake
    if not verify_handshake(gkey):
        logger.warning(
            "❌ QKD handshake failed for wave_id=%s packet_id=%s",
            getattr(gkey, "wave_id", "unknown"),
            packet.get("id"),
        )
        gkey.verified = False
        gkey.compromised = True

        # Strict mode → attempt renegotiation
        if qkd_required == "strict":
            try:
                renegotiate_gkey(gkey)
                logger.info("🔑 QKD re-negotiation triggered for wave_id=%s", gkey.wave_id)
                if verify_handshake(gkey):
                    logger.info("🔑 Handshake succeeded after renegotiation.")
                else:
                    raise QKDPolicyError("Handshake failed after renegotiation.")
            except Exception as reneg_err:
                logger.error("❌ QKD renegotiation failed: %s", reneg_err)
                raise QKDPolicyError("GKey verification failed – renegotiation unsuccessful.")

        else:
            raise QKDPolicyError("GKey verification failed – possible tamper or decoherence.")

    # 🔎 Second: verify wave state integrity (fingerprint + collapse hash)
    try:
        verify_wave_state_integrity(
            wave_state=packet.get("payload", {}),
            expected_fingerprint=metadata.get("fingerprint"),
            expected_collapse_hash=metadata.get("collapse_hash"),
        )
    except FingerprintMismatchError as e:
        logger.error("❌ Integrity check failed for packet_id=%s: %s", packet.get("id"), str(e))
        raise QKDPolicyError(f"Wave state integrity check failed: {e}")

    logger.info("✅ QKD passed for wave_id=%s packet_id=%s", gkey.wave_id, packet.get("id"))
    gkey.verified = True
    return True


# ───────────────────────────────────────────────
# 📡 Routing Layer
# ───────────────────────────────────────────────
def route_packet(packet: dict, gkey: GKey) -> bool:
    """
    Main GlyphNet router interface.
    Applies QKD policy enforcement before allowing packet routing.

    Args:
        packet: The GlyphNet packet dict.
        gkey: Associated QKD session key.

    Returns:
        bool: True if routing allowed, False otherwise.
    """
    try:
        if enforce_qkd_policy(packet, gkey):
            logger.info("📡 ✅ Routing packet %s", packet.get("id"))
            # TODO: Plug in actual transmission logic
            return True
    except QKDPolicyError as e:
        logger.error("📡 ❌ Routing blocked: %s", str(e))
        # TODO: Optional → quarantine or alternate route
        return False

    return False