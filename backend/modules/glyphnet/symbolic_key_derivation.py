import logging
import hashlib
import time
import secrets
from typing import Optional, Dict
import threading

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

    MAX_ATTEMPTS = 10

    def __init__(self):
        """
        Initializes the SymbolicKeyDerivation instance, setting up internal
        state for attempt tracking, lockouts, and thread safety.
        """
        self._codex_adapter = None
        self.brute_force_attempts: Dict[str, int] = {}
        self.lockout_time = 300  # seconds
        self.lockouts: Dict[str, float] = {}
        self._lock = threading.Lock()

    def _get_codex_adapter(self):
        """
        Lazily initialize and return the codex adapter used to symbolically
        evaluate key inputs. If no adapter is configured, returns a dummy
        adapter that hashes the input with SHA-256.

        Returns:
            An adapter instance with an evaluate(str) -> str method.
        """
        if self._codex_adapter is None:
            class DummyAdapter:
                def evaluate(self, input_str):
                    return hashlib.sha256(input_str.encode('utf-8')).hexdigest()
            self._codex_adapter = DummyAdapter()
        return self._codex_adapter

    def _is_locked_out(self, identity: str) -> bool:
        """
        Checks if a given identity (e.g., session or user) is currently locked out
        due to excessive failed attempts. Automatically clears expired lockouts.

        Args:
            identity (str): The identifier to check for lockout status.

        Returns:
            bool: True if locked out, False otherwise.
        """
        with self._lock:
            expiry = self.lockouts.get(identity, 0)
            now = time.time()
            if now < expiry:
                logger.warning(f"[SymbolicKeyDerivation] Identity {identity} locked out until {expiry} (now={now})")
                return True
            elif identity in self.lockouts:
                # Clear expired lockout
                del self.lockouts[identity]
                self.brute_force_attempts[identity] = 0
            return False

    def _record_failed_attempt(self, identity: str):
        """
        Records a failed key derivation or verification attempt for the given identity.
        Triggers a lockout if the maximum allowed attempts is exceeded.

        Args:
            identity (str): The identifier for which to record the failed attempt.
        """
        with self._lock:
            attempts = self.brute_force_attempts.get(identity, 0) + 1
            self.brute_force_attempts[identity] = attempts
            if attempts >= self.MAX_ATTEMPTS:
                self.lockouts[identity] = time.time() + self.lockout_time
                logger.warning(f"[SymbolicKeyDerivation] Identity {identity} locked out due to {attempts} failed attempts")

    def _clear_attempts(self, identity: str):
        """
        Clears all failed attempt counters and lockout state for the given identity.

        Args:
            identity (str): The identifier for which to clear attempts and lockouts.
        """
        with self._lock:
            self.brute_force_attempts.pop(identity, None)
            self.lockouts.pop(identity, None)

    def _get_entropy(self, fixed_entropy: Optional[str] = None) -> str:
        """
        Retrieves runtime entropy as a string for use in key derivation.
        If fixed_entropy is provided, it is returned directly (useful for testing).

        Args:
            fixed_entropy (Optional[str]): Optional fixed entropy to use.

        Returns:
            str: Entropy string.
        """
        if fixed_entropy is not None:
            return fixed_entropy
        try:
            return get_runtime_entropy_snapshot()
        except Exception as e:
            logger.error(f"[SymbolicKeyDerivation] Entropy retrieval failed: {e}")
            return ""

    def _gather_entropy(self, trust_level: float, emotion_level: float, timestamp: float, fixed_entropy: Optional[str]) -> str:
        """
        Combines input parameters and runtime entropy into a single entropy seed string.

        Args:
            trust_level (float): Trust level parameter.
            emotion_level (float): Emotion level parameter.
            timestamp (float): Timestamp parameter.
            fixed_entropy (Optional[str]): Optional fixed entropy override.

        Returns:
            str: Combined entropy seed.
        """
        entropy_part = self._get_entropy(fixed_entropy)
        seed = f"Trust:{trust_level};Emotion:{emotion_level};Time:{timestamp};Entropy:{entropy_part}"
        return seed

    def _add_salt_nonce(self, base_material: bytes) -> bytes:
        """
        Adds cryptographic salt and nonce bytes to the base material to enhance
        key uniqueness and randomness.

        Args:
            base_material (bytes): Base key material.

        Returns:
            bytes: Key material with added salt and nonce.
        """
        salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(12)
        combined = salt + nonce + base_material
        logger.debug("[SymbolicKeyDerivation] Added salt and nonce for key material")
        return combined

    def _key_stretch(self, input_bytes: bytes, iterations: int = 10000) -> bytes:
        """
        Performs repeated hashing (key stretching) on the input bytes to increase
        computational hardness against brute force.

        Args:
            input_bytes (bytes): Input bytes to stretch.
            iterations (int): Number of SHA-256 iterations.

        Returns:
            bytes: Stretched key bytes.
        """
        stretched = input_bytes
        for _ in range(iterations):
            stretched = hashlib.sha256(stretched).digest()
        logger.debug(f"[SymbolicKeyDerivation] Performed key stretching with {iterations} iterations")
        return stretched

    def derive_key(self, trust_level: float, emotion_level: float, timestamp: float,
                   identity: Optional[str] = None, seed_phrase: Optional[str] = None,
                   use_salt: bool = True, fixed_entropy: Optional[str] = None) -> Optional[bytes]:
        """
        Derives a secure cryptographic key based on input parameters combined with
        runtime entropy and optional seed phrase.

        Args:
            trust_level (float): Trust level, numeric.
            emotion_level (float): Emotion level, numeric.
            timestamp (float): Timestamp, numeric (e.g., epoch seconds).
            identity (Optional[str]): Identity string for rate limiting and lockout.
            seed_phrase (Optional[str]): Optional seed phrase to influence key derivation.
            use_salt (bool): Whether to apply salt and nonce (default True).
            fixed_entropy (Optional[str]): Fixed entropy string for deterministic testing.

        Returns:
            Optional[bytes]: Derived key bytes if successful, None if locked out or error.
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

            base_material = symbolic_output.encode('utf-8')

            salted_material = self._add_salt_nonce(base_material) if use_salt else base_material
            derived_key = self._key_stretch(salted_material)

            if identity:
                self._clear_attempts(identity)

            logger.info(f"[SymbolicKeyDerivation] Derived secure key for identity {identity}")
            return derived_key

        except Exception as e:
            logger.error(f"[SymbolicKeyDerivation] Key derivation failed: {e}")
            if identity:
                self._record_failed_attempt(identity)
            return None

    def verify_key(self, key: bytes, trust_level: float, emotion_level: float, timestamp: float,
                   identity: Optional[str] = None, seed_phrase: Optional[str] = None) -> bool:
        """
        Verifies whether the provided key matches the derived key for the given parameters.

        Args:
            key (bytes): The key to verify.
            trust_level (float): Trust level used in derivation.
            emotion_level (float): Emotion level used in derivation.
            timestamp (float): Timestamp used in derivation.
            identity (Optional[str]): Identity string used for rate limiting.
            seed_phrase (Optional[str]): Seed phrase used in derivation.

        Returns:
            bool: True if the derived key matches the provided key, False otherwise.
        """
        derived = self.derive_key(trust_level, emotion_level, timestamp, identity, seed_phrase)
        if derived is None:
            return False
        return secrets.compare_digest(derived, key)

        # Alias for backward compatibility
symbolic_key_deriver = SymbolicKeyDerivation()