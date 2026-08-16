import RiemannLab.Tasks.ZetaTwoSidedDampedSummability
import Mathlib.Analysis.PSeries

namespace RiemannLab

/-!
# Quadratic inverse-zero summability

The genus-one Hadamard product needs quadratic, rather than fourth-power,
damping.  The checked logarithmic shell count is strong enough: a logarithm
is bounded by a square root, leaving a convergent `3/2`-series.
-/

/-- An explicit square-root envelope for the positive unit-shell mass. -/
noncomputable def zetaShellSqrtConstant : ℝ :=
  (max 0 (Real.log jensenQuotientPolynomialConstant) + 48) /
    Real.log (8 / 7)

theorem zetaShellSqrtConstant_nonneg : 0 ≤ zetaShellSqrtConstant := by
  unfold zetaShellSqrtConstant
  exact div_nonneg (add_nonneg (le_max_left _ _) (by norm_num))
    (Real.log_pos (by norm_num)).le

theorem log_nat_add_two_le_four_sqrt_nat_add_one (n : ℕ) :
    Real.log ((n + 2 : ℕ) : ℝ) ≤ 4 * Real.sqrt ((n + 1 : ℕ) : ℝ) := by
  let x : ℝ := (n + 1 : ℕ)
  let y : ℝ := (n + 2 : ℕ)
  have hx : 1 ≤ x := by
    dsimp [x]
    exact_mod_cast Nat.succ_le_succ (Nat.zero_le n)
  have hy : 0 ≤ y := by positivity
  have hlog := Real.log_le_rpow_div hy (by norm_num : (0 : ℝ) < 1 / 2)
  have hlog' : Real.log y ≤ 2 * Real.sqrt y := by
    rw [← Real.sqrt_eq_rpow] at hlog
    convert hlog using 1 <;> norm_num <;> ring
  have hsqrt : Real.sqrt y ≤ 2 * Real.sqrt x := by
    rw [Real.sqrt_le_iff]
    constructor
    · positivity
    · have hx0 : 0 ≤ x := le_trans (by norm_num) hx
      have hsx : (Real.sqrt x) ^ 2 = x := Real.sq_sqrt hx0
      have hxy : y ≤ 4 * x := by
        dsimp [x, y]
        norm_num [Nat.cast_add]
        have hn : (0 : ℝ) ≤ n := Nat.cast_nonneg n
        linarith
      nlinarith [sq_nonneg (Real.sqrt x)]
  dsimp [x, y] at hlog' hsqrt ⊢
  linarith

/-- The actual multiplicity mass in the `n`th positive shell has a
square-root envelope. -/
theorem positiveUnitZetaShell_multiplicity_le_sqrt (n : ℕ) :
    ∑ ρ ∈ positiveUnitZetaShellFinset (n + 2),
        (analyticOrderNatAt riemannXiEntire ρ : ℝ) ≤
      zetaShellSqrtConstant * Real.sqrt ((n + 1 : ℕ) : ℝ) := by
  have hj := positiveUnitZetaShell_multiplicity_le_log
    (T := (n + 2 : ℕ)) (by exact_mod_cast Nat.le_add_left 2 n)
  have hlog := log_nat_add_two_le_four_sqrt_nat_add_one n
  have hden : 0 < Real.log (8 / 7) := Real.log_pos (by norm_num)
  have hsqrtOne : 1 ≤ Real.sqrt ((n + 1 : ℕ) : ℝ) := by
    rw [Real.one_le_sqrt]
    exact_mod_cast Nat.succ_le_succ (Nat.zero_le n)
  have hmax : Real.log jensenQuotientPolynomialConstant ≤
      max 0 (Real.log jensenQuotientPolynomialConstant) := le_max_right _ _
  have hsqrtOne' : 1 ≤ Real.sqrt ((n : ℝ) + 1) := by
    simpa only [Nat.cast_add, Nat.cast_one] using hsqrtOne
  norm_num [Nat.cast_add] at hj hlog ⊢
  apply hj.trans
  unfold zetaShellSqrtConstant
  rw [div_mul_eq_mul_div]
  apply (div_le_div_iff_of_pos_right hden).2
  have hmax0 : 0 ≤ max 0 (Real.log jensenQuotientPolynomialConstant) :=
    le_max_left _ _
  have hmaxmul : max 0 (Real.log jensenQuotientPolynomialConstant) ≤
      max 0 (Real.log jensenQuotientPolynomialConstant) *
        Real.sqrt (↑n + 1) := by
    calc
      max 0 (Real.log jensenQuotientPolynomialConstant) =
          max 0 (Real.log jensenQuotientPolynomialConstant) * 1 := by ring
      _ ≤ max 0 (Real.log jensenQuotientPolynomialConstant) *
          Real.sqrt (↑n + 1) :=
        mul_le_mul_of_nonneg_left hsqrtOne' hmax0
  calc
    Real.log jensenQuotientPolynomialConstant +
        12 * Real.log (↑n + 2) ≤
      max 0 (Real.log jensenQuotientPolynomialConstant) +
        12 * (4 * Real.sqrt (↑n + 1)) :=
      add_le_add hmax (mul_le_mul_of_nonneg_left hlog (by norm_num))
    _ = max 0 (Real.log jensenQuotientPolynomialConstant) +
        48 * Real.sqrt (↑n + 1) := by ring
    _ ≤ max 0 (Real.log jensenQuotientPolynomialConstant) *
          Real.sqrt (↑n + 1) + 48 * Real.sqrt (↑n + 1) := by
      exact add_le_add hmaxmul le_rfl
    _ = (max 0 (Real.log jensenQuotientPolynomialConstant) + 48) *
          Real.sqrt (↑n + 1) := by ring

