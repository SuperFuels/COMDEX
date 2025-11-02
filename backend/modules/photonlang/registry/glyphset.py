# -*- coding: utf-8 -*-
from __future__ import annotations

# Canonical Photon/Symatics operator glyphs (superset; safe for tests)
PHOTON_GLYPHS: set[str] = {
    # Core algebraic operators
    "⊕", "μ", "↔", "⟲", "π",
    # Logic / comparison / syntax
    "∧", "∨", "¬", "≔", "≟", "⟶", "≠", "≡", "∈", "≤", "≥",
    # Arithmetic (reserved for future)
    "＋", "−", "∕", "＾",
    # Punctuation used in Photon contexts
    "∶", "·", "‚", "⁏",
    # Photon brackets
    "⟮", "⟯", "⟦", "⟧", "⦃", "⦄",
}

# Minimal operator registry: enough structure for tests and future IR contracts
OP_REGISTRY: dict[str, dict[str, object]] = {
    "⊕": {"id": "superpose", "arity": 2, "class": "algebra"},
    "μ": {"id": "measure",   "arity": 1, "class": "algebra"},
    "↔": {"id": "entangle",  "arity": 2, "class": "algebra"},
    "⟲": {"id": "resonate",  "arity": "n", "class": "algebra"},
    "π": {"id": "project",   "arity": 1, "class": "algebra"},

    "≔": {"id": "define",    "arity": 2, "class": "syntax"},
    "≟": {"id": "equiv_test","arity": 2, "class": "logic"},
    "⟶": {"id": "arrow",     "arity": 2, "class": "lambda"},

    "∧": {"id": "and",       "arity": 2, "class": "logic"},
    "∨": {"id": "or",        "arity": 2, "class": "logic"},
    "¬": {"id": "not",       "arity": 1, "class": "logic"},

    "≠": {"id": "neq",       "arity": 2, "class": "compare"},
    "≡": {"id": "equiv",     "arity": 2, "class": "compare"},
    "∈": {"id": "in",        "arity": 2, "class": "set"},
    "≤": {"id": "le",        "arity": 2, "class": "compare"},
    "≥": {"id": "ge",        "arity": 2, "class": "compare"},
}