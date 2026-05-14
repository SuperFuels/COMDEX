import PhotonAlgebra.Basic
import PhotonAlgebra.Normalizer

namespace PhotonAlgebra

open Expr

/-- Normal-form equality: two expressions are equivalent iff their NFs are equal. -/
def EqNF (a b : Expr) : Prop := normalize a = normalize b

@[simp] theorem EqNF.refl (a : Expr) : EqNF a a := rfl
theorem EqNF.symm {a b : Expr} : EqNF a b -> EqNF b a := by intro h; simpa [EqNF] using h.symm
theorem EqNF.trans {a b c : Expr} : EqNF a b -> EqNF b c -> EqNF a c := by
  intro h1 h2; exact Eq.trans h1 h2

/-
  You will prove these by unfolding your `normalize` pipeline + using
  your internal lemmas about:
    - flattening
    - distribution
    - dedup/idempotence
    - absorption
  The key: DO NOT use `rfl` for non-definitional equalities.
-/

/-- Idempotence of normalization (Phase 1). -/
theorem normalize_idem (e : Expr) : normalize (normalize e) = normalize e := by
  -- If your Normalizer already has this lemma, just `simpa`:
  -- simpa using Normalizer.normalize_idem e
  -- Otherwise prove by: unfold normalize; show fixpoint; use your “already NF” lemma.
  simpa using Normalizer.normalize_idem e

/-- NF shape predicate: no `⊕` occurs directly under any `⊗`. -/
inductive NoPlusUnderTimes : Expr -> Prop
| atom (s) : NoPlusUnderTimes (atom s)
| top : NoPlusUnderTimes ⊤
| bot : NoPlusUnderTimes ⊥
| emp : NoPlusUnderTimes ∅
| neg {e} : NoPlusUnderTimes e -> NoPlusUnderTimes (¬ e)
| star {e} : NoPlusUnderTimes e -> NoPlusUnderTimes (★ e)
| plus {xs} : (∀ x ∈ xs, NoPlusUnderTimes x) -> NoPlusUnderTimes (plus xs)
| times {xs} :
    (∀ x ∈ xs, NoPlusUnderTimes x) ->
    (∀ x ∈ xs, ¬ ∃ ys, x = plus ys) ->
    NoPlusUnderTimes (times xs)
| ent {xs} : (∀ x ∈ xs, NoPlusUnderTimes x) -> NoPlusUnderTimes (entangle xs)
| diff {a b} : NoPlusUnderTimes a -> NoPlusUnderTimes b -> NoPlusUnderTimes (a ⊖ b)

theorem normalize_nf_invariant (e : Expr) : NoPlusUnderTimes (normalize e) := by
  -- This should follow from your distribution step inside normalize.
  simpa using Normalizer.normalize_nf_invariant e

/-- T: Distributivity in NF (the one your smoke-test demonstrates). -/
theorem T_dist (a b c : Expr) :
  EqNF (a ⊗ (b ⊕ c)) ((a ⊗ b) ⊕ (a ⊗ c)) := by
  -- This is the “correct” statement: equality *after normalization*.
  -- Prove by unfolding EqNF and using the distribution lemma of normalize.
  simp [EqNF, Normalizer.normalize_dist]

/-- Add the rest of your theorem set the same way. -/
theorem T_comm_add (a b : Expr) : EqNF (a ⊕ b) (b ⊕ a) := by
  simp [EqNF, Normalizer.normalize_plus_comm]

theorem T_assoc_add (a b c : Expr) : EqNF ((a ⊕ b) ⊕ c) (a ⊕ (b ⊕ c)) := by
  simp [EqNF, Normalizer.normalize_plus_assoc]

theorem T_absorb (a b : Expr) : EqNF (a ⊕ (a ⊗ b)) a := by
  simp [EqNF, Normalizer.normalize_absorb]

end PhotonAlgebra