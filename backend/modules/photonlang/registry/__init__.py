# -*- coding: utf-8 -*-
from __future__ import annotations
from .glyphset import PHOTON_GLYPHS, OP_REGISTRY

def load_registry() -> dict:
    """
    Returns a stable registry payload for tests and cross-language consumers.
    Keys:
      - glyphs: sorted list of all known Photon glyphs
      - ops   : mapping glyph -> metadata dict (id/arity/class)
    """
    return {
        "glyphs": sorted(PHOTON_GLYPHS),
        "ops": OP_REGISTRY,
    }

__all__ = ["load_registry", "PHOTON_GLYPHS", "OP_REGISTRY"]