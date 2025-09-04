# backend/modules/glyphnet/qkd_fingerprint.py

import hashlib
import base64
import json
from typing import Dict, Any

class FingerprintMismatchError(Exception):
    """Raised when a wave's fingerprint or collapse hash fails verification."""
    pass

def generate_decoherence_fingerprint(wave_state: Dict[str, Any]) -> str:
    """
    Generate a deterministic decoherence fingerprint based on wave state.

    Uses entropy, coherence, origin_trace, and QGlyph structure to produce a tamper-detectable hash.
    """
    entropy = wave_state.get("entropy", "")
    coherence = wave_state.get("coherence", "")
    origin_trace = wave_state.get("origin_trace", "")
    qglyphs = wave_state.get("qglyphs", [])

    raw_data = json.dumps({
        "entropy": entropy,
        "coherence": coherence,
        "origin_trace": origin_trace,
        "qglyphs": qglyphs
    }, sort_keys=True).encode("utf-8")

    sha = hashlib.sha256()
    sha.update(raw_data)
    return base64.urlsafe_b64encode(sha.digest()).decode("utf-8")

def verify_fingerprint(expected_fingerprint: str, wave_state: Dict[str, Any]) -> None:
    """
    Verify that the current wave_state matches the expected decoherence fingerprint.

    Raises FingerprintMismatchError if validation fails.
    """
    actual = generate_decoherence_fingerprint(wave_state)
    if actual != expected_fingerprint:
        raise FingerprintMismatchError(
            f"Fingerprint mismatch.\nExpected: {expected_fingerprint}\nActual:   {actual}"
        )

def collapse_hash(wave_payload: Dict[str, Any]) -> str:
    """
    Collapse hash for a symbolic payload used during QKD handshake verification.
    Can be used to validate CodexLang logic integrity.
    """
    codex = wave_payload.get("codex", "")
    symbolic_tree = wave_payload.get("symbolic_tree", {})

    raw = json.dumps({
        "codex": codex,
        "symbolic_tree": symbolic_tree
    }, sort_keys=True).encode("utf-8")

    sha = hashlib.sha256()
    sha.update(raw)
    return base64.urlsafe_b64encode(sha.digest()).decode("utf-8")