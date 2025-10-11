# -*- coding: utf-8 -*-
# File: backend/modules/glyphwave/core/wave_glyph.py
"""
Tessaris GlyphNet Core — WaveGlyph Definition & CodexLang Parsing
-----------------------------------------------------------------

This module defines the WaveGlyph class, which serves as the
base symbolic-light representation for the Tessaris GlyphNet system.

Enhancements include:
 - CodexLang parsing (parse_glyph)
 - Schema validation (phase, coherence ranges)
 - Fingerprinting and metadata enrichment
 - Compatibility with existing amplitude/origin_trace fields
 - Deterministic phase normalization (0–2π)
 - Granular validation errors and consistent timestamps

Author: Tessaris Research Group
Updated: 2025-10-10
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import time
import uuid
import re
import json
import hashlib
import datetime
import math


# ────────────────────────────────────────────────────────────────
# Custom Exceptions
# ────────────────────────────────────────────────────────────────

class GlyphValidationError(ValueError):
    """Raised when a WaveGlyph fails schema validation."""
    pass


# ────────────────────────────────────────────────────────────────
# Core WaveGlyph Class
# ────────────────────────────────────────────────────────────────

class WaveGlyph:
    def __init__(
        self,
        label: str,
        phase: float,
        amplitude: float,
        coherence: float,
        origin_trace: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None,
        uid: Optional[str] = None,
    ):
        self.uid = uid or str(uuid.uuid4())
        self.label = label
        self.phase = phase              # radians (0 to 2π)
        self.amplitude = amplitude      # normalized: 0.0 to 1.0
        self.coherence = coherence      # 0.0 (incoherent) to 1.0 (perfect)
        self.origin_trace = origin_trace or []  # lineage of glyphs
        self.metadata = metadata or {}  # CodexLang links, goals, SQI states, etc.
        self.timestamp = timestamp or time.time()

    # ────────────────────────────────────────────────────────────
    # Serialization
    # ────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, float | str | list | dict]:
        """Return a dict representation of the glyph for serialization."""
        return {
            "uid": self.uid,
            "label": self.label,
            "phase": self.phase,
            "amplitude": self.amplitude,
            "coherence": self.coherence,
            "origin_trace": self.origin_trace,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    def to_json(self, indent: int = 2) -> str:
        """Return a JSON representation of the glyph."""
        return json.dumps(self.to_dict(), indent=indent)

    def __repr__(self) -> str:
        """Clean representation for logs and debugging."""
        return f"<WaveGlyph {self.label} amp={self.amplitude:.2f} phase={self.phase:.2f} coh={self.coherence:.2f}>"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WaveGlyph":
        return cls(
            uid=data.get("uid"),
            label=data["label"],
            phase=data["phase"],
            amplitude=data["amplitude"],
            coherence=data["coherence"],
            origin_trace=data.get("origin_trace", []),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp"),
        )

    # ────────────────────────────────────────────────────────────
    # Hash Fingerprinting
    # ────────────────────────────────────────────────────────────

    def fingerprint(self) -> str:
        """Return a short deterministic fingerprint for this glyph."""
        h = hashlib.sha256()
        h.update(self.label.encode())
        h.update(str(self.phase).encode())
        h.update(str(self.coherence).encode())
        h.update(self.uid.encode())
        return h.hexdigest()[:16]


# ────────────────────────────────────────────────────────────────
# Glyph Schema & Validation
# ────────────────────────────────────────────────────────────────

GLYPH_SCHEMA = {
    "required": ["label", "phase", "amplitude", "coherence"],
    "phase_range": (0.0, 2 * math.pi),
    "coherence_range": (0.0, 1.0),
    "amplitude_range": (0.0, 1.0),
}


def validate_glyph(g: WaveGlyph) -> bool:
    """Validate a WaveGlyph object against Tessaris schema constraints."""
    for key in GLYPH_SCHEMA["required"]:
        if getattr(g, key, None) is None:
            raise GlyphValidationError(f"Missing required field: {key}")

    pmin, pmax = GLYPH_SCHEMA["phase_range"]
    if not (pmin <= g.phase <= pmax):
        raise GlyphValidationError(f"Phase {g.phase} out of range {pmin}–{pmax}")

    cmin, cmax = GLYPH_SCHEMA["coherence_range"]
    if not (cmin <= g.coherence <= cmax):
        raise GlyphValidationError(f"Coherence {g.coherence} out of range {cmin}–{cmax}")

    amin, amax = GLYPH_SCHEMA["amplitude_range"]
    if not (amin <= g.amplitude <= amax):
        raise GlyphValidationError(f"Amplitude {g.amplitude} out of range {amin}–{amax}")

    return True


# ────────────────────────────────────────────────────────────────
# CodexLang Expression Parsing
# ────────────────────────────────────────────────────────────────

_CodexLangPattern = re.compile(
    r"(?P<action>[a-zA-Z_][a-zA-Z0-9_]*)\((?P<target>[a-zA-Z0-9_:, ]+)\)"
)


def parse_glyph(
    expression: str,
    intent: str = "query",
    context: Optional[str] = None,
    amplitude: float = 1.0
) -> WaveGlyph:
    """
    Parse a CodexLang expression into a WaveGlyph.

    Example:
        >>> g = parse_glyph('observe(entropy::field)')
        >>> print(g.to_json())
    """
    match = _CodexLangPattern.match(expression.strip())
    if not match:
        raise GlyphValidationError(f"Invalid CodexLang expression: {expression}")

    label = f"{match.group('action')}_{match.group('target').replace('::', '_').replace(',', '_')}"
    now = time.time()  # use float for consistent KG timestamp format

    # Deterministic pseudo-randomized phase from hash, normalized to [0, 2π)
    phase_raw = (int(hashlib.md5(expression.encode()).hexdigest(), 16) % 6283) / 1000.0
    phase = phase_raw % (2 * math.pi)
    coherence = round((phase / (2 * math.pi)), 3)

    metadata = {
        "intent": intent,
        "context": context or "unspecified",
        "origin_trace": [f"CodexLang:{expression}"],
        "timestamp": now,
    }

    g = WaveGlyph(
        label=label,
        phase=phase,
        amplitude=amplitude,
        coherence=coherence,
        origin_trace=[expression],
        metadata=metadata,
    )
    validate_glyph(g)
    return g


# ────────────────────────────────────────────────────────────────
# Development Entry Point
# ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    exprs = [
        "observe(entropy::field)",
        "entangle(qwave::beam_01, photon::core)"
    ]
    for expr in exprs:
        try:
            glyph = parse_glyph(expr)
            print("Parsed Glyph Object:")
            print(glyph)
            print(glyph.to_json())
            print(f"Fingerprint: {glyph.fingerprint()}\n")
        except GlyphValidationError as e:
            print(f"Validation error: {e}")