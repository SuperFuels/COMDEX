# 📁 docs/CodexLang_Instruction/yamlsync.py
# -*- coding: utf-8 -*-
"""
YAML Sync Script — Photon Algebra
---------------------------------
Merges Photon ops into `instruction_registry.yaml` from:
- backend/photon_algebra/core.py (axioms, operators)
- backend/photon_algebra/rewriter.py (rewrite rules)

Preserves other domains (logic, quantum, symatics, etc.).
Orders Photon ops canonically: P1–P8, then ∅.
"""

import inspect
import pathlib
import yaml
from backend.photon_algebra import core
from backend.photon_algebra.rewriter import REWRITE_RULES

YAML_PATH = pathlib.Path("docs/CodexLang_Instruction/instruction_registry.yaml")

# ----------------------------
# Canonical Photon ordering (P1–P8 + ∅)
# ----------------------------
PHOTON_ORDER = [
    "photon:identity",   # P1
    "photon:superpose",  # P2
    "photon:entangle",   # P3
    "photon:fuse",       # P4
    "photon:cancel",     # P5
    "photon:negate",     # P6
    "photon:collapse",   # P7
    "photon:project",    # P8
    "photon:∅",          # Canonical EMPTY
]

# ----------------------------
# Helpers
# ----------------------------
def extract_photon_ops():
    """Generate Photon operator metadata from core.py."""
    ops = {}
    for name, fn in inspect.getmembers(core, inspect.isfunction):
        if fn.__module__ == "backend.photon_algebra.core":
            doc = (fn.__doc__ or "").strip()
            key = f"photon:{name}"
            ops[key] = {
                "description": doc or f"(auto) {name}",
                "symbols": guess_symbols(name),
            }

    # Canonical EMPTY (∅)
    ops["photon:∅"] = {
        "description": "Canonical empty state (EMPTY)",
        "symbols": ["∅"],
    }
    return ops


def guess_symbols(name: str):
    """Map function name → expected operator symbols."""
    mapping = {
        "superpose": ["⊕"],
        "entangle": ["↔"],
        "fuse": ["⊗"],
        "cancel": ["⊖"],
        "negate": ["¬"],
        "collapse": ["∇"],
        "project": ["★"],
        "identity": [],  # identity doesn’t get its own op symbol
    }
    return mapping.get(name, [])


def order_photon_section(photon_ops: dict) -> dict:
    """Sort Photon ops according to PHOTON_ORDER, keep extras at end."""
    ordered = {}
    for key in PHOTON_ORDER:
        if key in photon_ops:
            ordered[key] = photon_ops[key]
    # append any unlisted extras
    for key in sorted(photon_ops.keys()):
        if key not in ordered:
            ordered[key] = photon_ops[key]
    return ordered


# ----------------------------
# YAML Sync
# ----------------------------
def sync_yaml():
    ops = extract_photon_ops()

    if YAML_PATH.exists():
        with open(YAML_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}

    # ensure OP_METADATA root
    data.setdefault("OP_METADATA", {})
    photon_section = data["OP_METADATA"].setdefault("photon", {})

    # patch/merge photon ops
    for key, meta in ops.items():
        photon_section[key] = meta

    # reorder canonically
    data["OP_METADATA"]["photon"] = order_photon_section(photon_section)

    with open(YAML_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    print(f"✅ Photon ops merged + ordered into {YAML_PATH}")


# ----------------------------
# Entrypoint
# ----------------------------
if __name__ == "__main__":
    sync_yaml()