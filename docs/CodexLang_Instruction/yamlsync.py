# 📁 docs/CodexLang_Instruction/yamlsync.py
# -*- coding: utf-8 -*-
"""
YAML Sync Script — Photon Algebra (flat OP_METADATA)
----------------------------------------------------
Merges Photon ops into docs/CodexLang_Instruction/instruction_registry.yaml
from backend/photon_algebra/core.py. Writes flat OP_METADATA keys:

OP_METADATA:
  photon:identity: {description: ..., symbols: [...]}
  photon:superpose: ...

Cleans legacy nested OP_METADATA["photon"] or duplicate flat keys.
"""

import inspect
import pathlib
import yaml
from backend.photon_algebra import core

YAML_PATH = pathlib.Path("docs/CodexLang_Instruction/instruction_registry.yaml")

PHOTON_ORDER = [
    "photon:identity",   # P1
    "photon:superpose",  # P2
    "photon:entangle",   # P3
    "photon:fuse",       # P4
    "photon:cancel",     # P5
    "photon:negate",     # P6
    "photon:collapse",   # P7
    "photon:project",    # P8
    "photon:∅",          # EMPTY
]

def guess_symbols(name: str):
    return {
        "superpose": ["⊕"],
        "entangle": ["↔"],
        "fuse": ["⊗"],
        "cancel": ["⊖"],
        "negate": ["¬"],
        "collapse": ["∇"],
        "project": ["★"],
        "identity": [],
    }.get(name, [])

def extract_photon_ops():
    ops = {}
    for name, fn in inspect.getmembers(core, inspect.isfunction):
        if fn.__module__ == "backend.photon_algebra.core":
            doc = (fn.__doc__ or "").strip()
            key = f"photon:{name}"
            ops[key] = {"description": doc or f"(auto) {name}", "symbols": guess_symbols(name)}
    ops["photon:∅"] = {"description": "Canonical empty state (EMPTY)", "symbols": ["∅"]}
    return ops

def sync_yaml():
    ops = extract_photon_ops()
    data = {}
    if YAML_PATH.exists():
        data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8")) or {}

    opm = data.setdefault("OP_METADATA", {})

    # 🧹 Remove legacy nested subtree OP_METADATA["photon"] if present
    if isinstance(opm.get("photon"), dict):
        for k, v in list(opm["photon"].items()):
            if k.startswith("photon:"):
                opm[k] = v  # lift up to flat
        del opm["photon"]

    # Patch/merge flat photon ops
    opm.update(ops)

    # Reorder: keep photon ops in PHOTON_ORDER, others untouched
    # Build new OP_METADATA with ordered photon keys
    new_opm = {}
    # first, copy non-photon keys as-is
    for k, v in opm.items():
        if not k.startswith("photon:"):
            new_opm[k] = v
    # then, ordered photon keys
    for k in PHOTON_ORDER:
        if k in opm:
            new_opm[k] = opm[k]
    # finally, any extra photon keys not in order list
    for k in sorted(opm.keys()):
        if k.startswith("photon:") and k not in new_opm:
            new_opm[k] = opm[k]

    data["OP_METADATA"] = new_opm

    YAML_PATH.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"✅ Photon ops merged + ordered into {YAML_PATH}")

if __name__ == "__main__":
    sync_yaml()