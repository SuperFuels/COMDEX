# -*- coding: utf-8 -*-
"""
Doc Sync Script - Photon Algebra
--------------------------------

Generates:
- docs/CodexLang_Instruction/instruction_reference.md
- docs/SYMATICS_AXIOMS.md
- docs/CodexLang_Instruction/instruction_registry.yaml (patched with Photon ops)

Source of truth = backend/photon_algebra/core.py + rewriter.py
"""

import inspect
import pathlib
import yaml
from backend.photon_algebra import core
from backend.photon_algebra.rewriter import REWRITE_RULES

DOCS_DIR = pathlib.Path("docs")
CODEx_YAML = DOCS_DIR / "CodexLang_Instruction" / "instruction_registry.yaml"

# ----------------------------
# Helpers
# ----------------------------

def extract_axioms():
    """Pulls function docstrings from core.py."""
    axioms = []
    for name, fn in inspect.getmembers(core, inspect.isfunction):
        if fn.__module__ == "backend.photon_algebra.core":
            doc = (fn.__doc__ or "").strip()
            if doc:
                axioms.append((name, doc))
    return axioms

def extract_rules():
    """Pulls rewrite rules from rewriter.py."""
    return REWRITE_RULES

def write_instruction_reference(axioms, rules):
    path = DOCS_DIR / "CodexLang_Instruction" / "instruction_reference.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Photon Algebra - Instruction Reference\n\n")
        f.write("## Axioms (P1-P8)\n\n")
        for name, doc in axioms:
            f.write(f"- **{name}** -> {doc}\n")
        f.write("\n## Rewrite Rules\n\n")
        for pat, repl in rules:
            f.write(f"- `{pat}` -> `{repl}`\n")

def write_symatics_axioms(axioms):
    path = DOCS_DIR / "SYMATICS_AXIOMS.md"
    existing = ""
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()

    delimiter = "\n---\n## Photon Algebra (Auto-Generated)\n"
    if delimiter in existing:
        manual, _ = existing.split(delimiter, 1)
    else:
        manual = existing.strip()

    auto = ["\n---\n## Photon Algebra (Auto-Generated)\n"]
    for name, doc in axioms:
        auto.append(f"### {name}\n\n{doc}\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write((manual.strip() if manual else "") + "".join(auto))

def patch_codex_yaml(axioms):
    if not CODEx_YAML.exists():
        print("[WARN] Codex YAML not found, skipping patch.")
        return
    with open(CODEx_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    data.setdefault("OP_METADATA", {})
    for name, doc in axioms:
        key = f"photon:{name}"
        entry = data["OP_METADATA"].setdefault(key, {})
        entry["description"] = doc
        entry.setdefault("symbols", [])

    with open(CODEx_YAML, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

# ----------------------------
# Entrypoint
# ----------------------------

def main():
    axioms = extract_axioms()
    rules = extract_rules()
    write_instruction_reference(axioms, rules)
    write_symatics_axioms(axioms)
    patch_codex_yaml(axioms)
    print("✅ Doc sync completed.")

if __name__ == "__main__":
    main()