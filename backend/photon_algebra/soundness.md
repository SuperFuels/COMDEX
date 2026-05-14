# Photon Algebra Soundness (Optional Reference Semantics)

This document provides a simple reference semantics for a PA-core fragment and argues that the normalization rules are sound in that model.

Goal: lend extra credibility by showing that core rewrite steps preserve meaning under an explicit interpretation.

---

## 1) Scope of the soundness model

We model a **core fragment**:
- atoms
- `⊕` (sum)
- `⊗` (product)
- `∅` (empty)

Other operators (`¬`, `⊖`, `↔`, `★`, `∇`) can be added later with separate semantics; they are not required for the core termination/canonicalization story.

---

## 2) Semantics: sets of products (DNF-like)

Let `Atom` be the set of atomic symbols.

Define a “monomial” as a finite set of atoms (order irrelevant):
- e.g. `{a,b}` represents `a ⊗ b`.

Define the semantic domain:
- `Sem = P(P_f(Atom))` = set of finite monomials (a set of sets)

Interpretation `⟦e⟧ : Expr -> Sem`:

- `⟦a⟧ = { {a} }`
- `⟦∅⟧ = ∅`

- `⟦x ⊕ y⟧ = ⟦x⟧ ∪ ⟦y⟧`
- `⟦x ⊗ y⟧ = { m ∪ n | m ∈ ⟦x⟧, n ∈ ⟦y⟧ }`

This is the canonical “sum-of-products” semantics: `⊕` is union, `⊗` is set-product (with union on monomials).

---

## 3) Soundness of core rewrite steps

Each rewrite step used by normalization must preserve `⟦·⟧`.

Examples:

### 3.1 Commutativity / associativity (⊕, ⊗)
Follows from commutativity/associativity of `∪` and `∪` on sets.

### 3.2 Idempotence (⊕)
`x ⊕ x -> x` since `A ∪ A = A`.

### 3.3 Identity / annihilator
- `x ⊕ ∅ -> x` since `A ∪ ∅ = A`
- `x ⊗ ∅ -> ∅` since no monomials exist on the right to pair with.

### 3.4 Distribution (directed)
`x ⊗ (y ⊕ z) -> (x ⊗ y) ⊕ (x ⊗ z)` holds because set-product distributes over union.

### 3.5 Absorption (if implemented)
`x ⊕ (x ⊗ y) -> x` holds if your `⊗` is interpreted as “superset” monomials and your `⊕` includes an absorption reduction policy.
(If you enforce absorption as a rewrite, state the exact condition used in the normalizer and prove it matches the chosen semantics.)

---

## 4) What this buys you

- A clear “meaning” for the sum/product fragment.
- A simple argument that normalization is semantics-preserving.
- A clean explanation of why the chosen normal form is canonical (DNF-like).

---

## 5) Practical verification (optional)

You can implement `interp(e)` in tests and property-check:
- `interp(e) == interp(normalize(e))` for many random `e`.

This is not required for termination, but it is a high-credibility reinforcement.