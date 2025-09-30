# 📖 CodexLang Instruction Reference

This document is auto-generated from instruction_registry.yaml.

> Do not edit manually — run `python docs/CodexLang_Instruction/instruction_reference_builder.py`.


---

## Table of Contents

- [Logic](#logic)
  - [logic:¬](#logic¬)
  - [logic:⊕](#logic⊕)
  - [logic:⊗](#logic⊗)
- [Photon](#photon)
  - [photon:¬](#photon¬)
  - [photon:↔](#photon↔)
  - [photon:∅](#photon∅)
  - [photon:∇](#photon∇)
  - [photon:⊕](#photon⊕)
  - [photon:⊖](#photon⊖)
  - [photon:⊗](#photon⊗)
  - [photon:★](#photon★)
- [Quantum](#quantum)
  - [quantum:↔](#quantum↔)
  - [quantum:⊕](#quantum⊕)
- [Symatics](#symatics)
  - [symatics:cancel](#symaticscancel)
  - [symatics:resonance](#symaticsresonance)
- [⚖️ Collision Resolver Cheat Sheet](#️-collision-resolver-cheat-sheet)
- [🔑 Alias Table](#-alias-table)
- [📊 Priority Order](#-priority-order)


---

## Logic

### `logic:¬`

**Symbols:** ¬

**Canonical Key:** `logic:¬`

**Description:** Logical negation


---

### `logic:⊕`

**Symbols:** ⊕

**Canonical Key:** `logic:⊕`

**Description:** Logical XOR


---

### `logic:⊗`

**Symbols:** ⊗

**Canonical Key:** `logic:⊗`

**Description:** Multiplicative conjunction


---

## Photon

### `photon:¬`

**Symbols:** ¬

**Canonical Key:** `photon:¬`

**Description:** Photon negation (P6)


---

### `photon:↔`

**Symbols:** ↔

**Canonical Key:** `photon:↔`

**Description:** Photon entanglement (P3)


---

### `photon:∅`

**Symbols:** ∅

**Canonical Key:** `photon:∅`

**Description:** Canonical empty state (EMPTY)


---

### `photon:∇`

**Symbols:** ∇

**Canonical Key:** `photon:∇`

**Description:** Collapse operator (P7)


---

### `photon:⊕`

**Symbols:** ⊕

**Canonical Key:** `photon:⊕`

**Description:** Photon superposition (P2)


---

### `photon:⊖`

**Symbols:** ⊖

**Canonical Key:** `photon:⊖`

**Description:** Photon cancellation (P5)


---

### `photon:⊗`

**Symbols:** ⊗

**Canonical Key:** `photon:⊗`

**Description:** Photon resonance / amplification (P4)


---

### `photon:★`

**Symbols:** ★

**Canonical Key:** `photon:★`

**Description:** Projection with SQI drift score (P8)


---

## Quantum

### `quantum:↔`

**Symbols:** ↔

**Canonical Key:** `quantum:↔`

**Description:** Quantum entanglement / bidirectional equivalence


---

### `quantum:⊕`

**Symbols:** ⊕

**Canonical Key:** `quantum:⊕`

**Description:** Quantum XOR-like operation


---

## Symatics

### `symatics:cancel`

**Symbols:** cancel

**Canonical Key:** `symatics:cancel`

**Description:** Cancels a vibration or resonance


---

### `symatics:resonance`

**Symbols:** resonance

**Canonical Key:** `symatics:resonance`

**Description:** Triggers resonance effect


---

## ⚖️ Collision Resolver Cheat Sheet

Only a handful of symbols are ambiguous across domains. These require the collision resolver:


| Symbol | Possible Canonicals |
|--------|----------------------|
| ⊗ | logic:⊗, physics:⊗, symatics:⊗ |
| ⊕ | logic:⊕, quantum:⊕ |
| ↔ | logic:↔, quantum:↔ |

## 🔑 Alias Table


| Alias | Resolves To |
|-------|-------------|
| ⊕_q | quantum:⊕ |
| ⊗_p | physics:⊗ |
| ⊗_s | symatics:⊗ |
| ~ | photon:≈ |

## 📊 Priority Order


`logic → math → physics → quantum → symatics → photon → control`


Example: bare `↔` resolves to `logic:↔` because *logic outranks quantum*.
