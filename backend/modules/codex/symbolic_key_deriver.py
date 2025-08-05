import logging
import hashlib
import base64
from typing import Optional, Dict, Any

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


def get_collapse_trace() -> list[Dict[str, Any]]:
    """
    Return the internal collapse trace for introspection (CodexHUD or GlyphNet).
    """
    return symbolic_key_deriver.collapse_trace


def get_entanglement_map() -> Dict[str, str]:
    """
    Return the internal ↔ entanglement registry (identity ↔ glyphKey).
    """
    return symbolic_key_deriver.entanglement_registry


def export_collapse_trace_with_soullaw_metadata(identity: Optional[str] = None) -> Dict[str, Any]:
    """
    Export collapse trace for inclusion in `.dc.json` container, with SoulLaw metadata.
    """
    trace = get_collapse_trace()
    entanglement = get_entanglement_map()

    verdict = None
    if identity:
        from backend.modules.codex.soul_law_validator import validate_avatar_state
        verdict = validate_avatar_state(identity)

    export_data = {
        "collapse_trace": trace,
        "entanglement_map": entanglement,
        "soullaw_verdict": verdict,
    }
    logger.info("[SymbolicKeyDeriver] Exported collapse trace with SoulLaw metadata")
    return export_data


def derive_entropy_hash(data: str, salt: str = "glyph_entropy") -> str:
    """
    Derives a stable entropy hash from input data for GHX, SQI, and SoulLaw.

    Args:
        data (str): Input data (glyph strings, container IDs, etc.)
        salt (str): Optional salt to differentiate hashing contexts.

    Returns:
        str: Base64-encoded SHA256 entropy hash.
    """
    if not isinstance(data, str):
        data = str(data)

    entropy = f"{salt}:{data}".encode("utf-8")
    sha = hashlib.sha256(entropy).digest()
    hash_result = base64.urlsafe_b64encode(sha).decode("utf-8").rstrip("=")

    logger.debug(f"[SymbolicKeyDeriver] Entropy hash derived (salt={salt}): {hash_result}")
    return hash_result