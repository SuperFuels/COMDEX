# File: backend/modules/glyphnet/time_locked_key_manager.py

import time
import threading
import logging
from typing import Optional, Dict, Callable

logger = logging.getLogger(__name__)


class TimeLockedKeyManager:
    def __init__(self, poll_interval: int = 10):
        """
        Manage keys that unlock or expire based on real-time or symbolic CodexLang conditions.

        Args:
            poll_interval: How often (seconds) the unlock monitor checks conditions.
        """
        # key_id -> record dict
        self._keys: Dict[str, Dict] = {}
        self.lock = threading.Lock()
        self.poll_interval = poll_interval

        # Background monitor thread
        self._monitor_thread = threading.Thread(target=self._monitor_unlocks, daemon=True)
        self._monitor_thread.start()

    # ───────────────────────────────────────────────
    # 🔑 Key Management
    # ───────────────────────────────────────────────
    def add_time_locked_key(
        self,
        key_id: str,
        key: bytes,
        unlock_time: Optional[float] = None,
        unlock_condition: Optional[Callable] = None,
        expiry_time: Optional[float] = None,
    ):
        """
        Add a key that will unlock at a specified Unix timestamp, when a symbolic condition is met,
        or both. Optionally expires after a given Unix timestamp.

        Args:
            key_id: Unique identifier for the key.
            key: The cryptographic key bytes.
            unlock_time: Unix timestamp when the key becomes unlocked (optional).
            unlock_condition: Callable with no args returning bool for symbolic unlock condition (optional).
            expiry_time: Unix timestamp when the key becomes invalid again (optional).
        """
        with self.lock:
            self._keys[key_id] = {
                "key": key,
                "unlock_time": unlock_time,
                "unlock_condition": unlock_condition,
                "expiry_time": expiry_time,
                "unlocked": False,
                "unlock_source": None,
                "unlocked_at": None,
            }
            logger.info(
                f"[TimeLockedKeyManager] Added key '{key_id}' "
                f"(unlock_time={unlock_time}, expiry_time={expiry_time})"
            )

    def get_key(self, key_id: str) -> Optional[bytes]:
        """
        Retrieve a key if it is unlocked and not expired.
        """
        with self.lock:
            record = self._keys.get(key_id)
            if record and record["unlocked"]:
                if record["expiry_time"] and time.time() >= record["expiry_time"]:
                    logger.warning(f"[TimeLockedKeyManager] Key '{key_id}' expired, removing.")
                    self.remove_key(key_id)
                    return None
                return record["key"]
            logger.warning(f"[TimeLockedKeyManager] Key '{key_id}' is locked or does not exist")
            return None

    def remove_key(self, key_id: str):
        """
        Remove a key entirely from the manager.
        """
        with self.lock:
            if key_id in self._keys:
                del self._keys[key_id]
                logger.info(f"[TimeLockedKeyManager] Removed key '{key_id}'")

    # ───────────────────────────────────────────────
    # 🎛️ Manual Control
    # ───────────────────────────────────────────────
    def unlock_key(self, key_id: str, source: str = "manual"):
        """
        Forcefully unlock a key, bypassing time/condition checks.
        """
        with self.lock:
            record = self._keys.get(key_id)
            if record:
                record["unlocked"] = True
                record["unlock_source"] = source
                record["unlocked_at"] = time.time()
                logger.info(f"[TimeLockedKeyManager] Key '{key_id}' manually unlocked (source={source})")

    def relock_key(self, key_id: str):
        """
        Re-lock a key after it has been unlocked.
        """
        with self.lock:
            record = self._keys.get(key_id)
            if record:
                record["unlocked"] = False
                record["unlock_source"] = None
                record["unlocked_at"] = None
                logger.info(f"[TimeLockedKeyManager] Key '{key_id}' re-locked")

    def list_keys(self) -> Dict[str, Dict]:
        """
        Return shallow copy of key metadata for inspection (keys excluded).
        """
        with self.lock:
            return {
                k: {kk: vv for kk, vv in v.items() if kk != "key"}
                for k, v in self._keys.items()
            }

    # ───────────────────────────────────────────────
    # ⏱️ Unlock Monitor
    # ───────────────────────────────────────────────
    def _monitor_unlocks(self):
        """
        Background thread loop that checks for unlock/expiry conditions.
        """
        while True:
            with self.lock:
                now = time.time()
                for key_id, record in list(self._keys.items()):
                    # Handle expiry
                    if record["unlocked"] and record["expiry_time"] and now >= record["expiry_time"]:
                        logger.info(f"[TimeLockedKeyManager] Key '{key_id}' expired, removing.")
                        del self._keys[key_id]
                        continue

                    # Handle unlock conditions
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
                            record["unlock_source"] = "time" if time_check else "condition"
                            record["unlocked_at"] = now
                            logger.info(f"[TimeLockedKeyManager] Key '{key_id}' unlocked via {record['unlock_source']}")
            time.sleep(self.poll_interval)


# ───────────────────────────────────────────────
# 🔗 Singleton
# ───────────────────────────────────────────────
_time_locked_key_manager: Optional[TimeLockedKeyManager] = None


def get_time_locked_key_manager() -> TimeLockedKeyManager:
    global _time_locked_key_manager
    if _time_locked_key_manager is None:
        _time_locked_key_manager = TimeLockedKeyManager()
    return _time_locked_key_manager