# Symatics Theorems Results

Automated proof snapshot.

| Theorem | Statement | Result |
|---------|-----------|--------|
| T1: Self-Identity | `(A ⋈[φ] A) ↔ A ⇔ φ = 0` | ✅ |
| T2: Self-Annihilation | `(A ⋈[φ] A) ↔ ⊥ ⇔ φ = π` | ✅ |
| T3: Phase-Cancellation | `A ⋈[φ] (A ⋈[−φ] B) ↔ B` | ✅ |
| T4: Associativity | `((A ⋈[φ] B) ⋈[ψ] C) ↔ (A ⋈[φ+ψ] (B ⋈[ψ] C))` | ✅ |
| T5: No-Distributivity | `Distributivity fails for φ ∉ {0, π}` | ✅ |
| T6: No-Fixed-Point | `X = A ⋈[φ] X has no solutions for φ ≠ 0,π` | ✅ |
| T7: Irreducibility | `((A ⋈[φ] B) ∧ C) ≠ ((A ∧ C) ⋈[φ] (B ∧ C)) for φ ≠ 0,π` | ✅ |

---

## Significance

Theorems **T1–T6** establish the basic algebraic behavior of the interference connective `⋈[φ]`, confirming consistency with the axioms (A1–A8).  
However, **Theorem T7 (Irreducibility)** is the breakthrough:

- In classical Boolean logic, distributivity is universal:  
  `(A ∧ (B ∨ C)) ↔ ((A ∧ B) ∨ (A ∧ C))`.  

- In Symatics logic, distributivity **fails for all nontrivial phases** (φ ∉ {0, π}).  
  This demonstrates that `⋈` cannot be reduced to Boolean connectives.  

### Why it matters
- **Proof of beyond-Boolean separation**: `⋈` is not just a fancy notation for ∧/∨, but a genuinely new operator with distinct algebraic laws.  
- **First "irreducibility" theorem**: T7 is the first theorem where the Symatics system proves something that Boolean logic cannot replicate.  
- **Foundation for new expressive power**: This separation indicates that Symatics can capture interference phenomena (e.g. quantum-like superposition) which lie outside the reach of classical propositional logic.  

---