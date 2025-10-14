import secrets
import hashlib
from typing import Optional

from backend.modules.utils import log_info, log_warn
from backend.modules.glyphwave.gkey_model import GKey


def _generate_collapse_hash(wave_id: str, entropy: float, origin_trace: str) -> str:
    raw = f"{wave_id}|{entropy:.6f}|{origin_trace}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def initiate_handshake(wave_id: str, origin_trace: str, entropy: float) -> GKey:
    coherence = round(secrets.SystemRandom().uniform(0.9, 1.0), 4)
    collapse_hash = _generate_collapse_hash(wave_id, entropy, origin_trace)

    gkey = GKey(
        wave_id=wave_id,
        entropy=entropy,
        coherence_level=coherence,
        collapse_hash=collapse_hash,
        origin_trace=origin_trace,
        verified=False,
    )

    log_info(f"🔐 [QKD] Initiated GKey | wave_id={wave_id} | entropy={entropy:.6f} | coherence={coherence}")
    return gkey


async def verify_handshake(received_gkey: GKey, observed_entropy: float, trace_signature: str) -> bool:
    expected_hash = _generate_collapse_hash(
        wave_id=received_gkey.wave_id,
        entropy=observed_entropy,
        origin_trace=trace_signature,
    )

    match = expected_hash == received_gkey.collapse_hash

    received_gkey.verified = match
    received_gkey.compromised = not match

    if match:
        log_info(f"✅ [QKD] GKey verified | wave_id={received_gkey.wave_id}")
    else:
        log_warn(
            f"❌ [QKD] GKey verification failed | wave_id={received_gkey.wave_id} | expected_hash={expected_hash} "
            f"| received_hash={received_gkey.collapse_hash}"
        )

    return match


async def renegotiate_gkey(old_key: GKey, current_entropy: float) -> GKey:
    return await initiate_handshake(
        wave_id=old_key.wave_id,
        origin_trace=old_key.origin_trace,
        entropy=current_entropy,
    )


# 🔐 In-memory store for active GKeys (can be replaced with Redis or DB in prod)
class GKeyStore:
    _store = {}         # Stores GKey by wave_id
    _key_pairs = {}     # Stores QKD pair status by (sender, recipient) tuple

    @classmethod
    def add(cls, gkey: GKey):
        cls._store[gkey.wave_id] = gkey
        log_info(f"[GKeyStore] Stored GKey for wave_id={gkey.wave_id}")

    @classmethod
    def get(cls, wave_id: str) -> Optional[GKey]:
        return cls._store.get(wave_id)

    @classmethod
    def delete(cls, wave_id: str):
        if wave_id in cls._store:
            del cls._store[wave_id]
            log_info(f"[GKeyStore] Deleted GKey for wave_id={wave_id}")

    @classmethod
    def reset(cls):
        cls._store.clear()
        cls._key_pairs.clear()
        log_info("[GKeyStore] Store and key pairs reset")

    # ✅ Set QKD pair record
    @classmethod
    def set_key_pair(cls, sender: str, recipient: str, key_data: dict):
        key = (sender, recipient)
        cls._key_pairs[key] = key_data
        log_info(f"[GKeyStore] Set QKD key pair ({sender} → {recipient})")

    # ✅ Get QKD pair record
    @classmethod
    def get_key_pair(cls, sender: str, recipient: str) -> Optional[dict]:
        return cls._key_pairs.get((sender, recipient))

    # ✅ NEW: Tamper detection via collapse_hash + decoherence_fingerprint
    @classmethod
    def detect_tampering(cls, sender: str, recipient: str) -> bool:
        """
        Returns True if tampering is detected via:
        - Missing keys
        - Mismatched collapse_hash
        - Mismatched decoherence_fingerprint (if present)
        """
        forward = cls.get_key_pair(sender, recipient)
        reverse = cls.get_key_pair(recipient, sender)

        if not forward or not reverse:
            return True

        if forward.get("status") != "verified" or reverse.get("status") != "verified":
            return True

        if forward.get("collapse_hash") != reverse.get("collapse_hash"):
            return True

        fp1 = forward.get("decoherence_fingerprint")
        fp2 = reverse.get("decoherence_fingerprint")
        if fp1 and fp2 and fp1 != fp2:
            return True

        return False  # ✅ Passed all checks
        
    @staticmethod
    def renegotiate(sender_id: str, recipient_id: str) -> dict:
        """
        Force QKD renegotiation and generate a new GKey for the given sender-recipient pair.
        """
        logger.info(f"[QKD] Renegotiating GKey between {sender_id} and {recipient_id}")
        new_key = GKeyStore.generate_pair(sender_id, recipient_id)
        GKeyStore.store_pair(sender_id, recipient_id, new_key)
        return new_key


# -------------------------------------------------------------------------
# QKDHandshake Adapter Class — for compatibility with QKDManager
# -------------------------------------------------------------------------
import secrets
import hashlib
import time

class QKDHandshake:
    """
    Adapter layer providing a consistent object interface for QKDManager.
    Wraps the functional handshake calls defined above.
    """

    def __init__(self):
        self._last_key = None
        self._last_timestamp = None

    async def perform_handshake(self, wave_id: str, origin_trace: str, entropy: float):
        """
        Perform a QKD handshake using the existing initiate_handshake() logic.
        Stores the resulting GKey and timestamp.
        """
        self._last_timestamp = time.time()
        gkey = await initiate_handshake(wave_id, origin_trace, entropy)
        self._last_key = gkey
        return gkey

    def generate_session_key(self) -> str:
        """
        Deterministic fallback session key generator.
        Used when the manager needs a local key immediately.
        """
        token = secrets.token_bytes(32)
        return hashlib.sha3_256(token).hexdigest()

    def get_last_key(self):
        """Return the most recently negotiated GKey (if available)."""
        return self._last_key

    def get_status(self) -> dict:
        """Return status metadata for monitoring or telemetry."""
        return {
            "active": self._last_key is not None,
            "timestamp": self._last_timestamp,
            "wave_id": getattr(self._last_key, "wave_id", None),
            "verified": getattr(self._last_key, "verified", False),
        }