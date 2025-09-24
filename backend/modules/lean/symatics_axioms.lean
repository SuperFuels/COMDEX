import ./symatics_prelude

-- New interference connective axioms (schema instances)

axiom comm_phi      : (A ⋈[φ] B) ↔ (B ⋈[−φ] A)
axiom self_pi_bot   : (A ⋈[π] A) ↔ ⊥
axiom self_zero_id  : (A ⋈[0] A) ↔ A
axiom non_idem      : ∀ φ, φ ≠ 0 ∧ φ ≠ π → (A ⋈[φ] A) ≠ A
axiom neutral_phi   : (A ⋈[φ] ⊥) ↔ A
axiom no_distrib    : ¬(((A ⋈[φ] B) ∧ C) ↔ ((A ∧ C) ⋈[φ] (B ∧ C)))