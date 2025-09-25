import ./symatics_prelude

-- Commutativity with phase inversion
axiom comm_phi : (A ⋈[φ] B) ↔ (B ⋈[-φ] A)

-- Special self-interference cases
axiom self_pi_bot : (A ⋈[π] A) ↔ ⊥
axiom self_zero_id : (A ⋈[0] A) ↔ A
axiom non_idem : ∀ φ, φ ≠ 0 ∧ φ ≠ π → (A ⋈[φ] A) ≠ A

-- Neutrality of ⊥
axiom neutral_phi : (A ⋈[φ] ⊥) ↔ A

-- Explicit failure of distributivity
axiom no_distrib : ¬(((A ⋈[φ] B) ∧ C) ↔ ((A ∧ C) ⋈[φ] (B ∧ C)))

-- Phase composition axioms
axiom assoc_phase : (A ⋈[φ] B) ⋈[ψ] C ↔ A ⋈[φ+ψ] (B ⋈[ψ] C)
axiom inv_phase : A ⋈[φ] (A ⋈[-φ] B) ↔ B

-- A7 (constructive interference)
axiom fuse_phase_zero : (A ⋈[0] B) ↔ (A ⊕ B)

-- A8 (destructive interference)
axiom fuse_phase_pi : (A ⋈[π] B) ↔ (A ⊖ B)
