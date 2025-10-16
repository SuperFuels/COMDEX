import logging
import hashlib
import time
import secrets
from typing import Optional, Dict

from backend.modules.hexcore.memory_engine import get_runtime_entropy_snapshot
from backend.modules.glyphnet.ephemeral_key_manager import get_ephemeral_key_manager
from backend.modules.glyphvault.soul_law_validator import soul_law_validator  # ✅ Updated to singleton validator
from backend.modules.codex.codex_core import CodexCore

logger = logging.getLogger(__name__)


class SymbolicKeyDerivation:
    MAX_ATTEMPTS = 10  # Added to match test expectation

    def __init__(self):
        self._codex_adapter = None
        self.brute_force_attempts: Dict[str, int] = {}
        self.lockout_time = 300  # seconds to lockout
        self.lockouts: Dict[str, float] = {}
        self.collapse_trace = []
        self.entanglement_registry = {}

    def _get_codex_adapter(self):
        if self._codex_adapter is None:
            try:
                self._codex_adapter = CodexCore()
                logger.info("[SymbolicKeyDerivation] CodexCore initialized for collapse logic")
            except Exception as e:
                logger.warning(f"[SymbolicKeyDerivation] Falling back to dummy adapter: {e}")

                class DummyAdapter:
                    def evaluate(self, input_str):
                        return hashlib.sha256(input_str.encode('utf-8')).hexdigest()

                self._codex_adapter = DummyAdapter()
        return self._codex_adapter

    def _is_locked_out(self, identity: str) -> bool:
        expiry = self.lockouts.get(identity, 0)
        if time.time() < expiry:
            logger.warning(f"[SymbolicKeyDerivation] Identity {identity} locked out until {expiry}")
            return True
        return False

    def _record_failed_attempt(self, identity: str):
        self.brute_force_attempts[identity] = self.brute_force_attempts.get(identity, 0) + 1
        if self.brute_force_attempts[identity] >= self.MAX_ATTEMPTS:
            self.lockouts[identity] = time.time() + self.lockout_time
            logger.warning(f"[SymbolicKeyDerivation] Identity {identity} locked out due to brute force attempts")
            self.brute_force_attempts[identity] = 0

    def _clear_attempts(self, identity: str):
        if identity in self.brute_force_attempts:
            del self.brute_force_attempts[identity]
        if identity in self.lockouts:
            del self.lockouts[identity]

    def _get_entropy(self):
        try:
            return get_runtime_entropy_snapshot()
        except Exception as e:
            logger.error(f"[SymbolicKeyDerivation] Entropy retrieval failed: {e}")
            return ""

    def _gather_entropy(self, trust_level: float, emotion_level: float, timestamp: float) -> str:
        entropy_part = self._get_entropy()
        seed = f"Trust:{trust_level};Emotion:{emotion_level};Time:{timestamp};Entropy:{entropy_part}"
        return seed

    def _add_salt_nonce(self, base_material: bytes) -> bytes:
        salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(12)
        combined = salt + nonce + base_material
        logger.debug("[SymbolicKeyDerivation] Added salt and nonce for key material")
        return combined

    def _key_stretch(self, input_bytes: bytes, iterations: int = 10000) -> bytes:
        stretched = input_bytes
        for _ in range(iterations):
            stretched = hashlib.sha256(stretched).digest()
        logger.debug(f"[SymbolicKeyDerivation] Performed key stretching with {iterations} iterations")
        return stretched

    def _register_collapse_trace(self, expression: str, output: str, adapter: str, qbit: Optional[str], entangled_with: Optional[str]):
        trace_entry = {
            "expression": expression,
            "output": output,
            "adapter": adapter,
            "timestamp": time.time(),
            "qbit": qbit,
            "↔": entangled_with
        }
        self.collapse_trace.append(trace_entry)
        logger.debug(f"[SymbolicKeyDerivation] Collapse trace recorded: {trace_entry}")

    def _register_entanglement(self, identity: str) -> str:
        if identity in self.entanglement_registry:
            return self.entanglement_registry[identity]
        glyph_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        self.entanglement_registry[identity] = glyph_key
        self.entanglement_registry[glyph_key] = identity  # bidirectional
        logger.debug(f"[SymbolicKeyDerivation] QBit entanglement registered: {identity} ↔ {glyph_key}")
        return glyph_key

    def derive_key(self, trust_level: float, emotion_level: float, timestamp: float,
                   identity: Optional[str] = None, seed_phrase: Optional[str] = None) -> Optional[bytes]:

        if not isinstance(trust_level, (float, int)) or not isinstance(emotion_level, (float, int)) or not isinstance(timestamp, (float, int)):
            raise TypeError("trust_level, emotion_level, and timestamp must be numeric")
        if identity is not None and not isinstance(identity, str):
            raise TypeError("identity must be a string if provided")
        if seed_phrase is not None and not isinstance(seed_phrase, str):
            raise TypeError("seed_phrase must be a string if provided")

        if identity:
            if self._is_locked_out(identity):
                logger.error(f"[SymbolicKeyDerivation] Derivation blocked due to lockout for identity {identity}")
                return None

            # ✅ Soul Law validation (using singleton)
            if not soul_law_validator.validate_avatar({"id": identity, "role": "system"}):
                logger.error(f"[SymbolicKeyDerivation] SoulLaw rejected identity {identity}")
                return None

        try:
            base_input = self._gather_entropy(float(trust_level), float(emotion_level), float(timestamp))
            if seed_phrase:
                base_input += f";Seed:{seed_phrase}"

            expression = f"⟦ Key : {base_input} ⟧"
            codex_adapter = self._get_codex_adapter()
            symbolic_output = codex_adapter.evaluate(expression)
            adapter_type = codex_adapter.__class__.__name__

            base_material = symbolic_output.encode("utf-8")
            salted_material = self._add_salt_nonce(base_material)
            derived_key = self._key_stretch(salted_material)

            qbit = self._register_entanglement(identity) if identity else None
            entangled_with = self.entanglement_registry.get(qbit) if qbit else None
            self._register_collapse_trace(expression, symbolic_output, adapter_type, qbit, entangled_with)

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
    if identity and self._is_locked_out(identity):
        logger.error(f"[SymbolicKeyDerivation] Verification blocked due to lockout for identity {identity}")
        return False

    derived = self.derive_key(trust_level, emotion_level, timestamp, identity, seed_phrase)
    if derived is None:
        return False

    match = derived == key
    if not match and identity:
        self._record_failed_attempt(identity)
    elif match and identity:
        self._clear_attempts(identity)

    return match


