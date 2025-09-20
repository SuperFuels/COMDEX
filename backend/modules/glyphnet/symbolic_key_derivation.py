# File: backend/modules/glyphnet/symbolic_key_derivation.py

import logging
import hashlib
import time
import secrets
import threading
import os
from datetime import datetime
from typing import Optional, Dict

from backend.modules.hexcore.memory_engine import get_runtime_entropy_snapshot

logger = logging.getLogger(__name__)


class SymbolicKeyDerivation:
    """
    SymbolicKeyDerivation manages the secure derivation of cryptographic keys
    from symbolic inputs combined with runtime entropy and security parameters.

    Features:
    - Combines trust level, emotion level, timestamp, and optional seed phrase
      into an entropy source for key derivation.
    - Uses a codex adapter (or dummy fallback) to symbolically evaluate key input.
    - Applies key stretching for cryptographic hardness.
    - Supports brute-force attempt tracking, lockouts, and thread-safe counters.
    - Allows disabling of salts and runtime entropy for deterministic testing.

    Attributes:
        MAX_ATTEMPTS (int): Maximum allowed failed attempts before lockout.
        lockout_time (int): Duration in seconds of lockout period after max attempts.
    """

    MAX_ATTEMPTS: int = 10
    DEFAULT_ITERATIONS: int = int(os.getenv("SKD_ITERATIONS", "10000"))

    def __init__(self, hash_algo: str = "sha256"):
        """
        Initializes the SymbolicKeyDerivation instance, setting up internal
        state for attempt tracking, lockouts, and thread safety.
        """
        self._codex_adapter = None
        self.brute_force_attempts: Dict[str, int] = {}
        self.lockout_time = 300  # seconds
        self.lockouts: Dict[str, float] = {}
        self._lock = threading.Lock()
        self.hash_algo = hash_algo

    # ───────────────────────────────────────────────
    # Codex Adapter
    # ───────────────────────────────────────────────
    def _get_codex_adapter(self):
        if self._codex_adapter is None:
            class DummyAdapter:
                def evaluate(self, input_str: str) -> str:
                    return hashlib.sha256(input_str.encode("utf-8")).hexdigest()
            self._codex_adapter = DummyAdapter()
        return self._codex_adapter

    # ───────────────────────────────────────────────
    # Lockout Handling
    # ───────────────────────────────────────────────
    def _is_locked_out(self, identity: str) -> bool:
        with self._lock:
            expiry = self.lockouts.get(identity, 0)
            now = time.time()
            if now < expiry:
                logger.warning(
                    f"[SymbolicKeyDerivation] Identity {identity} locked out until "
                    f"{datetime.fromtimestamp(expiry).isoformat()} (now={datetime.fromtimestamp(now).isoformat()})"
                )
                return True
            elif identity in self.lockouts:
                # Clear expired lockout
                del self.lockouts[identity]
                self.brute_force_attempts[identity] = 0
            return False

    def _record_failed_attempt(self, identity: str):
        with self._lock:
            attempts = self.brute_force_attempts.get(identity, 0) + 1
            self.brute_force_attempts[identity] = attempts
            if attempts >= self.MAX_ATTEMPTS:
                self.lockouts[identity] = time.time() + self.lockout_time
                logger.warning(f"[SymbolicKeyDerivation] 🚫 Lockout for {identity} after {attempts} failed attempts")

    def _clear_attempts(self, identity: str):
        with self._lock:
            if identity in self.brute_force_attempts:
                logger.debug(f"[SymbolicKeyDerivation] Cleared failed attempts for {identity}")
            self.brute_force_attempts.pop(identity, None)
            self.lockouts.pop(identity, None)

    # ───────────────────────────────────────────────
    # Entropy + Salt
    # ───────────────────────────────────────────────
    def _get_entropy(self, fixed_entropy: Optional[str] = None) -> str:
        if fixed_entropy is not None:
            return fixed_entropy
        try:
            return get_runtime_entropy_snapshot()
        except Exception as e:
            logger.error(f"[SymbolicKeyDerivation] Entropy retrieval failed: {e}")
            return ""

    def _gather_entropy(self, trust_level: float, emotion_level: float, timestamp: float, fixed_entropy: Optional[str]) -> str:
        entropy_part = self._get_entropy(fixed_entropy)
        return f"Trust:{trust_level};Emotion:{emotion_level};Time:{timestamp};Entropy:{entropy_part}"

    def _add_salt_nonce(self, base_material: bytes) -> bytes:
        salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(12)
        combined = salt + nonce + base_material
        logger.debug("[SymbolicKeyDerivation] Added salt and nonce for key material")
        return combined

    # ───────────────────────────────────────────────
    # Key Stretching
    # ───────────────────────────────────────────────
    def _key_stretch(self, input_bytes: bytes, iterations: Optional[int] = None) -> bytes:
        iterations = iterations or self.DEFAULT_ITERATIONS
        stretched = input_bytes
        hash_func = getattr(hashlib, self.hash_algo, hashlib.sha256)

        for _ in range(iterations):
            stretched = hash_func(stretched).digest()

        logger.debug(f"[SymbolicKeyDerivation] Performed key stretching ({iterations} iterations, algo={self.hash_algo})")
        return stretched

    # ───────────────────────────────────────────────
    # Public API
    # ───────────────────────────────────────────────
    def derive_key(
        self,
        trust_level: float,
        emotion_level: float,
        timestamp: float,
        identity: Optional[str] = None,
        seed_phrase: Optional[str] = None,
        use_salt: bool = True,
        fixed_entropy: Optional[str] = None,
        iterations: Optional[int] = None,
    ) -> Optional[bytes]:
        """
        Derives a secure cryptographic key based on input parameters combined with
        runtime entropy and optional seed phrase.
        """
        try:
            trust_level = float(trust_level)
            emotion_level = float(emotion_level)
            timestamp = float(timestamp)
        except (TypeError, ValueError):
            logger.error("[SymbolicKeyDerivation] Input validation failed: trust_level, emotion_level, and timestamp must be numeric")
            if identity:
                self._record_failed_attempt(identity)
            return None

        if identity is not None and not isinstance(identity, str):
            logger.error("[SymbolicKeyDerivation] Input validation failed: identity must be a string if provided")
            if identity:
                self._record_failed_attempt(identity)
            return None

        if seed_phrase is not None and not isinstance(seed_phrase, str):
            logger.error("[SymbolicKeyDerivation] Input validation failed: seed_phrase must be a string if provided")
            if identity:
                self._record_failed_attempt(identity)
            return None

        if identity and self._is_locked_out(identity):
            logger.error(f"[SymbolicKeyDerivation] Derivation blocked due to lockout for identity {identity}")
            return None

        try:
            base_input = self._gather_entropy(trust_level, emotion_level, timestamp, fixed_entropy)
            if seed_phrase:
                base_input += f";Seed:{seed_phrase}"

            codex_adapter = self._get_codex_adapter()
            symbolic_output = codex_adapter.evaluate(f"⟦ Key : {base_input} ⟧")
            base_material = symbolic_output.encode("utf-8")

            salted_material = self._add_salt_nonce(base_material) if use_salt else base_material
            derived_key = self._key_stretch(salted_material, iterations)

            if identity:
                self._clear_attempts(identity)

            logger.info(
                f"[SymbolicKeyDerivation] ✅ Derived secure key for {identity or 'anon'} "
                f"(time={datetime.fromtimestamp(timestamp).isoformat()})"
            )
            return derived_key
        except Exception as e:
            logger.error(f"[SymbolicKeyDerivation] Key derivation failed: {e}")
            if identity:
                self._record_failed_attempt(identity)
            return None

    def verify_key(
        self,
        key: bytes,
        trust_level: float,
        emotion_level: float,
        timestamp: float,
        identity: Optional[str] = None,
        seed_phrase: Optional[str] = None,
    ) -> bool:
        """
        Verifies whether the provided key matches the derived key for the given parameters.
        """
        derived = self.derive_key(trust_level, emotion_level, timestamp, identity, seed_phrase)
        if derived is None:
            return False
        return secrets.compare_digest(derived, key)


# ✅ Alias for backward compatibility
symbolic_key_deriver = SymbolicKeyDerivation()