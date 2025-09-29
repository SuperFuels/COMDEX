# 📖 CodexLang Instruction Reference

This document is auto-generated from instruction_registry.yaml.

> Do not edit manually — run `python docs/CodexLang_Instruction/instruction_reference_builder.py`.


---

## Table of Contents

- [Photon](#photon)
  - [photon](#photon)
- [⚖️ Collision Resolver Cheat Sheet](#️-collision-resolver-cheat-sheet)
- [🔑 Alias Table](#-alias-table)
- [📊 Priority Order](#-priority-order)

---

## Photon

### `photon`

**Symbols:** —

**Canonical Key:** `photon`

**Description:** _(no description available)_


---

## ⚖️ Collision Resolver Cheat Sheet

Only a handful of symbols are ambiguous across domains. These require the collision resolver:


| Symbol | Possible Domains | Notes |
|--------|------------------|-------|

Everything else is **unambiguous** → no resolver needed.

## 🔑 Alias Table

Explicit aliases disambiguate collisions immediately:


| Alias | Resolves To |
|-------|-------------|

## 📊 Priority Order

When no alias is given, the system uses this global order to resolve collisions:


``


Example: bare `↔` resolves to `logic:↔` because *logic outranks quantum*.

### ⚙️ How Resolution Works

1. **Aliases win first** — e.g., `⊕_q` → `quantum:⊕`, `⊗_p` → `physics:⊗`.

2. **If no alias**, the system checks the global priority order.

3. **If still unresolved**, fall back to the raw operator as-is.


👉 You only pay the cost of collision resolution for these special cases. Everything else maps directly.
