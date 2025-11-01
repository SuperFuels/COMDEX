import time
import threading
import logging
from typing import Optional, Dict
from Crypto.Random import get_random_bytes
from backend.modules.encryption.session_key_vault import get_session_key_vault
from backend.modules.glyphnet.glyphnet_key_locks import get_key_lock_manager  # <-- imported lock manager

logger = logging.getLogger(__name__)

class EphemeralKeyManager:
    def __init__(self, key_ttl_seconds: int = 300):
        """
        Manage ephemeral keys with automatic expiration (Forward Secrecy).

        Args:
            key_ttl_seconds: Time-to-live for each ephemeral key in seconds (default 5 minutes).
        """
        self.key_ttl = key_ttl_seconds
        self._keys: Dict[str, Dict] = {}  # session_id -> {"key": bytes, "expiry": float}
        self.lock = threading.Lock()
        self._cleaner_thread = threading.Thread(target=self._clean_expired_keys, daemon=True)
        self._cleaner_thread.start()
        self.vault = get_session_key_vault()
        self.lock_manager = get_key_lock_manager()  # <-- instantiate lock manager

    def generate_key(self, session_id: str,
                     trust_level: float = 0.5,
                     emotion_level: float = 0.5,
                     seed_phrase: Optional[str] = None) -> bytes:
        """
        Generate a new ephemeral AES-256 key for the given session ID using symbolic key derivation.
        Stores in-memory and in vault.

        Args:
            session_id: The unique session identifier.
            trust_level: Semantic trust parameter (0.0 - 1.0).
            emotion_level: Semantic emotion parameter (0.0 - 1.0).
            seed_phrase: Optional entropy seed phrase.

        Returns:
            The derived key bytes.
        """
        # Import here to avoid circular import
        from backend.modules.glyphnet.symbolic_key_derivation import symbolic_key_deriver

        with self.lock:
            timestamp = time.time()
            derived_key = symbolic_key_deriver.derive_key(trust_level, emotion_level, timestamp, identity=session_id, seed_phrase=seed_phrase)
            if derived_key is None:
                # fallback to random if symbolic derivation failed
                logger.warning(f"[EphemeralKeyManager] Symbolic derivation failed for {session_id}, generating random key")
                derived_key = get_random_bytes(32)
            expiry = timestamp + self.key_ttl
            self._keys[session_id] = {"key": derived_key, "expiry": expiry}
            self.vault.store_key(session_id, derived_key)
            logger.info(f"[EphemeralKeyManager] Generated ephemeral symbolic key for session {session_id} (expires in {self.key_ttl}s)")
            return derived_key

    def get_key(self, session_id: str, context: Optional[dict] = None) -> Optional[bytes]:
        """
        Retrieve the ephemeral key if valid, not expired, and unlocked.

        Args:
            session_id: The session ID of the key.
            context: Optional context dict for symbolic lock evaluation.

        Returns:
            The key bytes if accessible, else None.
        """
        with self.lock:
            # Check symbolic lock before returning key
            if self.lock_manager.is_locked(session_id):
                can_unlock = self.lock_manager.can_unlock(session_id, context=context)
                if not can_unlock:
                    logger.warning(f"[EphemeralKeyManager] Access denied by lock for session {session_id}")
                    return None
                else:
                    # Lock condition passed - clear the lock
                    self.lock_manager.clear_lock(session_id)
                    logger.info(f"[EphemeralKeyManager] Lock cleared for session {session_id} after successful unlock")

            record = self._keys.get(session_id)
            if record and record["expiry"] > time.time():
                return record["key"]
            else:
                logger.warning(f"[EphemeralKeyManager] Ephemeral key for session {session_id} expired or not found")
                # Clean up expired key if present
                if session_id in self._keys:
                    del self._keys[session_id]
                self.vault.delete_key(session_id)
                return None

    def revoke_key(self, session_id: str):
        """
        Manually revoke and delete an ephemeral key.
        """
        with self.lock:
            if session_id in self._keys:
                del self._keys[session_id]
                logger.info(f"[EphemeralKeyManager] Revoked ephemeral key for session {session_id}")
            self.vault.delete_key(session_id)

    def _clean_expired_keys(self):
        while True:
            with self.lock:
                now = time.time()
                expired_sessions = [sid for sid, rec in self._keys.items() if rec["expiry"] <= now]
                for sid in expired_sessions:
                    del self._keys[sid]
                    self.vault.delete_key(sid)
                    logger.info(f"[EphemeralKeyManager] Auto-cleaned expired ephemeral key for session {sid}")
            time.sleep(30)

# Singleton instance
_ephemeral_key_manager: Optional[EphemeralKeyManager] = None

def get_ephemeral_key_manager() -> EphemeralKeyManager:
    global _ephemeral_key_manager
    if _ephemeral_key_manager is None:
        _ephemeral_key_manager = EphemeralKeyManager()
    return _ephemeral_key_manager