📄 docs/rfc/separation.md (Boolean separation note)

# Separation of Symatics vs Boolean Logic

Status: Draft
Author: Tessaris
Date: 2025-09-25

---

## 1. Motivation
To establish Symatics as a distinct algebra, we must show it cannot be reduced to Boolean logic (`∧, ∨, ¬`) except in trivial cases.

---

## 2. Boundary Cases
- `(A ⋈[0] B)` behaves like `A ⊕ B` (similar to `∨`).
- `(A ⋈[π] A)` annihilates to ⊥ (similar to contradiction).

Thus, **Boolean behavior appears only at φ = 0 or π.**

---

## 3. Non-reducibility
For φ ≠ {0, π}, no Boolean connective captures interference:

- Example: `(A ⋈[φ] B)` produces phase-sensitive outcomes.
- Boolean connectives are **phase-insensitive**.

Therefore, there is no homomorphism `h : Symatics → Boolean` preserving ⋈ semantics.

---

## 4. Theorem Sketch
**Theorem:** ∄ Boolean connective `⊗` s.t.  
`∀ A,B,φ. (A ⋈[φ] B) ≡ (A ⊗ B)`  
except at φ = 0, π.

*Proof outline:* Suppose such `⊗` exists. Then for φ ≠ 0,π, truth-value of `A ⋈[φ] B` must vary with φ. But all Boolean connectives are invariant under phase. Contradiction.

---

## 5. Consequence
- Symatics strictly extends Boolean logic.
- Lean injection + rewriter confirm this via test `no_distrib` and phase laws.
- This separation justifies publishing Symatics as a novel algebra, not a variant of propositional logic.

# Symatics Separation Note  
*(Irreducibility of ⋈ vs Boolean Connectives)*

---

## Context

Classical Boolean logic is governed by universal algebraic laws:  
- Commutativity, associativity, idempotence, distributivity.  
- Every connective (∧, ∨) can be expressed in terms of others.  

The Symatics interference connective `⋈[φ]`, parameterized by a phase φ, was introduced to model *interference-style composition* of propositions.  
Axioms (A1–A8) capture its expected algebraic behavior (identity, annihilation, phase inversion, cancellation).

---

## Theorem T7 — Irreducibility

**Statement:**  
For φ ∉ {0, π},  

((A ⋈[φ] B) ∧ C) ≠ ((A ∧ C) ⋈[φ] (B ∧ C))

**Interpretation:**  
Distributivity fails for interference. Unlike Boolean logic, `⋈` does **not** distribute over conjunction.  
This irreducibility theorem proves that `⋈` cannot be defined in terms of ∧/∨ alone.

---

## Significance

- **Beyond-Boolean separation:**  
  Theorem T7 shows that Symatics logic diverges fundamentally from Boolean algebra.  
  Boolean logic enforces distributivity globally; Symatics only preserves it in trivial phase cases (φ = 0, π).

- **Expressive novelty:**  
  `⋈` introduces algebraic behavior unavailable to ∧/∨.  
  This opens the door to modeling phase-sensitive interactions (constructive vs destructive interference).

- **First separation theorem:**  
  T7 is the first rigorously tested theorem that places Symatics logic *outside* the Boolean clone of connectives.  
  In algebraic logic terms, `⋈` belongs to a strictly larger operator class.

---

## Research Outlook

- **Formal algebraic semantics:**  
  Build a phase-semantic model to characterize the truth conditions of `⋈` beyond Boolean valuations.  

- **Computational implications:**  
  Benchmark results suggest normalization shrinks complex ⋈-chains, unlike Boolean normal forms.  
  This could offer practical advantages in symbolic reasoning.

- **Future theorems:**  
  T7 is a first step; the next stage is to explore distributive-like patterns for constrained φ values (e.g. rational multiples of π) and their relationship to quantum logics.

---

📌 **Summary:**  
Theorem T7 establishes *irreducibility*: the Symatics interference connective `⋈[φ]` cannot be reduced to classical ∧/∨.  
This separation is the cornerstone of Symatics’ claim to novelty as a logical system.

