# 📖 CodexLang Instruction Reference

This document is auto-generated from canonical operator metadata.

> Do not edit manually — run `python backend/modules/codex/instruction_reference_builder.py`.


---

## Table of Contents

- [Control](#control)
  - [control:⟲](#control⟲)
  - [control:⧖](#control⧖)
- [Logic](#logic)
  - [logic:¬](#logic¬)
  - [logic:→](#logic→)
  - [logic:↔](#logic↔)
  - [logic:∧](#logic∧)
  - [logic:∨](#logic∨)
  - [logic:⊕](#logic⊕)
  - [logic:⊗](#logic⊗)
- [Math](#math)
  - [math:∇](#math∇)
- [Photon](#photon)
  - [photon:≈](#photon≈)
  - [photon:⊙](#photon⊙)
- [Physics](#physics)
  - [physics:⊗](#physics⊗)
- [Quantum](#quantum)
  - [quantum:A](#quantumA)
  - [quantum:H](#quantumH)
  - [quantum:bra](#quantumbra)
  - [quantum:commutator_close](#quantumcommutator_close)
  - [quantum:commutator_open](#quantumcommutator_open)
  - [quantum:ket](#quantumket)
  - [quantum:↔](#quantum↔)
  - [quantum:⊕](#quantum⊕)
- [Symatics](#symatics)
  - [symatics:cancel](#symaticscancel)
  - [symatics:damping](#symaticsdamping)
  - [symatics:resonance](#symaticsresonance)
  - [symatics:⊗](#symatics⊗)
- [⚖️ Collision Resolver Cheat Sheet](#️-collision-resolver-cheat-sheet)
- [🔑 Alias Table](#-alias-table)
- [📊 Priority Order](#-priority-order)

---

## Control

### `control:⟲`

**Symbols:** ⟲

**Canonical Key:** `control:⟲`

**Description:** Performs self-mutation or update


---

### `control:⧖`

**Symbols:** ⧖

**Canonical Key:** `control:⧖`

**Description:** Delays execution of a symbol


---

## Logic

### `logic:¬`

**Symbols:** ¬

**Canonical Key:** `logic:¬`

**Description:** Logical negation


---

### `logic:→`

**Symbols:** →

**Canonical Key:** `logic:→`

**Description:** Logical implication


---

### `logic:↔`

**Symbols:** ↔

**Canonical Key:** `logic:↔`

**Description:** Logical equivalence (biconditional)


**⚠ Collides With:**
- `quantum:↔`

---

### `logic:∧`

**Symbols:** ∧

**Canonical Key:** `logic:∧`

**Description:** Logical AND


---

### `logic:∨`

**Symbols:** ∨

**Canonical Key:** `logic:∨`

**Description:** Logical OR


---

### `logic:⊕`

**Symbols:** ⊕

**Canonical Key:** `logic:⊕`

**Description:** Logical XOR


**⚠ Collides With:**
- `quantum:⊕`

---

### `logic:⊗`

**Symbols:** ⊗

**Canonical Key:** `logic:⊗`

**Description:** Multiplies symbolic structures


**⚠ Collides With:**
- `physics:⊗`
- `symatics:⊗`

---

## Math

### `math:∇`

**Symbols:** ∇

**Canonical Key:** `math:∇`

**Description:** Gradient / divergence operator


---

## Photon

### `photon:≈`

**Symbols:** ≈, ~

**Canonical Key:** `photon:≈`

**Description:** Photon wave equivalence


---

### `photon:⊙`

**Symbols:** ⊙

**Canonical Key:** `photon:⊙`

**Description:** Photon absorption/emission operator


---

## Physics

### `physics:⊗`

**Symbols:** ⊗_p

**Canonical Key:** `physics:⊗`

**Description:** Physical tensor product


**⚠ Collides With:**
- `logic:⊗`
- `symatics:⊗`

---

## Quantum

### `quantum:A`

**Symbols:** Â

**Canonical Key:** `quantum:A`

**Description:** Quantum operator Â


---

### `quantum:H`

**Symbols:** H

**Canonical Key:** `quantum:H`

**Description:** Hadamard gate


---

### `quantum:bra`

**Symbols:** ⟨ψ|

**Canonical Key:** `quantum:bra`

**Description:** Quantum bra state


---

### `quantum:commutator_close`

**Symbols:** ]

**Canonical Key:** `quantum:commutator_close`

**Description:** Quantum commutator end


---

### `quantum:commutator_open`

**Symbols:** [

**Canonical Key:** `quantum:commutator_open`

**Description:** Quantum commutator start


---

### `quantum:ket`

**Symbols:** ψ⟩

**Canonical Key:** `quantum:ket`

**Description:** Quantum ket state


---

### `quantum:↔`

**Symbols:** ↔

**Canonical Key:** `quantum:↔`

**Description:** Quantum bidirectional equivalence


**⚠ Collides With:**
- `logic:↔`

---

### `quantum:⊕`

**Symbols:** ⊕_q

**Canonical Key:** `quantum:⊕`

**Description:** Quantum XOR-like operation


**⚠ Collides With:**
- `logic:⊕`

---

## Symatics

### `symatics:cancel`

**Symbols:** cancel

**Canonical Key:** `symatics:cancel`

**Description:** Cancels a vibration or resonance


---

### `symatics:damping`

**Symbols:** damping

**Canonical Key:** `symatics:damping`

**Description:** Applies damping factor


---

### `symatics:resonance`

**Symbols:** resonance

**Canonical Key:** `symatics:resonance`

**Description:** Triggers resonance effect


---

### `symatics:⊗`

**Symbols:** ⊗_s

**Canonical Key:** `symatics:⊗`

**Description:** Symatics tensor product


**⚠ Collides With:**
- `logic:⊗`
- `physics:⊗`

---

## ⚖️ Collision Resolver Cheat Sheet

Only a handful of symbols are ambiguous across domains. These require the collision resolver:


| Symbol | Possible Domains | Notes |
|--------|------------------|-------|
| ⊗      | logic, physics, symatics | Tensor / product ambiguity |
| ⊕      | logic, quantum           | XOR-like vs quantum addition |
| ↔      | logic, quantum           | Equivalence vs quantum bidirection |
| ∇      | math (reserved)          | May overlap in future domains |
| ≈ / ~  | photon                   | Aliased forms of wave equivalence |

Everything else (¬, ∧, ∨, H, ⟨ψ|, ψ⟩, cancel, resonance, etc.) is **unambiguous** → no resolver needed.

## 🔑 Alias Table

Explicit aliases disambiguate collisions immediately:


| Alias | Resolves To |
|-------|-------------|
| ⊕_q | quantum:⊕ |
| ⊗_p | physics:⊗ |
| ⊗_s | symatics:⊗ |
| ~ | photon:≈ |

## 📊 Priority Order

When no alias is given, the system uses this global order to resolve collisions:


`logic → math → physics → quantum → symatics → photon → control`


Example: bare `↔` resolves to `logic:↔` because *logic outranks quantum*.

### ⚙️ How Resolution Works

1. **Aliases win first** — e.g., `⊕_q` → `quantum:⊕`, `⊗_p` → `physics:⊗`.

2. **If no alias**, the system checks the global priority order.

3. **If still unresolved**, fall back to the raw operator as-is.


👉 You only pay the cost of collision resolution for these special cases. Everything else maps directly.
