import Init

/-
Symatics Prelude (v1.0)
Lean-correct core for Symatics.
-/

abbrev SProp := Prop

-- Phase is abstract, but supports + and - syntax.
axiom Phase : Type
axiom phase_add : Phase → Phase → Phase
axiom phase_neg : Phase → Phase

instance : HAdd Phase Phase Phase := ⟨phase_add⟩
instance : Neg Phase := ⟨phase_neg⟩

-- Interference connective
axiom sInterf : Phase → SProp → SProp → SProp

-- Notations
notation "⊥" => False
notation A " ⋈[" φ "] " B => sInterf φ A B

-- Common phases
axiom zero_phase : Phase
axiom pi_phase   : Phase

notation A " ⊕ " B => sInterf zero_phase A B
notation A " ⊖ " B => sInterf pi_phase A B
