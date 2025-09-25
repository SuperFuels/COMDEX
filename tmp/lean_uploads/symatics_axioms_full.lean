import ./symatics_prelude


axiom comm_phi : (A ⋈[φ] B) ↔ (B ⋈[-φ] A)

axiom self_pi_bot : (A ⋈[π] A) ↔ ⊥

axiom self_zero_id : (A ⋈[0] A) ↔ A

axiom non_idem : ∀ φ, φ ≠ 0 ∧ φ ≠ π → (A ⋈[φ] A) ≠ A

axiom neutral_phi : (A ⋈[φ] ⊥) ↔ A

axiom no_distrib : ¬(((A ⋈[φ] B) ∧ C) ↔ ((A ∧ C) ⋈[φ] (B ∧ C)))

theorem no_distrib_formal : ((A ⋈[φ] B) ∧ C) ≠ ((A ∧ C) ⋈[φ] (B ∧ C))

axiom assoc_phase : (A ⋈[φ] B) ⋈[ψ] C ↔ A ⋈[φ+ψ] (B ⋈[ψ] C)

axiom inv_phase : A ⋈[φ] (A ⋈[-φ] B) ↔ B

axiom fuse_phase_zero : (A ⋈[0] B) ↔ (A ⊕ B)

axiom fuse_phase_pi : (A ⋈[π] B) ↔ (A ⊖ B)
