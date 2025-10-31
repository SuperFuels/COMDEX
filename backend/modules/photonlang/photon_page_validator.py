"""
Photon Page Validator (v0.2)
Ensures .ptn capsule format, symbolic integrity and entanglement constraints.
"""

from __future__ import annotations
from typing import Any, Dict, List

# Allowed operators from Photonic glyph alphabet
GLYPHS = set("⊕↔⟲μπ⇒∇⧖")

def _validate_glyph_stream(stream: List[str]):
    for g in stream:
        if any(ch not in GLYPHS for ch in g):
            raise ValueError(f"Invalid glyph in Photon page: {g}")

def _validate_entanglement(page: Dict[str, Any]):
    links = page.get("links", [])
    if not isinstance(links, list):
        raise ValueError("links must be list")

    for link in links:
        if not isinstance(link, dict):
            raise ValueError("each link must be dict")
        if "target" not in link:
            raise ValueError("entanglement link missing target")
        if "type" in link and link["type"] not in ("↔", "π", "⧖"):
            raise ValueError(f"invalid entanglement type {link['type']}")

def _validate_replay_tape(page: Dict[str, Any]):
    if "delta" in page and not isinstance(page["delta"], list):
        raise ValueError("delta must be CRDT delta array")

def _validate_resonance_block(page: Dict[str, Any]):
    if "resonance" not in page:
        return
    r = page["resonance"]
    for k in ("psi", "rho", "kappa"):
        if k not in r:
            raise ValueError(f"resonance missing {k}")

def validate_page_entanglement(page: Dict[str, Any]) -> bool:
    """
    Validate .ptn page structure, entanglement graph & glyph stream.
    This is the canonical validator used before executing Photon pages.
    """

    # Required core fields
    for req in ("source", "glyphs"):
        if req not in page:
            raise ValueError(f"Photon page missing required field: {req}")

    # Glyph correctness
    glyphs = page.get("glyphs", [])
    if not isinstance(glyphs, list):
        raise ValueError("glyphs must be list of glyph tokens")

    _validate_glyph_stream(glyphs)

    # Entanglement relations (WikiCapsule style links)
    _validate_entanglement(page)

    # Replay / Delta memory
    _validate_replay_tape(page)

    # Resonance metadata block
    _validate_resonance_block(page)

    # Placeholder for v0.3 entropy signature enforcement
    if "entropy_signature" in page and not isinstance(page["entropy_signature"], str):
        raise ValueError("entropy_signature must be string")

    return True