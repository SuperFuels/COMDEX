# backend/modules/glyphnet/qkd_fingerprint.py

import hashlib
import base64
import json
import hmac
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class FingerprintMismatchError(Exception):
    """Raised when a wave's fingerprint or collapse hash fails verification."""


# ───────────────────────────────────────────────
# 🔒 Utility
# ───────────────────────────────────────────────
def _safe_compare(a: str, b: str) -> bool:
    """Timing-safe string comparison."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


# ───────────────────────────────────────────────
# 📡 Decoherence Fingerprinting
# ───────────────────────────────────────────────
def generate_decoherence_fingerprint(wave_state: Dict[str, Any]) -> str:
    """
    Generate a deterministic decoherence fingerprint based on wave state.

    Uses entropy, coherence, origin_trace, and QGlyph structure
    to produce a tamper-detectable base64-encoded SHA-256 hash.
    """
    raw_data = json.dumps(
        {
            "entropy": wave_state.get("entropy", ""),
            "coherence": wave_state.get("coherence", ""),
            "origin_trace": wave_state.get("origin_trace", ""),
            "qglyphs": wave_state.get("qglyphs", []),
        },
        sort_keys=True,
    ).encode("utf-8")

    sha = hashlib.sha256()
    sha.update(raw_data)
    return base64.urlsafe_b64encode(sha.digest()).decode("utf-8")


def verify_fingerprint(expected_fingerprint: str, wave_state: Dict[str, Any]) -> None:
    """
    Verify that the current wave_state matches the expected decoherence fingerprint.

    Raises:
        FingerprintMismatchError: if the fingerprint does not match.
    """
    actual = generate_decoherence_fingerprint(wave_state)
    if not _safe_compare(actual, expected_fingerprint):
        logger.warning(
            f"[QKD] ❌ Fingerprint mismatch.\nExpected: {expected_fingerprint}\nActual:   {actual}"
        )
        raise FingerprintMismatchError(
            f"Fingerprint mismatch.\nExpected: {expected_fingerprint}\nActual:   {actual}"
        )


# ───────────────────────────────────────────────
# 🌀 Collapse Hashing
# ───────────────────────────────────────────────
def collapse_hash(wave_payload: Dict[str, Any]) -> str:
    """
    Collapse hash for a symbolic payload used during QKD handshake verification.
    Ensures CodexLang logic integrity by hashing the codex + symbolic_tree.

    Args:
        wave_payload: A dict containing "codex" and "symbolic_tree".

    Returns:
        str: Base64-encoded SHA-256 collapse hash.
    """
    raw = json.dumps(
        {
            "codex": wave_payload.get("codex", ""),
            "symbolic_tree": wave_payload.get("symbolic_tree", {}),
        },
        sort_keys=True,
    ).encode("utf-8")

    sha = hashlib.sha256()
    sha.update(raw)
    return base64.urlsafe_b64encode(sha.digest()).decode("utf-8")


def verify_collapse_hash(expected_hash: str, wave_payload: Dict[str, Any]) -> None:
    """
    Verify that a payload matches the expected collapse hash.

    Args:
        expected_hash: The expected base64-encoded SHA-256 collapse hash.
        wave_payload: The payload dict with "codex" and "symbolic_tree".

    Raises:
        FingerprintMismatchError: if the collapse hash does not match.
    """
    actual = collapse_hash(wave_payload)
    if not _safe_compare(actual, expected_hash):
        logger.warning(
            f"[QKD] ❌ Collapse hash mismatch.\nExpected: {expected_hash}\nActual:   {actual}"
        )
        raise FingerprintMismatchError(
            f"Collapse hash mismatch.\nExpected: {expected_hash}\nActual:   {actual}"
        )


# ───────────────────────────────────────────────
# ✅ Combined Verifier
# ───────────────────────────────────────────────
def verify_wave_state_integrity(
    wave_state: Dict[str, Any],
    expected_fingerprint: Optional[str] = None,
    expected_collapse_hash: Optional[str] = None,
) -> None:
    """
    Verify both the decoherence fingerprint and collapse hash integrity
    for a given wave state + payload.

    Args:
        wave_state: Dict containing entropy, coherence, origin_trace, qglyphs,
                    codex, and symbolic_tree.
        expected_fingerprint: Optional expected fingerprint to validate.
        expected_collapse_hash: Optional expected collapse hash to validate.

    Raises:
        FingerprintMismatchError: if any integrity check fails.
    """
    if expected_fingerprint:
        verify_fingerprint(expected_fingerprint, wave_state)

    if expected_collapse_hash:
        verify_collapse_hash(expected_collapse_hash, wave_state)

    logger.debug("[QKD] ✅ Wave state integrity verified successfully.")