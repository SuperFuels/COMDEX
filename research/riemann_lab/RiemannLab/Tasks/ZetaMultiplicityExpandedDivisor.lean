import RiemannLab.Tasks.ZetaGenusOneCanonicalFactor
import Mathlib.Data.Finite.Sigma

namespace RiemannLab

/-!
# Multiplicity-expanded zeta divisor

Canonical products are most naturally indexed by one factor for every copy of
a zero.  These types expand the analytic multiplicity into a finite `Fin`
fibre and transport the checked quadratic shell summability to that literal
factor index.
-/

/-- One positive-height canonical factor for every unit of analytic
multiplicity. -/
def PositiveHighZetaFactorIndex :=
  Σ i : PositiveHighZetaShellIndex,
    Fin (analyticOrderNatAt riemannXiEntire i.2.1)

/-- The shellwise quadratic weight of a positive-height factor copy. -/
noncomputable def positiveHighZetaFactorQuadraticWeight
    (j : PositiveHighZetaFactorIndex) : ℝ :=
  1 / (((j.1.1 + 1 : ℕ) : ℝ) ^ 2)

theorem positiveHighZetaFactorQuadraticWeight_nonneg
    (j : PositiveHighZetaFactorIndex) :
    0 ≤ positiveHighZetaFactorQuadraticWeight j := by
  exact div_nonneg zero_le_one (pow_nonneg (Nat.cast_nonneg _) 2)

/-- Repeating each positive zero exactly according to its analytic
multiplicity preserves quadratic summability. -/
theorem summable_positiveHighZetaFactorQuadraticWeight :
    Summable positiveHighZetaFactorQuadraticWeight := by
  unfold PositiveHighZetaFactorIndex
  apply (summable_sigma_of_nonneg
    (fun j ↦ positiveHighZetaFactorQuadraticWeight_nonneg j)).2
  constructor
  · intro i
    exact Summable.of_finite
  · apply summable_positiveHighZetaQuadraticMass.congr
    intro i
    rw [tsum_fintype]
    simp [positiveHighZetaFactorQuadraticWeight,
      positiveHighZetaQuadraticMass, Finset.sum_const,
      nsmul_eq_mul, div_eq_mul_inv, mul_comm]

/-- The actual positive zero carried by a multiplicity-expanded factor. -/
def positiveHighZetaFactorPoint (j : PositiveHighZetaFactorIndex) : ℂ :=
  j.1.2.1

theorem positiveHighZetaFactorPoint_ne_zero (j : PositiveHighZetaFactorIndex) :
    positiveHighZetaFactorPoint j ≠ 0 := by
  have hz : IsNontrivialZetaZero j.1.2.1 :=
    (mem_positiveUnitZetaShellFinset.mp j.1.2.property).1
  intro h
  rw [show j.1.2.1 = 0 from h] at hz
  have := hz.re_pos
  norm_num at this

/-- Shell height controls the norm of every literal positive factor point. -/
theorem positiveHighZetaFactor_shell_le_norm (j : PositiveHighZetaFactorIndex) :
    ((j.1.1 + 1 : ℕ) : ℝ) ≤ ‖positiveHighZetaFactorPoint j‖ := by
  have hmem := mem_positiveUnitZetaShellFinset.mp j.1.2.property
  have him0 : 0 ≤ j.1.2.1.im := by
    norm_num [Nat.cast_add] at hmem
    linarith [hmem.2.1]
  calc
    ((j.1.1 + 1 : ℕ) : ℝ) ≤ j.1.2.1.im := by
      norm_num [Nat.cast_add] at hmem ⊢
      linarith [hmem.2.1]
    _ = |j.1.2.1.im| := (abs_of_nonneg him0).symm
    _ ≤ ‖j.1.2.1‖ := Complex.abs_im_le_norm _

/-- The literal multiplicity-expanded positive divisor has summable inverse
square norm. -/
theorem summable_positiveHighZetaFactor_inverseSquare :
    Summable (fun j : PositiveHighZetaFactorIndex ↦
      1 / ‖positiveHighZetaFactorPoint j‖ ^ 2) := by
  apply summable_positiveHighZetaFactorQuadraticWeight.of_nonneg_of_le
  · intro j
    positivity
  · intro j
    unfold positiveHighZetaFactorQuadraticWeight
    have hlo : 0 < (((j.1.1 + 1 : ℕ) : ℝ) ^ 2) := by positivity
    exact one_div_le_one_div_of_le hlo
      (pow_le_pow_left₀ (by positivity) (positiveHighZetaFactor_shell_le_norm j) 2)

/-- One negative-height canonical factor for every transported unit of zeta
multiplicity. -/
def NegativeHighZetaFactorIndex :=
  Σ i : NegativeHighZetaShellIndex,
    Fin (analyticOrderNatAt riemannZeta (1 - i.2.1))

/-- The shellwise quadratic weight of a negative-height factor copy. -/
noncomputable def negativeHighZetaFactorQuadraticWeight
    (j : NegativeHighZetaFactorIndex) : ℝ :=
  1 / (((j.1.1 + 1 : ℕ) : ℝ) ^ 2)

