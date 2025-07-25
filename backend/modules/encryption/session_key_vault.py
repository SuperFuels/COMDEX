import threading
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class SessionKeyVault:
    def __init__(self):
        self._vault_lock = threading.Lock()
        self._keys: Dict[str, bytes] = {}

    def store_key(self, session_id: str, key: bytes):
        with self._vault_lock:
            self._keys[session_id] = key
            logger.info(f"[SessionKeyVault] Stored key for session {session_id}")

    def retrieve_key(self, session_id: str) -> Optional[bytes]:
        with self._vault_lock:
            key = self._keys.get(session_id)
            if key:
                logger.info(f"[SessionKeyVault] Retrieved key for session {session_id}")
            else:
                logger.warning(f"[SessionKeyVault] No key found for session {session_id}")
            return key

    def delete_key(self, session_id: str):
        with self._vault_lock:
            if session_id in self._keys:
                del self._keys[session_id]
                logger.info(f"[SessionKeyVault] Deleted key for session {session_id}")

    def clear_all_keys(self):
        with self._vault_lock:
            self._keys.clear()
            logger.info("[SessionKeyVault] Cleared all session keys")

    def list_all_keys(self) -> Dict[str, bytes]:
        """
        Return a copy of all stored session keys.
        """
        with self._vault_lock:
            return dict(self._keys)

# Singleton instance
_session_key_vault: Optional[SessionKeyVault] = None

def get_session_key_vault() -> SessionKeyVault:
    global _session_key_vault
    if _session_key_vault is None:
        _session_key_vault = SessionKeyVault()
    return _session_key_vault