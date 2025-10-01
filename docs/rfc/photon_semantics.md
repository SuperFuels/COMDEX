# Photon Semantics — Meta-Operators Extension (E3)

In addition to the core operators (⊕, ⊗, ⊖, ↔, ¬, ★, ∅),  
we introduce four **meta-level operators/constants**.  
These are **inert** in Phase 1 — no rewrite rules are applied yet —  
but they establish the semantic ground for later reasoning.

---

## ⊤ (Top Element)
- **Definition:** Universal truth element.
- **Intuition:** Always true / always present state.
- **Analogy:** Boolean `True`, logical tautology.
- **Normalization:** Pass-through (no simplification rules yet).

---

## ⊥ (Bottom Element)
- **Definition:** Contradiction / falsity.
- **Intuition:** Impossible or inconsistent state.
- **Analogy:** Boolean `False`, logical contradiction.
- **Normalization:** Pass-through (no simplification rules yet).

---

## a ≈ b (Similarity)
- **Definition:** Binary similarity relation between photon states.
- **Intuition:** Expresses that two states are "similar" in some abstract space.
- **Analogy:** Fuzzy equivalence, approximate equality.
- **Notes:** Not algebraic; semantics TBD (may use SQI scoring later).
- **Normalization:** Pass-through.

---

## a ⊂ b (Containment)
- **Definition:** Binary containment relation (subset or inclusion).
- **Intuition:** `a` is structurally included in `b`.
- **Analogy:** Set-theoretic subset ⊂, or type-theoretic subtyping.
- **Notes:** Semantics TBD (may connect to partial ordering).
- **Normalization:** Pass-through.

---

## Summary
- These operators/constants exist **only structurally** in Phase 1.
- They pretty-print and parse correctly, but are not rewritten.
- Future work (Phase 2) will add semantics:
  - ⊤/⊥ simplifications,
  - ≈ as approximate equivalence,
  - ⊂ as partial ordering/subsumption.

---

# Photon Algebra Semantics (Phase 1)

Successor to Boolean Algebra. Defines foundational axioms (P1–P8), collapse,
and normal forms.

Boolean {0,1} ⊂ PhotonStates

Symatics ↔ Codex ↔ Photon are unified here.

---

## Core Operators

- **⊕ (Superposition)**  
  Combine multiple states into a nondeterministic set.  
  Normalization flattens nested ⊕ and removes ∅.  

- **⊗ (Fusion / Amplification)**  
  Binary operator. Represents resonance/amplification of states.  

- **⊖ (Cancellation)**  
  Binary, non-commutative.  
  If both operands are identical, reduces to ∅.  

- **↔ (Entanglement)**  
  Binary, lowest precedence. Groups multiple states into symmetric entanglement.  

- **¬ (Negation)**  
  Unary. Double negation eliminates.  

- **★ (Projection)**  
  Unary. Can be symbolic (★a) or scored (★a = SQI drift).  

- **∅ (Empty state)**  
  Canonical neutral element.  

---

## Meta-Operators (E2 Extension)

These are **inert for now** — no rewrites or algebraic semantics are attached.
They exist structurally and normalize pass-through.

- **≈ (Similarity)**  
  Binary operator: `a ≈ b`.  
  Represents semantic similarity / fuzzy relation.  
  Currently inert, only structural.

- **⊂ (Containment)**  
  Binary operator: `a ⊂ b`.  
  Represents structural inclusion / subset relation.  
  Currently inert, only structural.

- **⊤ (Top element / universal truth)**  
  Constant: always true, universal element.  
  Analogous to Boolean `1`.

- **⊥ (Bottom element / contradiction)**  
  Constant: contradiction, impossible state.  
  Analogous to Boolean `0`.

---

## Notes

- Pretty-printer / parser round-trips all of these.  
- `normalize()` is pass-through for meta-ops until we decide rewrite rules.  
- Future work:  
  - **≈** → fuzzy similarity semantics (metric, cosine, etc).  
  - **⊂** → subset ordering, monotonic rewrites.  
  - **⊤/⊥** → absorbent / identity rules for operators.  