symbolic_key_deriver = SymbolicKeyDerivation()

# ✅ Compatibility Shim for Legacy Imports
def estimate_glyph_cost(glyph_expression: str) -> float:
    """
    Backwards-compatible cost estimation for glyphs.
    Uses CodexCore evaluation complexity as a cost proxy.
    """
    try:
        adapter = symbolic_key_deriver._get_codex_adapter()
        result = adapter.evaluate(glyph_expression)
        if isinstance(result, str):
            return float(len(result)) / 256.0  # Approximate cost based on symbolic output size
        return 1.0
    except Exception as e:
        logger.error(f"[SymbolicKeyDerivation] Cost estimation failed: {e}")
        return 1.0


# ✅ Compatibility Stub for Legacy Imports
class CodexContextAdapter:
    """
    Legacy placeholder for CodexContextAdapter.
    Routes calls to SymbolicKeyDerivation for modern key/collapse logic.
    """
    def __init__(self):
        self.symbolic_deriver = symbolic_key_deriver

    def evaluate(self, expression: str) -> str:
        """
        Mimics legacy CodexContextAdapter.evaluate behavior
        using CodexCore (via SymbolicKeyDerivation).
        """
        adapter = self.symbolic_deriver._get_codex_adapter()
        return adapter.evaluate(expression)

# =========================================================
# 🧠 Context Adapter Bridge
# =========================================================
def adapt_codex_context(content: str, source: str = "memory") -> dict:
    """
    Provides a backward-compatible context adapter used by CodexMemoryTrigger.
    Builds a symbolic evaluation context for CodexLang glyphs.
    """
    try:
        adapter = CodexContextAdapter()
        symbolic_result = adapter.evaluate(f"⟦ adapt : {content} ⟧")
        return {
            "source": source,
            "adapted": symbolic_result,
            "timestamp": time.time(),
            "meta": {
                "entropy": symbolic_key_deriver._get_entropy(),
                "adapter": adapter.__class__.__name__,
            }
        }
    except Exception as e:
        logger.error(f"[CodexContextAdapter] adapt_codex_context failed: {e}")
        return {
            "source": source,
            "adapted": content,
            "error": str(e),
            "timestamp": time.time(),
        }