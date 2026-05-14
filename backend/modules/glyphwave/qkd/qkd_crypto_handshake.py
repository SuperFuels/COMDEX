import hashlib
from backend.modules.glyphwave.qkd.qkd_logger import log_qkd_event
from backend.modules.glyphwave.core.wave_state_store import store_wave_state
from backend.modules.glyphwave.qkd.decoherence_fingerprint import DecoherenceFingerprint
from backend.modules.glyphwave.gkey_model import GKey


def _generate_collapse_hash(wave_id: str, entropy: float, origin_trace: str) -> str:
    """Generate a SHA256 collapse hash from wave metadata."""
    raw = f"{wave_id}|{entropy:.6f}|{origin_trace}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def initiate_qkd_handshake(sender_id: str, receiver_id: str, wave) -> bool:
    """
    Initiates a Quantum Key Distribution (QKD) handshake.

    Steps:
      1. Verify wave's decoherence fingerprint via DecoherenceFingerprint.
      2. Verify GKey's collapse hash.
      3. Log event outcome.
      4. Store wave state if verified.

    Returns:
        bool: True if handshake verified, False otherwise.
    """
    metadata = wave.metadata
    wave_id = metadata.get("wave_id")
    collapse_hash = metadata.get("collapse_hash")
    entropy = metadata.get("entropy", 0.0)
    origin_trace = metadata.get("origin_trace", {})
    gkey_raw = metadata.get("gkey")
    expected_fp = metadata.get("decoherence_fingerprint")

    # 1️⃣ Verify decoherence fingerprint
    fingerprint_verified = True
    try:
        if expected_fp:
            fingerprint_verified = DecoherenceFingerprint.verify_fingerprint(
                expected=expected_fp,
                trace=origin_trace,
                entropy=entropy,
                wave_id=wave_id,
            )
        else:
            fingerprint_verified = True  # Assume valid if legacy wave without fingerprint
    except Exception as e:
        print(f"[QKD] ⚠️ Decoherence fingerprint verification failed: {e}")
        fingerprint_verified = False

    # 2️⃣ Verify GKey collapse hash
    gkey_verified = True
    if gkey_raw:
        try:
            gkey = GKey(**gkey_raw) if isinstance(gkey_raw, dict) else gkey_raw
            expected_hash = _generate_collapse_hash(wave_id, entropy, str(origin_trace))
            gkey_verified = (expected_hash == gkey.collapse_hash)
            gkey.verified = gkey_verified
            gkey.compromised = not gkey_verified
        except Exception as e:
            print(f"[QKD] ⚠️ GKey verification error: {e}")
            gkey_verified = False

    # ✅ Final verification
    verified = fingerprint_verified and gkey_verified

    # 3️⃣ Log the QKD event
    log_qkd_event(
        sender_id=sender_id,
        receiver_id=receiver_id,
        wave_id=wave_id,
        status="success" if verified else "tamper",
        detail=(
            "Verified fingerprint and GKey hash"
            if verified else
            "Fingerprint or GKey hash mismatch"
        ),
        collapse_hash=collapse_hash,
    )

    # 4️⃣ Store valid wave
    if verified:
        store_wave_state(wave)

    return verified