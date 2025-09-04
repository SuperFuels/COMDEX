# File: backend/modules/glyphwave/qkd/qkd_crypto_handshake.py

import hashlib
from backend.modules.glyphwave.qkd.qkd_logger import log_qkd_event
from backend.modules.glyphwave.core.wave_state_store import store_wave_state
from backend.modules.glyphwave.qkd.decoherence_fingerprint import collapse_fingerprint_match
from backend.modules.glyphwave.qkd.gkey_model import GKey


def _generate_collapse_hash(wave_id: str, entropy: float, origin_trace: str) -> str:
    raw = f"{wave_id}|{entropy:.6f}|{origin_trace}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def initiate_qkd_handshake(sender_id: str, receiver_id: str, wave) -> bool:
    """
    Initiates a Quantum Key Distribution (QKD) handshake.

    - Verifies wave's collapse fingerprint.
    - Verifies GKey's collapse hash.
    - Logs the QKD event.
    - Stores the wave if verified.

    Returns:
        bool: True if QKD verified, False otherwise.
    """
    metadata = wave.metadata
    wave_id = metadata.get("wave_id")
    collapse_hash = metadata.get("collapse_hash")
    entropy = metadata.get("entropy")
    origin_trace = metadata.get("origin_trace", "")
    gkey_raw = metadata.get("gkey")

    # 1. Verify collapse fingerprint
    fingerprint_verified = collapse_fingerprint_match(wave)

    # 2. Verify GKey collapse hash
    gkey_verified = True  # assume OK if no GKey
    if gkey_raw:
        try:
            gkey = GKey(**gkey_raw) if isinstance(gkey_raw, dict) else gkey_raw
            expected_hash = _generate_collapse_hash(wave_id, entropy, origin_trace)
            gkey_verified = (expected_hash == gkey.collapse_hash)
            gkey.verified = gkey_verified
            gkey.compromised = not gkey_verified
        except Exception as e:
            gkey_verified = False

    # Final verdict
    verified = fingerprint_verified and gkey_verified

    # Log event
    await log_qkd_event(
        status="success" if verified else "tamper",
        wave_id=wave_id,
        sender_id=sender_id,
        receiver_id=receiver_id,
        collapse_hash=collapse_hash,
        entropy_level=entropy,
        reason=(
            "Verified fingerprint and GKey hash"
            if verified else
            "Fingerprint or GKey hash mismatch"
        ),
    )

    # Store valid wave
    if verified:
        store_wave_state(wave)

    return verified