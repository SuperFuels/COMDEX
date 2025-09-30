# 📁 docs/CodexLang_Instruction/instruction_reference_builder.py
# -*- coding: utf-8 -*-
"""
Instruction Reference Builder (YAML-first)

Generates instruction_reference.md from docs/CodexLang_Instruction/instruction_registry.yaml.
- Groups by domain (top-level keys like logic, quantum, photon, symatics, etc.)
- For each canonical op, shows symbols merged from:
  • the raw symbol keys under each domain (e.g., logic: { ⊕: { canonical: logic:⊕, ... } })
  • OP_METADATA symbols for the same canonical key (if present)
- Appends collision cheat sheet, alias table, and priority order from YAML keys:
  collisions, aliases, priority_order
"""

import yaml
from collections import defaultdict
from pathlib import Path

REG_PATH = Path("docs/CodexLang_Instruction/instruction_registry.yaml")
OUT_PATH = Path("docs/CodexLang_Instruction/instruction_reference.md")


def load_registry():
    data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8"))
    return data or {}


def merge_symbols_for_canonical(reg, canonical_key):
    """Collect symbols from raw domain entries and OP_METADATA for a canonical key."""
    symbols = []

    # 1) Raw domain maps: domain -> { raw_symbol: { canonical, description } }
    for domain, entries in reg.items():
        if domain in ("OP_METADATA", "collisions", "aliases", "priority_order"):
            continue
        if not isinstance(entries, dict):
            continue
        for raw_symbol, meta in entries.items():
            if not isinstance(meta, dict):
                continue
            if meta.get("canonical") == canonical_key:
                symbols.append(raw_symbol)

    # 2) OP_METADATA symbols: OP_METADATA.{domain}.{canonical_key}.symbols
    opm = reg.get("OP_METADATA", {})
    domain = canonical_key.split(":")[0]
    mdomain = opm.get(domain, {})
    m = mdomain.get(canonical_key, {})
    for s in (m.get("symbols") or []):
        symbols.append(s)

    # Deduplicate while preserving order
    seen = set()
    return [s for s in symbols if not (s in seen or seen.add(s))]


def build_reference():
    reg = load_registry()

    # Build a map: domain -> list[(canonical_key, description, symbols)]
    domain_map = defaultdict(list)

    for domain, entries in reg.items():
        if domain in ("OP_METADATA", "collisions", "aliases", "priority_order"):
            continue
        if not isinstance(entries, dict):
            continue

        for raw_symbol, meta in entries.items():
            if not isinstance(meta, dict):
                continue
            canonical = meta.get("canonical")
            desc = meta.get("description", "_(no description available)_")
            if not canonical or ":" not in canonical:
                continue

            symbols = merge_symbols_for_canonical(reg, canonical)
            domain_map[domain].append((canonical, desc, symbols))

    # Sort domains and canonical keys
    for d in domain_map:
        domain_map[d].sort(key=lambda t: t[0])

    # Render markdown
    lines = []
    lines.append("# 📖 CodexLang Instruction Reference\n")
    lines.append("This document is auto-generated from instruction_registry.yaml.\n")
    lines.append("> Do not edit manually — run `python docs/CodexLang_Instruction/instruction_reference_builder.py`.\n")
    lines.append("\n---\n")

    # TOC
    lines.append("## Table of Contents\n")
    for d in sorted(domain_map.keys()):
        lines.append(f"- [{d.capitalize()}](#{d.lower()})")
        for canonical, _, _ in domain_map[d]:
            anchor = canonical.replace(":", "")
            lines.append(f"  - [{canonical}](#{anchor})")
    lines.append("- [⚖️ Collision Resolver Cheat Sheet](#️-collision-resolver-cheat-sheet)")
    lines.append("- [🔑 Alias Table](#-alias-table)")
    lines.append("- [📊 Priority Order](#-priority-order)\n")
    lines.append("\n---\n")

    # Domain sections
    for d in sorted(domain_map.keys()):
        lines.append(f"## {d.capitalize()}\n")
        for canonical, desc, symbols in domain_map[d]:
            sym_str = ", ".join(symbols) if symbols else "—"
            anchor = canonical.replace(":", "")
            lines.append(f"### `{canonical}`\n")
            lines.append(f"**Symbols:** {sym_str}\n")
            lines.append(f"**Canonical Key:** `{canonical}`\n")
            lines.append(f"**Description:** {desc}\n")
            lines.append("\n---\n")

    # Collisions / Aliases / Priority (from YAML)
    lines.append("## ⚖️ Collision Resolver Cheat Sheet\n")
    lines.append("Only a handful of symbols are ambiguous across domains. These require the collision resolver:\n")
    collisions = reg.get("collisions", {})
    if collisions:
        lines.append("\n| Symbol | Possible Canonicals |")
        lines.append("|--------|----------------------|")
        for sym, opts in collisions.items():
            lines.append(f"| {sym} | {', '.join(opts)} |")
    else:
        lines.append("\n_(none defined in YAML)_")
    lines.append("")

    lines.append("## 🔑 Alias Table\n")
    aliases = reg.get("aliases", {})
    if aliases:
        lines.append("\n| Alias | Resolves To |")
        lines.append("|-------|-------------|")
        for a, t in aliases.items():
            lines.append(f"| {a} | {t} |")
    else:
        lines.append("\n_(none defined in YAML)_")
    lines.append("")

    lines.append("## 📊 Priority Order\n")
    prio = reg.get("priority_order", [])
    if prio:
        lines.append("\n`" + " → ".join(prio) + "`\n")
        lines.append("\nExample: bare `↔` resolves to `logic:↔` because *logic outranks quantum*.\n")
    else:
        lines.append("\n_(none defined in YAML)_\n")

    # Write
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ Instruction reference regenerated at {OUT_PATH.resolve()}")


if __name__ == "__main__":
    build_reference()