theorem negativeHighZetaFactorQuadraticWeight_nonneg
    (j : NegativeHighZetaFactorIndex) :
    0 ≤ negativeHighZetaFactorQuadraticWeight j := by
  exact div_nonneg zero_le_one (pow_nonneg (Nat.cast_nonneg _) 2)

/-- The reflected negative divisor is likewise summable after literal
multiplicity expansion. -/
theorem summable_negativeHighZetaFactorQuadraticWeight :
    Summable negativeHighZetaFactorQuadraticWeight := by
  unfold NegativeHighZetaFactorIndex
  apply (summable_sigma_of_nonneg
    (fun j ↦ negativeHighZetaFactorQuadraticWeight_nonneg j)).2
  constructor
  · intro i
    exact Summable.of_finite
  · apply summable_negativeHighZetaQuadraticMass.congr
    intro i
    rw [tsum_fintype]
    simp [negativeHighZetaFactorQuadraticWeight,
      negativeHighZetaQuadraticMass, Finset.sum_const,
      nsmul_eq_mul, div_eq_mul_inv, mul_comm]

/-- The actual reflected negative zero carried by a factor copy. -/
def negativeHighZetaFactorPoint (j : NegativeHighZetaFactorIndex) : ℂ :=
  1 - j.1.2.1

theorem negativeHighZetaFactorPoint_ne_zero (j : NegativeHighZetaFactorIndex) :
    negativeHighZetaFactorPoint j ≠ 0 := by
  have hz : IsNontrivialZetaZero (1 - j.1.2.1) :=
    ((mem_positiveUnitZetaShellFinset.mp j.1.2.property).1).one_sub
  intro h
  rw [show 1 - j.1.2.1 = 0 from h] at hz
  have := hz.re_pos
  norm_num at this

/-- Reflection preserves the shell lower bound needed for inverse-square
summability. -/
theorem negativeHighZetaFactor_shell_le_norm (j : NegativeHighZetaFactorIndex) :
    ((j.1.1 + 1 : ℕ) : ℝ) ≤ ‖negativeHighZetaFactorPoint j‖ := by
  have hmem := mem_positiveUnitZetaShellFinset.mp j.1.2.property
  have him0 : 0 ≤ j.1.2.1.im := by
    norm_num [Nat.cast_add] at hmem
    linarith [hmem.2.1]
  have him : ((j.1.1 + 1 : ℕ) : ℝ) ≤ j.1.2.1.im := by
    norm_num [Nat.cast_add] at hmem ⊢
    linarith [hmem.2.1]
  calc
    ((j.1.1 + 1 : ℕ) : ℝ) ≤ |(1 - j.1.2.1).im| := by
      simpa [abs_of_nonneg him0] using him
    _ ≤ ‖1 - j.1.2.1‖ := Complex.abs_im_le_norm _

/-- The literal multiplicity-expanded negative divisor has summable inverse
square norm. -/
theorem summable_negativeHighZetaFactor_inverseSquare :
    Summable (fun j : NegativeHighZetaFactorIndex ↦
      1 / ‖negativeHighZetaFactorPoint j‖ ^ 2) := by
  apply summable_negativeHighZetaFactorQuadraticWeight.of_nonneg_of_le
  · intro j
    positivity
  · intro j
    unfold negativeHighZetaFactorQuadraticWeight
    have hlo : 0 < (((j.1.1 + 1 : ℕ) : ℝ) ^ 2) := by positivity
    exact one_div_le_one_div_of_le hlo
      (pow_le_pow_left₀ (by positivity) (negativeHighZetaFactor_shell_le_norm j) 2)

/-- The central block, also expanded into one point per unit of analytic
multiplicity. -/
def LowHeightZetaFactorIndex :=
  Σ ρ : {z : NontrivialZetaZeroPoint | |z.1.im| < 2},
    Fin (zetaZeroMultiplicity ρ.1)

/-- The multiplicity-expanded central factor index is finite. -/
noncomputable instance finite_lowHeightZetaFactorIndex :
    Finite LowHeightZetaFactorIndex := by
  let e : NontrivialZetaZeroPoint ↪ ℂ :=
    ⟨Subtype.val, Subtype.val_injective⟩
  have hbase : {z : NontrivialZetaZeroPoint | |z.1.im| < 2}.Finite := by
    have hpre := lowHeightNontrivialZetaZeros_finite.preimage_embedding e
    have heq : e ⁻¹' lowHeightNontrivialZetaZeros =
        {z : NontrivialZetaZeroPoint | |z.1.im| < 2} := by
      ext z
      simp [e, lowHeightNontrivialZetaZeros, z.property]
    rw [← heq]
    exact hpre
  letI := hbase.fintype
  letI : Fintype LowHeightZetaFactorIndex := Sigma.instFintype
  exact Finite.of_fintype _

/-- Any amplitude on the multiplicity-expanded central divisor is summable. -/
theorem summable_lowHeightZetaFactorIndex (f : LowHeightZetaFactorIndex → ℂ) :
    Summable f := by
  exact Summable.of_finite

end RiemannLab
