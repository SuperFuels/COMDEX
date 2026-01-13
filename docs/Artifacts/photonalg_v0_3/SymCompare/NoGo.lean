import Mathlib.Data.Complex.Trigonometric
import Mathlib.Analysis.SpecialFunctions.Trigonometric.Basic
import Mathlib.Tactic

namespace SymCompare

open Real Complex

/--
Canonical Symatics-style interference connective (scalar form):

Interf φ A B := A + cis(φ) * B

This matches the placeholder used in the sym_compare_v1 Python runners:
  Interf_phi(A,B) := A + exp(i*phi) B
since cis φ = cos φ + i sin φ = exp(iφ).
-/
def Interf (φ : ℝ) (A B : ℂ) : ℂ := A + (Complex.cis φ) * B

/-- Abstract φ-invariance lemma: if h(Interf φ A B) is defined via a φ-free op on h(A),h(B),
then the image is φ-invariant. -/
theorem n1_image_phi_invariant
    {α β : Type} (Interfα : ℝ → α → α → α) (h : α → β) (op : β → β → β)
    (hom : ∀ φ A B, h (Interfα φ A B) = op (h A) (h B)) :
    ∀ φ₁ φ₂ A B, h (Interfα φ₁ A B) = h (Interfα φ₂ A B) := by
  intro φ₁ φ₂ A B
  -- both sides rewrite to op (h A) (h B)
  simpa [hom φ₁ A B, hom φ₂ A B]

/-- Concrete fact: cis(pi/3) ≠ cis(pi/2) (real parts differ: 1/2 vs 0). -/
theorem cis_pi_div_three_ne_cis_pi_div_two :
    Complex.cis (Real.pi / 3) ≠ Complex.cis (Real.pi / 2) := by
  intro h
  have hre : Real.cos (Real.pi / 3) = Real.cos (Real.pi / 2) := by
    -- take real parts of both sides
    simpa using congrArg Complex.re h
  -- simplify cos values: cos(pi/3)=1/2, cos(pi/2)=0
  have : ((1 : ℝ) / 2) = 0 := by simpa using hre
  norm_num at this

/-- Witness: Interf differs across φ for A=0,B=1 at φ1=pi/3, φ2=pi/2. -/
theorem interf_phi_witness_ne :
    Interf (Real.pi / 3) 0 1 ≠ Interf (Real.pi / 2) 0 1 := by
  -- Interf φ 0 1 = cis φ
  simpa [Interf, cis_pi_div_three_ne_cis_pi_div_two]

/--
N1 (faithful version): there is no injective representation h into a φ-free target operation op
that preserves interference for all φ, because the image would be φ-invariant, contradicting
a concrete witness where Interf differs across φ.

Evidence lock (numeric, vector witness):
  docs/Artifacts/sym_compare_v1/EFFECTALG_COUNTEREXAMPLE.json
-/
theorem N1_no_faithful_phi_free_representation
    {β : Type} (h : ℂ → β) (op : β → β → β)
    (hinj : Function.Injective h)
    (hom : ∀ φ A B, h (Interf φ A B) = op (h A) (h B)) :
    False := by
  have imgInv := n1_image_phi_invariant Interf h op hom
  have heq : h (Interf (Real.pi / 3) 0 1) = h (Interf (Real.pi / 2) 0 1) :=
    imgInv (Real.pi / 3) (Real.pi / 2) 0 1
  have : Interf (Real.pi / 3) 0 1 = Interf (Real.pi / 2) 0 1 := hinj heq
  exact interf_phi_witness_ne this

/-
N2 (strong): Interf φ cannot be the additive operation of any semiring for φ=pi/3
because semiring addition must be associative, but Interf is not.

This is strictly stronger than “distributivity fails” (it blocks semiring structure immediately).
Numeric distributivity witness is separately locked by:
  docs/Artifacts/sym_compare_v1/SEMIRING_COUNTEREXAMPLE.json
after you switch the semiring runner to LHS/RHS distributivity.
-/

/-- Helper: if z ≠ 0 and z ≠ 1 then z ≠ z^2. -/
theorem ne_sq_of_ne_zero_ne_one {z : ℂ} (hz0 : z ≠ 0) (hz1 : z ≠ 1) : z ≠ z^2 := by
  intro h
  -- from z = z^2, we get z^2 - z = 0, i.e. z*(z-1)=0
  have : z * (z - 1) = 0 := by
    -- rearrange: z^2 - z = 0
    have : z^2 - z = 0 := by
      simpa [pow_two, sub_eq_add_neg, add_assoc, add_left_comm, add_comm] using congrArg (fun t => t - z) h
    -- factor z^2 - z = z*(z-1)
    -- ring_nf works over ℂ
    -- z*(z-1) = z^2 - z
    simpa [pow_two, mul_add, add_mul, sub_eq_add_neg, mul_assoc, mul_left_comm, mul_comm, add_assoc, add_left_comm,
      add_comm, sub_mul, mul_sub] using this
  have := mul_eq_zero.mp this
  rcases this with h0 | h1
  · exact hz0 h0
  · -- z - 1 = 0 => z = 1
    have : z = 1 := by simpa using sub_eq_zero.mp h1
    exact hz1 this

/-- Interf (pi/3) is not associative. -/
theorem N2_interf_pi_div_three_not_associative :
    ¬ (∀ a b c : ℂ, Interf (Real.pi / 3) (Interf (Real.pi / 3) a b) c
                  = Interf (Real.pi / 3) a (Interf (Real.pi / 3) b c)) := by
  intro hassoc
  -- plug in a=0, b=0, c=1: LHS = cis φ, RHS = (cis φ)^2
  have h := hassoc 0 0 1
  have hz : Complex.cis (Real.pi / 3) = (Complex.cis (Real.pi / 3))^2 := by
    simpa [Interf, pow_two, mul_assoc, mul_add, add_mul] using h
  have hz0 : Complex.cis (Real.pi / 3) ≠ 0 := by simpa using (Complex.cis_ne_zero (Real.pi / 3))
  have hz1 : Complex.cis (Real.pi / 3) ≠ 1 := by
    intro h1
    have hre : Real.cos (Real.pi / 3) = (1 : ℝ) := by
      simpa using congrArg Complex.re h1
    -- cos(pi/3)=1/2 ≠ 1
    have : ((1 : ℝ) / 2) = 1 := by simpa using hre
    norm_num at this
  exact (ne_sq_of_ne_zero_ne_one hz0 hz1) hz

end SymCompare