/-- Quadratically damped multiplicity mass on the positive shell union. -/
noncomputable def positiveHighZetaQuadraticMass
    (i : PositiveHighZetaShellIndex) : ℝ :=
  analyticOrderNatAt riemannXiEntire i.2.1 /
    (((i.1 + 1 : ℕ) : ℝ) ^ 2)

theorem positiveHighZetaQuadraticMass_nonneg
    (i : PositiveHighZetaShellIndex) :
    0 ≤ positiveHighZetaQuadraticMass i := by
  exact div_nonneg (Nat.cast_nonneg _) (pow_nonneg (Nat.cast_nonneg _) 2)

private theorem sqrt_div_sq_eq_rpow (n : ℕ) :
    Real.sqrt ((n + 1 : ℕ) : ℝ) / (((n + 1 : ℕ) : ℝ) ^ 2) =
      1 / (((n + 1 : ℕ) : ℝ) ^ (3 / 2 : ℝ)) := by
  let x : ℝ := (n + 1 : ℕ)
  have hx : 0 < x := by positivity
  have hsqrt : Real.sqrt x = x ^ (1 / 2 : ℝ) := Real.sqrt_eq_rpow x
  dsimp [x] at hsqrt ⊢
  rw [hsqrt, ← Real.rpow_two]
  rw [← Real.rpow_sub hx]
  norm_num
  rw [Real.rpow_neg (le_of_lt hx)]
  simp [x]

/-- The complete positive-height zeta divisor is summable with the quadratic
damping required for a genus-one canonical product. -/
theorem summable_positiveHighZetaQuadraticMass :
    Summable positiveHighZetaQuadraticMass := by
  unfold PositiveHighZetaShellIndex positiveHighZetaQuadraticMass
  apply (summable_sigma_of_nonneg (fun i ↦ div_nonneg (Nat.cast_nonneg _)
    (pow_nonneg (Nat.cast_nonneg _) 2))).2
  constructor
  · intro n
    exact Summable.of_finite
  · have hpseries : Summable (fun n : ℕ ↦
        zetaShellSqrtConstant /
          (((n + 1 : ℕ) : ℝ) ^ (3 / 2 : ℝ))) := by
      have hbase : Summable (fun n : ℕ ↦
          1 / (((n + 1 : ℕ) : ℝ) ^ (3 / 2 : ℝ))) := by
        have h := (Real.summable_one_div_nat_add_rpow 1 (3 / 2)).2 (by norm_num)
        apply h.congr
        intro n
        rw [abs_of_nonneg]
        · norm_num [Nat.cast_add]
        · positivity
      simpa [div_eq_mul_inv] using hbase.mul_left zetaShellSqrtConstant
    apply hpseries.of_nonneg_of_le
    · intro n
      exact tsum_nonneg fun i ↦ positiveHighZetaQuadraticMass_nonneg ⟨n, i⟩
    · intro n
      rw [tsum_fintype]
      change (∑ ρ : PositiveZetaShellPoint n,
          (analyticOrderNatAt riemannXiEntire ρ.1 : ℝ) /
            (((n + 1 : ℕ) : ℝ) ^ 2)) ≤ _
      rw [← Finset.sum_div]
      have hmass := positiveUnitZetaShell_multiplicity_le_sqrt n
      have hden : 0 < (((n + 1 : ℕ) : ℝ) ^ 2) := by positivity
      calc
        (∑ ρ : PositiveZetaShellPoint n,
            (analyticOrderNatAt riemannXiEntire ρ.1 : ℝ)) /
              (((n + 1 : ℕ) : ℝ) ^ 2) =
            (∑ ρ ∈ positiveUnitZetaShellFinset (n + 2),
              (analyticOrderNatAt riemannXiEntire ρ : ℝ)) /
              (((n + 1 : ℕ) : ℝ) ^ 2) := by
              congr 1
              exact (Finset.sum_subtype
                (positiveUnitZetaShellFinset (n + 2))
                (fun ρ ↦ Iff.rfl)
                (fun ρ ↦ (analyticOrderNatAt riemannXiEntire ρ : ℝ))).symm
        _ ≤ (zetaShellSqrtConstant * Real.sqrt ((n + 1 : ℕ) : ℝ)) /
              (((n + 1 : ℕ) : ℝ) ^ 2) :=
            div_le_div_of_nonneg_right hmass hden.le
        _ = zetaShellSqrtConstant /
              (((n + 1 : ℕ) : ℝ) ^ (3 / 2 : ℝ)) := by
            rw [mul_div_assoc, sqrt_div_sq_eq_rpow]
            simp [div_eq_mul_inv]

