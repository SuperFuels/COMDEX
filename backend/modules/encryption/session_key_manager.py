import time
import threading
import logging
from typing import Optional
from Crypto.Random import get_random_bytes
from backend.modules.glyphnet.session_key_vault import get_session_key_vault

logger = logging.getLogger(__name__)

class SessionKeyManager:
    def __init__(self, rotation_interval_seconds: int = 3600):
        """
        Manage session keys with automatic rotation.

        Args:
            rotation_interval_seconds: How often to rotate keys (default 1 hour).
        """
        self.rotation_interval = rotation_interval_seconds
        self.current_key = self._generate_new_key()
        self.last_rotation = time.time()
        self.lock = threading.Lock()
        self._rotation_thread = threading.Thread(target=self._rotation_loop, daemon=True)
        self._rotation_thread.start()

        self.vault = get_session_key_vault()
        # Store initial key with a default session ID
        self.vault.store_key("current_session", self.current_key)

    def _generate_new_key(self) -> bytes:
        key = get_random_bytes(32)  # AES-256 key size
        logger.info("[SessionKeyManager] Generated new session key")
        return key

    def get_current_key(self) -> bytes:
        with self.lock:
            return self.current_key

    def _rotation_loop(self):
        while True:
            time_since = time.time() - self.last_rotation
            if time_since >= self.rotation_interval:
                with self.lock:
                    self.current_key = self._generate_new_key()
                    self.last_rotation = time.time()
                    logger.info("[SessionKeyManager] Session key rotated")
                    # Store rotated key in vault with timestamped session ID
                    session_id = f"session_{int(self.last_rotation)}"
                    self.vault.store_key(session_id, self.current_key)
                    # Update "current_session" pointer
                    self.vault.store_key("current_session", self.current_key)
            time.sleep(10)

    def manual_rotate(self):
        with self.lock:
            self.current_key = self._generate_new_key()
            self.last_rotation = time.time()
            logger.info("[SessionKeyManager] Session key manually rotated")
            # Store manual rotated key in vault
            session_id = f"session_{int(self.last_rotation)}"
            self.vault.store_key(session_id, self.current_key)
            self.vault.store_key("current_session", self.current_key)

# Singleton instance
_session_manager: Optional[SessionKeyManager] = None

def get_session_key_manager() -> SessionKeyManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionKeyManager()
    return _session_manager