import ./symatics_prelude

/-
Symatics Axioms (v1.0)
----------------------
Schema-level laws for the interference connective ⋈[φ].
These mirror the Python rewriter + Codex LAW_REGISTRY.
-/

variables {A B C : SProp} {φ ψ : Phase}

-- Commutativity with phase inversion
axiom comm_phi : (A ⋈[φ] B) ↔ (B ⋈[−φ] A)

-- Special self-interference cases
axiom self_pi   : (A ⋈[pi_phase] A) ↔ ⊥
axiom self_zero : (A ⋈[zero_phase] A) ↔ A
axiom non_idem  : ∀ φ, φ ≠ zero_phase ∧ φ ≠ pi_phase → (A ⋈[φ] A) ≠ A

-- Neutrality of ⊥
axiom neutral_phi : (A ⋈[φ] ⊥) ↔ A

-- Explicit failure of distributivity
axiom no_distrib :
  ¬(((A ⋈[φ] B) ∧ C) ↔ ((A ∧ C) ⋈[φ] (B ∧ C)))

-- Formal irreducibility (Theorem 7)
axiom no_distrib_formal :
  ∀ (φ : Phase), φ ≠ zero_phase ∧ φ ≠ pi_phase →
    ((A ⋈[φ] B) ∧ C) ≠ ((A ∧ C) ⋈[φ] (B ∧ C))

-- Phase composition axioms
axiom assoc_phase : (A ⋈[φ] B) ⋈[ψ] C ↔ A ⋈[φ+ψ] (B ⋈[ψ] C)
axiom inv_phase   : A ⋈[φ] (A ⋈[−φ] B) ↔ B

-- Canonical phase interference laws
axiom fuse_phase_zero : (A ⋈[zero_phase] B) ↔ (A ⊕ B)
axiom fuse_phase_pi   : (A ⋈[pi_phase] B) ↔ (A ⊖ B)