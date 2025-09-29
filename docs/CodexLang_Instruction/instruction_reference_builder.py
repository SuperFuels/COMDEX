# 📁 docs/CodexLang_Instruction/instruction_reference_builder.py

"""
Instruction Reference Builder

Generates instruction_reference.md from instruction_registry.yaml.
- Groups by domain
- Lists symbols per canonical key
- Annotates operator collisions using COLLISIONS
- Appends a global collision cheat sheet + resolver rules + aliases + priority order
"""

import os
import yaml
from collections import defaultdict

# Load registry
REGISTRY_PATH = os.path.join("docs", "CodexLang_Instruction", "instruction_registry.yaml")
with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    registry = yaml.safe_load(f)

OP_METADATA = registry.get("OP_METADATA", {})
CANONICAL_OPS = registry.get("CANONICAL_OPS", {})
COLLISIONS = registry.get("COLLISIONS", {})
ALIASES = registry.get("ALIASES", {})
PRIORITY_ORDER = registry.get("PRIORITY_ORDER", [])


def build_reference() -> str:
    """
    Build Markdown documentation for all canonical ops.
    """
    lines = []
    lines.append("# 📖 CodexLang Instruction Reference\n")
    lines.append("This document is auto-generated from instruction_registry.yaml.\n")
    lines.append("> Do not edit manually — run `python docs/CodexLang_Instruction/instruction_reference_builder.py`.\n")
    lines.append("\n---\n")

    # ─────────────────────────────────────────────────────────────
    # Group operators by domain
    # ─────────────────────────────────────────────────────────────
    domains = defaultdict(list)
    for canonical, meta in OP_METADATA.items():
        domain = canonical.split(":")[0]
        domains[domain].append((canonical, meta))

    # ─────────────────────────────────────────────────────────────
    # Table of Contents
    # ─────────────────────────────────────────────────────────────
    lines.append("## Table of Contents\n")
    for domain in sorted(domains.keys()):
        lines.append(f"- [{domain.capitalize()}](#{domain.lower()})")
        for key, _ in sorted(domains[domain], key=lambda kv: kv[0]):
            lines.append(f"  - [{key}](#{key.replace(':', '')})")
    lines.append("- [⚖️ Collision Resolver Cheat Sheet](#️-collision-resolver-cheat-sheet)")
    lines.append("- [🔑 Alias Table](#-alias-table)")
    lines.append("- [📊 Priority Order](#-priority-order)")
    lines.append("\n---\n")

    # ─────────────────────────────────────────────────────────────
    # Domain sections
    # ─────────────────────────────────────────────────────────────
    for domain in sorted(domains.keys()):
        lines.append(f"## {domain.capitalize()}\n")
        for key, meta in sorted(domains[domain], key=lambda kv: kv[0]):
            # Prefer metadata-provided symbols
            symbols = list(meta.get("symbols", [])) if meta.get("symbols") else []

            # If empty, reverse-lookup all raw symbols that map to this canonical key
            if not symbols and CANONICAL_OPS:
                symbols = [s for s, k in CANONICAL_OPS.items() if k == key]

            # Deduplicate while preserving order
            seen = set()
            symbols = [s for s in symbols if not (s in seen or seen.add(s))]

            # Collisions
            colliding_keys = set()
            for raw_sym, options in COLLISIONS.items():
                if key in options:
                    colliding_keys.update([o for o in options if o != key])
            sorted_collisions = sorted(colliding_keys)

            symbols_str = ", ".join(symbols) if symbols else "—"
            description = meta.get("description", "_(no description available)_")

            # Section
            lines.append(f"### `{key}`\n")
            lines.append(f"**Symbols:** {symbols_str}\n")
            lines.append(f"**Canonical Key:** `{key}`\n")
            lines.append(f"**Description:** {description}\n")

            if sorted_collisions:
                lines.append("\n**⚠ Collides With:**")
                for alt in sorted_collisions:
                    lines.append(f"- `{alt}`")

            lines.append("\n---\n")

    # ─────────────────────────────────────────────────────────────
    # Global Collision Cheat Sheet
    # ─────────────────────────────────────────────────────────────
    lines.append("## ⚖️ Collision Resolver Cheat Sheet\n")
    lines.append("Only a handful of symbols are ambiguous across domains. These require the collision resolver:\n")
    lines.append("\n| Symbol | Possible Domains | Notes |")
    lines.append("|--------|------------------|-------|")
    for sym, domains in COLLISIONS.items():
        lines.append(f"| {sym} | {', '.join(domains)} | — |")
    lines.append("\nEverything else is **unambiguous** → no resolver needed.\n")

    # ─────────────────────────────────────────────────────────────
    # Alias Table
    # ─────────────────────────────────────────────────────────────
    lines.append("## 🔑 Alias Table\n")
    lines.append("Explicit aliases disambiguate collisions immediately:\n")
    lines.append("\n| Alias | Resolves To |")
    lines.append("|-------|-------------|")
    for alias, target in ALIASES.items():
        lines.append(f"| {alias} | {target} |")
    lines.append("")

    # ─────────────────────────────────────────────────────────────
    # Priority Order
    # ─────────────────────────────────────────────────────────────
    lines.append("## 📊 Priority Order\n")
    lines.append("When no alias is given, the system uses this global order to resolve collisions:\n")
    lines.append("\n`" + " → ".join(PRIORITY_ORDER) + "`\n")
    lines.append("\nExample: bare `↔` resolves to `logic:↔` because *logic outranks quantum*.\n")

    # ─────────────────────────────────────────────────────────────
    # Resolution rules explanation
    # ─────────────────────────────────────────────────────────────
    lines.append("### ⚙️ How Resolution Works\n")
    lines.append("1. **Aliases win first** — e.g., `⊕_q` → `quantum:⊕`, `⊗_p` → `physics:⊗`.\n")
    lines.append("2. **If no alias**, the system checks the global priority order.\n")
    lines.append("3. **If still unresolved**, fall back to the raw operator as-is.\n")
    lines.append("\n👉 You only pay the cost of collision resolution for these special cases. Everything else maps directly.\n")

    return "\n".join(lines)


if __name__ == "__main__":
    output = build_reference()
    out_path = os.path.join("docs", "CodexLang_Instruction", "instruction_reference.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"[✅] Instruction reference generated at {out_path}")