# backend/modules/photonlang/registry.py
from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

# Path to the JSON registry shipped with the package
_REG_PATH = Path(__file__).resolve().parent / "ops" / "operators.json"


@dataclass(frozen=True)
class OperatorSpec:
    glyph: str
    name: str
    arity: str  # e.g. "1", "2", "n"


def _nfc(s: str) -> str:
    """Normalize to NFC so composed glyphs compare reliably."""
    return unicodedata.normalize("NFC", s)


def load_registry() -> Dict[str, OperatorSpec]:
    """
    Load the operator registry from JSON.
    Returns a mapping of glyph -> OperatorSpec.
    On missing/invalid file, returns an empty dict (non-fatal).
    """
    try:
        data = json.loads(_REG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

    table: Dict[str, OperatorSpec] = {}
    for op in data.get("operators", []):
        spec = OperatorSpec(
            glyph=_nfc(op["glyph"]),
            name=op["name"],
            arity=str(op.get("arity", "n")),
        )
        table[spec.glyph] = spec
    return table


def ops_table_for_runtime() -> Dict[str, str]:
    """Return glyph -> canonical op-name mapping for runtime lookups (__OPS__)."""
    return {g: s.name for g, s in load_registry().items()}


def registry_glyphs() -> set[str]:
    """
    Dynamic view of glyphs declared in operators.json.
    Kept separate from the static canonical GLYPHSET below.
    """
    return set(load_registry().keys())

# -*- coding: utf-8 -*-
from __future__ import annotations

# Canonical Photon/Symatics operator glyphs (superset; used by tests)
PHOTON_GLYPHS: set[str] = {
    # Core algebraic operators
    "⊕", "μ", "↔", "⟲", "π",
    # Logic / comparison / syntax
    "∧", "∧̄", "∨", "¬",
    "≔", "≟", "≟≟", "≠", "≠≟", "≡", "∈", "≤", "≥",
    "⟶",
    # Arithmetic (reserved for future)
    "＋", "−", "∕", "＾",
    # Punctuation used in Photon contexts
    "∶", "·", "‚", "⁏",
    # Photon brackets
    "⟮", "⟯", "⟦", "⟧", "⦃", "⦄",
}

# Minimal operator registry: include canonical forms + composites as aliases
OP_REGISTRY: dict[str, dict[str, object]] = {
    # Algebra
    "⊕": {"id": "superpose", "arity": 2, "class": "algebra"},
    "μ": {"id": "measure",   "arity": 1, "class": "algebra"},
    "↔": {"id": "entangle",  "arity": 2, "class": "algebra"},
    "⟲": {"id": "resonate",  "arity": "n", "class": "algebra"},
    "π": {"id": "project",   "arity": 1, "class": "algebra"},

    # Syntax / lambda
    "≔": {"id": "define",        "arity": 2, "class": "syntax"},
    "⟶": {"id": "arrow",         "arity": 2, "class": "lambda"},

    # Logic (canonicals)
    "∧":  {"id": "and",          "arity": 2, "class": "logic"},
    "∨":  {"id": "or",           "arity": 2, "class": "logic"},
    "¬":  {"id": "not",          "arity": 1, "class": "logic"},
    "≟":  {"id": "equiv_test",   "arity": 2, "class": "logic"},

    # Logic (composites as aliases)
    "∧̄": {"id": "and_sc",       "arity": 2, "class": "logic",   "alias_of": "∧"},
    "≟≟": {"id": "equiv_strict", "arity": 2, "class": "logic",   "alias_of": "≟"},

    # Comparison (canonicals)
    "≠":  {"id": "neq",          "arity": 2, "class": "compare"},
    "≡":  {"id": "equiv",        "arity": 2, "class": "compare"},
    "∈":  {"id": "in",           "arity": 2, "class": "set"},
    "≤":  {"id": "le",           "arity": 2, "class": "compare"},
    "≥":  {"id": "ge",           "arity": 2, "class": "compare"},

    # Comparison (composite alias)
    "≠≟": {"id": "neq_strict",   "arity": 2, "class": "compare", "alias_of": "≠"},

    # Punctuation (listed so tests can treat them as “known”)
    "∶": {"id": "colon_ratio",   "class": "punct"},
    "·": {"id": "dot_middle",    "class": "punct"},
    "‚": {"id": "comma_low",     "class": "punct"},
    "⁏": {"id": "semicolon",     "class": "punct"},
}

def registry_glyphs() -> set[str]:
    """
    Dynamic view of glyphs declared in operators.json.
    """
    return set(load_registry().keys())

def glyphs() -> set[str]:
    """Static canonical glyph set used by tests/consumers."""
    return set(PHOTON_GLYPHS)