import Init

/-
Symatics Prelude (v1.0) — ASCII-safe.
-/

noncomputable section

abbrev SProp := Prop

-- Abstract phase space
axiom Phase : Type
axiom zero_phase : Phase
axiom pi_phase   : Phase

axiom phase_add : Phase -> Phase -> Phase
axiom phase_neg : Phase -> Phase

-- Mark these noncomputable so Lake codegen doesn’t choke on axioms/constants.
noncomputable instance : HAdd Phase Phase Phase where
  hAdd := phase_add

noncomputable instance : Neg Phase where
  neg := phase_neg

-- Interference connective
axiom sInterf : Phase -> SProp -> SProp -> SProp

-- Notations (ASCII + Unicode)
notation "BOT" => False
notation:70 A " sInterf[" phi "] " B => sInterf phi A B

notation "⊥" => False
notation:70 A " ⋈[" phi "] " B => sInterf phi A B

notation:70 A " ⊕ " B => sInterf zero_phase A B
notation:70 A " ⊖ " B => sInterf pi_phase A B

end
