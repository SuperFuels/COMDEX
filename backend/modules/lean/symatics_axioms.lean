import Tessaris.Symatics.Prelude

/-
Symatics Axioms (v1.0)
Schema-level laws for ⋈[φ].
-/

namespace SymaticsAxioms

variable {A B C : SProp}
variable {φ ψ : Phase}

axiom comm_phi : (A ⋈[φ] B) ↔ (B ⋈[-φ] A)

axiom self_pi   : (A ⋈[pi_phase] A) ↔ ⊥
axiom self_zero : (A ⋈[zero_phase] A) ↔ A
axiom non_idem  : ∀ (φ' : Phase), φ' ≠ zero_phase ∧ φ' ≠ pi_phase → (A ⋈[φ'] A) ≠ A

axiom neutral_phi : (A ⋈[φ] ⊥) ↔ A

axiom no_distrib :
  ¬(((A ⋈[φ] B) ∧ C) ↔ ((A ∧ C) ⋈[φ] (B ∧ C)))

axiom no_distrib_formal :
  ∀ (φ' : Phase), φ' ≠ zero_phase ∧ φ' ≠ pi_phase →
    ((A ⋈[φ'] B) ∧ C) ≠ ((A ∧ C) ⋈[φ'] (B ∧ C))

axiom assoc_phase : ((A ⋈[φ] B) ⋈[ψ] C) ↔ (A ⋈[φ + ψ] (B ⋈[ψ] C))
axiom inv_phase   : (A ⋈[φ] (A ⋈[-φ] B)) ↔ B

axiom fuse_phase_zero : (A ⋈[zero_phase] B) ↔ (A ⊕ B)
axiom fuse_phase_pi   : (A ⋈[pi_phase] B) ↔ (A ⊖ B)

end SymaticsAxioms