/-! ## Reflection and the complete two-sided divisor -/

/-- Quadratically damped multiplicity on the reflected negative shell union. -/
noncomputable def negativeHighZetaQuadraticMass
    (i : NegativeHighZetaShellIndex) : ℝ :=
  analyticOrderNatAt riemannZeta (1 - i.2.1) /
    (((i.1 + 1 : ℕ) : ℝ) ^ 2)

/-- Functional-equation reflection transports the positive quadratic
summability theorem to the complete negative-height divisor. -/
theorem summable_negativeHighZetaQuadraticMass :
    Summable negativeHighZetaQuadraticMass := by
  have heq : negativeHighZetaQuadraticMass = positiveHighZetaQuadraticMass := by
    funext i
    have hzero : IsNontrivialZetaZero i.2.1 :=
      (mem_positiveUnitZetaShellFinset.mp i.2.property).1
    unfold negativeHighZetaQuadraticMass positiveHighZetaQuadraticMass
    rw [zetaMultiplicity_one_sub hzero,
      ← hzero.xiMultiplicity_eq_zetaMultiplicity]
  rw [heq]
  exact summable_positiveHighZetaQuadraticMass

/-- The finite central zero block is quadratically summable for every
nonzero-denominator weight. -/
theorem summable_lowHeight_zeta_inverseSquareMultiplicity :
    Summable (fun ρ : {z : NontrivialZetaZeroPoint | |z.1.im| < 2} ↦
      (zetaZeroMultiplicity ρ.1 : ℝ) / ‖ρ.1.1‖ ^ 2) := by
  let e : NontrivialZetaZeroPoint ↪ ℂ :=
    ⟨Subtype.val, Subtype.val_injective⟩
  have hfinite : {z : NontrivialZetaZeroPoint | |z.1.im| < 2}.Finite := by
    have hpre := lowHeightNontrivialZetaZeros_finite.preimage_embedding e
    have heq : e ⁻¹' lowHeightNontrivialZetaZeros =
        {z : NontrivialZetaZeroPoint | |z.1.im| < 2} := by
      ext z
      simp [e, lowHeightNontrivialZetaZeros, z.property]
    rw [← heq]
    exact hpre
  letI := hfinite.fintype
  exact Summable.of_finite

/-- Collected convergence package required before constructing the global
genus-one product. -/
theorem zeta_genusOne_quadratic_summability_package :
    Summable positiveHighZetaQuadraticMass ∧
      Summable negativeHighZetaQuadraticMass ∧
      Summable (fun ρ : {z : NontrivialZetaZeroPoint | |z.1.im| < 2} ↦
        (zetaZeroMultiplicity ρ.1 : ℝ) / ‖ρ.1.1‖ ^ 2) :=
  ⟨summable_positiveHighZetaQuadraticMass,
    summable_negativeHighZetaQuadraticMass,
    summable_lowHeight_zeta_inverseSquareMultiplicity⟩

end RiemannLab
