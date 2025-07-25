import logging
import time
from typing import Dict, Optional

from backend.modules.glyphos.codexlang_translator import run_codexlang_string

logger = logging.getLogger(__name__)

class GlyphNetKeyLockManager:
    def __init__(self):
        # session_id → dict with keys: "lock_expr" (str), "created" (float), "ttl" (float or None)
        self._locks: Dict[str, Dict] = {}

    def register_lock(self, session_id: str, lock_expression: str, ttl_seconds: Optional[float] = None):
        """
        Register a symbolic lock expression on a session key.

        Args:
            session_id: ID of the session/key to lock.
            lock_expression: CodexLang expression to evaluate for unlock.
            ttl_seconds: Optional time-to-live after which the lock expires.
        """
        self._locks[session_id] = {
            "lock_expr": lock_expression,
            "created": time.time(),
            "ttl": ttl_seconds
        }
        logger.info(f"[GlyphNetKeyLockManager] Registered lock on session '{session_id}' with TTL={ttl_seconds}")

    def clear_lock(self, session_id: str):
        """
        Remove the lock on a session key.
        """
        if session_id in self._locks:
            del self._locks[session_id]
            logger.info(f"[GlyphNetKeyLockManager] Cleared lock on session '{session_id}'")

    def is_locked(self, session_id: str) -> bool:
        """
        Check if the session key is currently locked.

        Returns True if locked, False if no lock or expired.
        """
        lock_info = self._locks.get(session_id)
        if not lock_info:
            return False
        # Check TTL expiry
        if lock_info["ttl"] is not None:
            if time.time() > lock_info["created"] + lock_info["ttl"]:
                # Lock expired — auto-clear
                self.clear_lock(session_id)
                return False
        return True

    def can_unlock(self, session_id: str, context: Optional[dict] = None) -> bool:
        """
        Evaluate the lock expression in the given context to decide if key can be unlocked.

        Args:
            session_id: Session key ID.
            context: Symbolic context dict for CodexLang expression evaluation.

        Returns:
            True if unlock condition passes, False otherwise.
        """
        lock_info = self._locks.get(session_id)
        if not lock_info:
            return True  # No lock means no restriction

        expr = lock_info.get("lock_expr")
        if not expr:
            return True  # No expression means unlocked

        try:
            # Evaluate CodexLang expression with given context
            # run_codexlang_string returns a dict or symbolic result
            result = run_codexlang_string(expr)
            # Interpret result to boolean: assuming presence of 'success' key or truthy output
            if isinstance(result, dict):
                return result.get("success", bool(result))
            return bool(result)
        except Exception as e:
            logger.error(f"[GlyphNetKeyLockManager] Lock evaluation failed for session '{session_id}': {e}")
            return False

# Singleton instance
_key_lock_manager: Optional[GlyphNetKeyLockManager] = None

def get_key_lock_manager() -> GlyphNetKeyLockManager:
    global _key_lock_manager
    if _key_lock_manager is None:
        _key_lock_manager = GlyphNetKeyLockManager()
    return _key_lock_manager