📄 docs/rfc/semantics.md (minimal semantic model sketch)

# Symatics Semantics (Sketch)

Status: Draft
Author: Tessaris
Date: 2025-09-25

---

## 1. Goal
Provide a minimal formal semantics for the interference connective `⋈[φ]` and related operators, sufficient for mechanized proof validation.

---

## 2. Domain
- Let **Σ** = set of atomic signatures (A, B, …).
- Each atom carries an **amplitude** `α ∈ ℝ⁺` and a **phase** `φ ∈ [0, 2π)`.

We model an atomic wave as a tuple:

Wave = (σ, α, φ)   where σ ∈ Σ

---

## 3. Interference Connective (⋈[φ])
Definition:

(A ⋈[φ] B)(t) = α_A e^{iφ_A} + α_B e^{i(φ_B + φ)}

- `φ` is the **relative phase shift**.
- Results collapse via measurement (`∇`) into either constructive (`⊕`) or destructive (`⊖`) forms.

---

## 4. Canonical Laws
- **Self-zero**: `(A ⋈[0] A) → A` (constructive alignment).
- **Self-π**: `(A ⋈[π] A) → ⊥` (destructive cancellation).
- **Commutativity**: `(A ⋈[φ] B) ↔ (B ⋈[-φ] A)`.
- **Phase addition**: `((A ⋈[φ] B) ⋈[ψ] C) ↔ A ⋈[φ+ψ] (B ⋈[ψ] C)`.

---

## 5. Semantics of Collapse
The collapse operator maps a wave expression into a probability distribution:

∇ : Expr → Dist(Signatures)

s.t. normalization holds: `∑ P(σ) = 1`.

---

## 6. Relation to Classical Logic
- Classical `∧, ∨` emerge only at boundary cases (`φ = 0, π`).
- For `φ ∉ {0, π}`, no Boolean connective reproduces ⋈’s behavior.
- ⇒ Symatics is strictly **non-reducible** to Boolean algebra.

