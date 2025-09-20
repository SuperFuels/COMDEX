# backend/modules/glyphnet/glyphnet_key_locks.py

import logging
import time
from typing import Dict, Optional, Any

from backend.modules.glyphos.codexlang_translator import run_codexlang_string

logger = logging.getLogger(__name__)


class GlyphNetKeyLockManager:
    """
    Symbolic lock manager for session keys.
    Uses CodexLang expressions as symbolic "locks" that must evaluate true before unlocking.
    """

    def __init__(self) -> None:
        # session_id → dict with: "lock_expr" (CodexLang str), "created" (float), "ttl" (float or None)
        self._locks: Dict[str, Dict[str, Any]] = {}

    def register_lock(self, session_id: str, lock_expression: str, ttl_seconds: Optional[float] = None) -> None:
        """
        Register a symbolic lock expression on a session key.
        """
        self._locks[session_id] = {
            "lock_expr": lock_expression,
            "created": time.time(),
            "ttl": ttl_seconds,
        }
        logger.info(
            f"[GlyphNetKeyLockManager] Registered lock on session='{session_id}' "
            f"expr='{lock_expression}' ttl={ttl_seconds}"
        )

    def clear_lock(self, session_id: str) -> None:
        """Remove the lock on a session key."""
        if session_id in self._locks:
            del self._locks[session_id]
            logger.info(f"[GlyphNetKeyLockManager] Cleared lock on session '{session_id}'")

    def is_locked(self, session_id: str) -> bool:
        """
        Check if the session key is currently locked.

        Returns:
            True if locked, False if no lock or expired.
        """
        lock_info = self._locks.get(session_id)
        if not lock_info:
            return False

        ttl = lock_info.get("ttl")
        if ttl is not None and time.time() > lock_info["created"] + ttl:
            self.clear_lock(session_id)
            logger.info(f"[GlyphNetKeyLockManager] Lock expired for session '{session_id}'")
            return False

        return True

    def can_unlock(self, session_id: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Evaluate the lock expression in the given context to decide if key can be unlocked.
        """
        lock_info = self._locks.get(session_id)
        if not lock_info:
            return True

        expr = lock_info.get("lock_expr")
        if not expr:
            return True

        try:
            result = run_codexlang_string(expr)

            # Normalize CodexLang result → boolean
            passed = False
            if isinstance(result, dict):
                passed = result.get("success", bool(result))
            elif isinstance(result, bool):
                passed = result
            elif isinstance(result, str):
                passed = result.strip().lower() in {"true", "yes", "1"}
            else:
                passed = bool(result)

            logger.debug(
                f"[GlyphNetKeyLockManager] Lock evaluation for session='{session_id}' expr='{expr}' result={passed}"
            )
            return passed

        except Exception as e:
            logger.error(
                f"[GlyphNetKeyLockManager] Lock evaluation failed for session='{session_id}' "
                f"expr='{expr}' error={e}"
            )
            return False

    def get_lock_status(self, session_id: str) -> Dict[str, Any]:
        """
        Return current lock status for debugging/telemetry.

        Returns dict with:
            - locked: bool
            - expr: CodexLang expression or None
            - ttl_remaining: seconds remaining, or None if no TTL
        """
        lock_info = self._locks.get(session_id)
        if not lock_info:
            return {"locked": False, "expr": None, "ttl_remaining": None}

        ttl_remaining = None
        if lock_info.get("ttl") is not None:
            expiry = lock_info["created"] + lock_info["ttl"]
            ttl_remaining = max(0, expiry - time.time())

        return {
            "locked": self.is_locked(session_id),
            "expr": lock_info.get("lock_expr"),
            "ttl_remaining": ttl_remaining,
        }


# Singleton instance
_key_lock_manager: Optional[GlyphNetKeyLockManager] = None


def get_key_lock_manager() -> GlyphNetKeyLockManager:
    global _key_lock_manager
    if _key_lock_manager is None:
        _key_lock_manager = GlyphNetKeyLockManager()
    return _key_lock_manager