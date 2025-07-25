import time
import threading
import logging
from typing import Optional, Dict, Callable

logger = logging.getLogger(__name__)

class TimeLockedKeyManager:
    def __init__(self):
        """
        Manage keys that unlock or expire based on real-time or symbolic CodexLang conditions.
        """
        self._keys: Dict[str, Dict] = {}  # key_id -> { 'key': bytes, 'unlock_time': float, 'unlock_condition': Callable, 'unlocked': bool }
        self.lock = threading.Lock()
        self._monitor_thread = threading.Thread(target=self._monitor_unlocks, daemon=True)
        self._monitor_thread.start()

    def add_time_locked_key(self, key_id: str, key: bytes, unlock_time: Optional[float] = None, unlock_condition: Optional[Callable] = None):
        """
        Add a key that will unlock at a specified Unix timestamp or when a symbolic condition returns True.

        Args:
            key_id: Unique identifier for the key.
            key: The cryptographic key bytes.
            unlock_time: Unix timestamp when the key becomes unlocked (optional).
            unlock_condition: Callable with no args returning bool for symbolic unlock condition (optional).
        """
        with self.lock:
            self._keys[key_id] = {
                "key": key,
                "unlock_time": unlock_time,
                "unlock_condition": unlock_condition,
                "unlocked": False
            }
            logger.info(f"[TimeLockedKeyManager] Added time-locked key '{key_id}' with unlock_time={unlock_time}")

    def get_key(self, key_id: str) -> Optional[bytes]:
        with self.lock:
            record = self._keys.get(key_id)
            if record and record["unlocked"]:
                return record["key"]
            else:
                logger.warning(f"[TimeLockedKeyManager] Key '{key_id}' is locked or does not exist")
                return None

    def _monitor_unlocks(self):
        while True:
            with self.lock:
                now = time.time()
                for key_id, record in self._keys.items():
                    if not record["unlocked"]:
                        time_check = record["unlock_time"] is not None and now >= record["unlock_time"]
                        condition_check = False
                        if record["unlock_condition"]:
                            try:
                                condition_check = record["unlock_condition"]()
                            except Exception as e:
                                logger.error(f"[TimeLockedKeyManager] Unlock condition error for '{key_id}': {e}")
                        if time_check or condition_check:
                            record["unlocked"] = True
                            logger.info(f"[TimeLockedKeyManager] Key '{key_id}' has been unlocked")
            time.sleep(10)

    def remove_key(self, key_id: str):
        with self.lock:
            if key_id in self._keys:
                del self._keys[key_id]
                logger.info(f"[TimeLockedKeyManager] Removed key '{key_id}'")

# Singleton instance
_time_locked_key_manager: Optional[TimeLockedKeyManager] = None

def get_time_locked_key_manager() -> TimeLockedKeyManager:
    global _time_locked_key_manager
    if _time_locked_key_manager is None:
        _time_locked_key_manager = TimeLockedKeyManager()
    return _time_locked_key_manager