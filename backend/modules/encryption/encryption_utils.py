import hashlib
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def derive_semantic_hash(value: str, salt: Optional[str] = None) -> str:
    """
    Creates a semantic hash based on identity or symbolic value (QGlyph lock seed).
    """
    combined = value + (salt or "")
    sha = hashlib.sha256(combined.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(sha[:24]).decode("utf-8")  # Shorten for tag use


def tag_with_qglyph_lock(packet: dict, meaning_key: str) -> dict:
    """
    Attaches a symbolic QGlyph tag based on meaning to the packet metadata.
    """
    tag = derive_semantic_hash(meaning_key)
    packet.setdefault("meta", {})["qglyph_tag"] = tag
    logger.debug(f"[QGlyphTag] Attached tag {tag} for key {meaning_key}")
    return packet


def validate_qglyph_tag(packet: dict, expected_key: str) -> bool:
    """
    Validates a symbolic QGlyph tag.
    """
    tag = packet.get("meta", {}).get("qglyph_tag")
    expected = derive_semantic_hash(expected_key)
    valid = tag == expected
    if not valid:
        logger.warning(f"[QGlyphTag] Mismatch: {tag} vs expected {expected}")
    return valid


def generate_key_hint_for_contract(identity: str, codex_contract: str) -> str:
    """
    Placeholder for deriving symbolic encryption keys from CodexLang contracts.
    """
    return derive_semantic_hash(identity + codex_contract)