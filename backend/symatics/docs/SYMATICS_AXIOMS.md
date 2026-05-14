# Symatics Axioms v0.1

**Core idea**: The atomic unit is a **signature** σ capturing stable invariants of a wave/glyph,
not a scalar “1”. Computation manipulates σ via physical-like operators.

## Primitives
- σ ∈ Σ: signature (amplitude envelope, carrier f, phase φ, polarization P, mode m, OAM ℓ, etc.)
- Operators:
  - Superposition: σ₁ ⊕ σ₂
  - Entanglement: σ₁ ↔ σ₂
  - Resonance: σ₁ ⟲ σ₂ (energy coupling / matched response)
  - Measurement: μ(σ) → ˆσ (canonical glyph/unit)
  - Projection: πᵣ(σ) (restrict to subspace r; e.g., polarization)
  - Fold: 𝔽ᵣ(σ) (reduce structure by rule r)
  - Expand: 𝔼ᵣ(σ) (unfold/introduce structure by rule r)
  - Transport: τₕ(σ) (propagate through medium h)
  - Interference: σ₁ ⊖ σ₂ (destructive/constructive mix)

## Algebraic Laws (Abridged)
1. ⊕ is associative up to normalization: (σ⊕τ)⊕ρ ≈ σ⊕(τ⊕ρ)
2. ⊕ is commutative: σ⊕τ ≈ τ⊕σ
3. Identity for ⊕: ∃ 𝟘 s.t. σ⊕𝟘 ≈ σ
4. ↔ distributes over ⊕: (σ⊕τ)↔ρ ≈ (σ↔ρ) ⊕ (τ↔ρ)
5. μ is idempotent + canonicalizing: μ(μ(σ)) ≡ μ(σ)
6. μ is stable under isometries U: μ(Uσ) ≡ μ(σ)
7. Resonance selects matched components: (σ⟲τ) ≈ π_match(σ⊕τ)
8. Transport respects composition: τₕ₂(τₕ₁(σ)) ≡ τ_{h₂∘h₁}(σ)
9. Projection-Measurement commute on invariant subspaces: μ(πᵣ(σ)) ≡ μ(σ) if σ∈r
10. Equivalence (≃) is defined by metric d(σ,τ) ≤ ε on invariants.

All laws are implemented as rewrite schemata + semantic checks.