import logging
from typing import Optional

from backend.modules.codex.codex_context_adapter import SymbolicKeyDerivation

logger = logging.getLogger(__name__)

# Instantiate the global symbolic key derivation engine
symbolic_key_deriver = SymbolicKeyDerivation()

def derive_symbolic_key(
    trust_level: float,
    emotion_level: float,
    timestamp: float,
    identity: Optional[str] = None,
    seed_phrase: Optional[str] = None
) -> Optional[bytes]:
    """
    Public function to derive a symbolic key using Codex collapse + SoulLaw validation.
    """
    return symbolic_key_deriver.derive_key(
        trust_level=trust_level,
        emotion_level=emotion_level,
        timestamp=timestamp,
        identity=identity,
        seed_phrase=seed_phrase
    )

def verify_symbolic_key(
    key: bytes,
    trust_level: float,
    emotion_level: float,
    timestamp: float,
    identity: Optional[str] = None,
    seed_phrase: Optional[str] = None
) -> bool:
    """
    Public function to verify a symbolic key by re-deriving and comparing.
    """
    return symbolic_key_deriver.verify_key(
        key=key,
        trust_level=trust_level,
        emotion_level=emotion_level,
        timestamp=timestamp,
        identity=identity,
        seed_phrase=seed_phrase
    )

def get_collapse_trace():
    """
    Return the internal collapse trace for introspection (CodexHUD or GlyphNet).
    """
    return symbolic_key_deriver.collapse_trace

def get_entanglement_map():
    """
    Return the internal ↔ entanglement registry (identity ↔ glyphKey).
    """
    return symbolic_key_deriver.entanglement_registry