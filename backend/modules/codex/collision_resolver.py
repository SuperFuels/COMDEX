# 📁 backend/modules/codex/collision_resolver.py

"""
Collision Resolver for CodexLang Operators

Centralizes how raw symbols map to canonical, domain-tagged operator keys.
- Prefer explicit aliases (e.g., ⊕_q -> quantum:⊕).
- For ambiguous raw symbols (⊗, ⊕, ↔, ...), resolve by priority or optional context.
- Fall back to the flat CANONICAL_OPS map only for non-colliding symbols.
- Supports overrides from config/resolver_config.yaml (hot-reloadable).
"""

import os
import yaml
from typing import Optional, Dict, List
from backend.modules.codex.canonical_ops import CANONICAL_OPS

# ───────────────────────────────────────────────
# Default static maps (fallback if YAML missing)
# ───────────────────────────────────────────────

ALIASES: Dict[str, str] = {
    "⊕_q": "quantum:⊕",
    "⊗_p": "physics:⊗",
    "⊗_s": "symatics:⊗",
    "~": "photon:≈",
}

COLLISIONS: Dict[str, List[str]] = {
    "⊗": ["logic:⊗", "physics:⊗", "symatics:⊗"],
    "⊕": ["logic:⊕", "quantum:⊕"],
    "↔": ["logic:↔", "quantum:↔"],
    "∇": ["math:∇"],
    "≈": ["photon:≈"],
}

PRIORITY_ORDER: List[str] = [
    "logic",
    "math",
    "physics",
    "quantum",
    "symatics",
    "photon",
    "control",
]

# Path to optional YAML config (project-level)
CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    "../../../..", "config", "resolver_config.yaml"
)


# ───────────────────────────────────────────────
# Config loader
# ───────────────────────────────────────────────

def load_config(path: str = CONFIG_PATH):
    """Load resolver settings from YAML if available, overriding defaults."""
    global ALIASES, COLLISIONS, PRIORITY_ORDER
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        # Merge overrides
        if "ALIASES" in cfg:
            ALIASES.update(cfg["ALIASES"])
        if "COLLISIONS" in cfg:
            COLLISIONS.update(cfg["COLLISIONS"])
        if "PRIORITY_ORDER" in cfg:
            PRIORITY_ORDER[:] = cfg["PRIORITY_ORDER"]

# Auto-load at module import
load_config()

def reload_config():
    """Manually trigger a reload of resolver YAML (hot-reload)."""
    load_config()


# ───────────────────────────────────────────────
# Resolver functions
# ───────────────────────────────────────────────

def resolve_collision(symbol: str, context: Optional[str] = None) -> Optional[str]:
    """
    Resolve a raw symbol into a canonical key using:
      - Explicit context (if provided and valid)
      - Global PRIORITY_ORDER (default fallback)
    """
    options = COLLISIONS.get(symbol)
    if not options:
        return None

    # 1️⃣ Prefer explicit context
    if context:
        for opt in options:
            if opt.startswith(context + ":"):
                return opt

    # 2️⃣ Otherwise, choose by global priority order
    for domain in PRIORITY_ORDER:
        for opt in options:
            if opt.startswith(domain + ":"):
                return opt

    return None


def resolve_op(op: str, context: Optional[str] = None) -> str:
    """
    Public API for canonicalizing operators.

    Resolution order:
      1) ALIASES (explicit disambiguation like ⊕_q -> quantum:⊕)
      2) COLLISIONS (ambiguous raw symbols resolved by context/priority)
      3) CANONICAL_OPS (simple, non-colliding mappings)
      4) Fallback (raw input)
    """
    # 1️⃣ Alias wins outright
    if op in ALIASES:
        return ALIASES[op]

    # 2️⃣ Collision resolution (context-aware, then priority fallback)
    if op in COLLISIONS:
        resolved = resolve_collision(op, context=context)
        if resolved:
            return resolved

    # 3️⃣ Direct canonical mapping (non-colliding)
    if op in CANONICAL_OPS:
        return CANONICAL_OPS[op]

    # 4️⃣ Fallback - return as-is
    return op


def is_collision(symbol: str) -> bool:
    """Check if a symbol has multiple canonical mappings."""
    return symbol in COLLISIONS