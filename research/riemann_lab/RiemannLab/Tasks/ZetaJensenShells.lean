import RiemannLab.Tasks.SummableShellEnvelope
import RiemannLab.Tasks.QuantitativeZeroSeparation

namespace RiemannLab

open Complex Set Metric MeromorphicOn

/-!
# Unit-height zeta shells inside the quantitative Jensen disks

This file supplies the geometric specialization needed by the shell
summability theorem.  Every nontrivial zero in `[T,T+1)` lies in the checked
radius-`7/2` Jensen disk centered at `2+iT`; consequently each such shell is
finite and is supported by the exact xi divisor used in the `O(log T)` bound.
-/

/-- The positive-oriented unit-height shell of nontrivial zeta zeros. -/
def positiveUnitZetaShell (T : ℝ) : Set ℂ :=
  {ρ | IsNontrivialZetaZero ρ ∧ T ≤ ρ.im ∧ ρ.im < T + 1}

/-- Complete radius-`7/2` geometry for one critical-strip unit shell. -/
theorem nontrivialZero_mem_xiJensenDisk_of_mem_unitShell
    {T : ℝ} {ρ : ℂ} (hρ : IsNontrivialZetaZero ρ)
    (hlo : T ≤ ρ.im) (hhi : ρ.im < T + 1) :
    ρ ∈ closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ) := by
  rw [mem_closedBall, dist_eq, Complex.norm_def, Real.sqrt_le_iff]
  constructor
  · norm_num
  · simp [riemannXiJensenCenter, Complex.normSq_apply]
    have hre0 := hρ.re_pos
    have hre1 := hρ.re_lt_one
    nlinarith [sq_nonneg (ρ.re - 2), sq_nonneg (ρ.im - T)]

/-- Every unit shell is contained in the finite xi Jensen-divisor support. -/
theorem positiveUnitZetaShell_subset_xiJensenDivisorSupport (T : ℝ) :
    positiveUnitZetaShell T ⊆ ↑(xiJensenDivisorSupport T) := by
  intro ρ hρ
  have hmem := nontrivialZero_mem_xiJensenDisk_of_mem_unitShell
    hρ.1 hρ.2.1 hρ.2.2
  exact (riemannXiEntire_eq_zero_iff_mem_xiJensenDivisorSupport hmem).mp
    hρ.1.riemannXiEntire_eq_zero

/-- Hence each actual unit-height zeta shell is finite, without choosing an
enumeration of the zeros. -/
theorem positiveUnitZetaShell_finite (T : ℝ) :
    (positiveUnitZetaShell T).Finite := by
  exact (Finset.finite_toSet (xiJensenDivisorSupport T)).subset
    (positiveUnitZetaShell_subset_xiJensenDivisorSupport T)

/-- The unit shell as a finite set, ready for multiplicity-weighted sums. -/
noncomputable def positiveUnitZetaShellFinset (T : ℝ) : Finset ℂ :=
  (positiveUnitZetaShell_finite T).toFinset

@[simp]
theorem mem_positiveUnitZetaShellFinset {T : ℝ} {ρ : ℂ} :
    ρ ∈ positiveUnitZetaShellFinset T ↔
      IsNontrivialZetaZero ρ ∧ T ≤ ρ.im ∧ ρ.im < T + 1 := by
  simp [positiveUnitZetaShellFinset, positiveUnitZetaShell]

/-- On a point of the actual zeta shell, the xi divisor stores exactly its
natural analytic multiplicity. -/
theorem xiJensenDivisor_apply_eq_multiplicity
    {T : ℝ} {ρ : ℂ} (hρ : ρ ∈ positiveUnitZetaShell T) :
    divisor riemannXiEntire
        (closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ)) ρ =
      (analyticOrderNatAt riemannXiEntire ρ : ℤ) := by
  have hmem := nontrivialZero_mem_xiJensenDisk_of_mem_unitShell
    hρ.1 hρ.2.1 hρ.2.2
  have hana : AnalyticOnNhd ℂ riemannXiEntire
      (closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ)) :=
    fun z _ ↦ analyticAt_riemannXiEntire z
  rw [hana.divisor_apply hmem]
  have hfinite : analyticOrderAt riemannXiEntire ρ ≠ ⊤ := by
    rw [hρ.1.xiOrder_eq_zetaOrder]
    exact zetaZeroOrder_ne_top (by
      intro h
      have hlt := hρ.1.re_lt_one
      rw [h] at hlt
      norm_num at hlt)
  rw [show analyticOrderAt riemannXiEntire ρ =
      (analyticOrderNatAt riemannXiEntire ρ : ℕ) by
        exact (ENat.coe_toNat_eq_self.mpr hfinite).symm]
  simp

/-- The complete multiplicity mass of one actual zeta shell is bounded by
the Jensen divisor mass on the containing disk. -/
theorem positiveUnitZetaShell_multiplicity_le_jensenDivisor (T : ℝ) :
    ∑ ρ ∈ positiveUnitZetaShellFinset T,
        (analyticOrderNatAt riemannXiEntire ρ : ℤ) ≤
      ∑ᶠ u, divisor riemannXiEntire
        (closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ)) u := by
  let D := divisor riemannXiEntire
    (closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ))
  have hana : AnalyticOnNhd ℂ riemannXiEntire
      (closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ)) :=
    fun z _ ↦ analyticAt_riemannXiEntire z
  calc
    ∑ ρ ∈ positiveUnitZetaShellFinset T,
        (analyticOrderNatAt riemannXiEntire ρ : ℤ) =
      ∑ ρ ∈ positiveUnitZetaShellFinset T, D ρ := by
        apply Finset.sum_congr rfl
        intro ρ hρ
        exact (xiJensenDivisor_apply_eq_multiplicity
          ((mem_positiveUnitZetaShellFinset.mp hρ))).symm
    _ ≤ ∑ ρ ∈ xiJensenDivisorSupport T, D ρ := by
      apply Finset.sum_le_sum_of_subset_of_nonneg
      · intro ρ hρ
        exact positiveUnitZetaShell_subset_xiJensenDivisorSupport T
          (mem_positiveUnitZetaShellFinset.mp hρ)
      · intro ρ hρ hnot
        exact hana.divisor_nonneg ρ
    _ = ∑ᶠ u, D u := by
      rw [finsum_eq_sum_of_support_subset (s := xiJensenDivisorSupport T)]
      intro z hz
      simpa [xiJensenDivisorSupport, D, Function.mem_support] using hz

/-- Quantitative `O(log T)` bound for the actual multiplicity-weighted zeta
shell, now in real coordinates for the summability engine. -/
theorem positiveUnitZetaShell_multiplicity_le_log
    {T : ℝ} (hT : 2 ≤ T) :
    ∑ ρ ∈ positiveUnitZetaShellFinset T,
        (analyticOrderNatAt riemannXiEntire ρ : ℝ) ≤
      (Real.log jensenQuotientPolynomialConstant + 12 * Real.log T) /
        Real.log (8 / 7) := by
  have hZ := positiveUnitZetaShell_multiplicity_le_jensenDivisor T
  have hR : (∑ ρ ∈ positiveUnitZetaShellFinset T,
        (analyticOrderNatAt riemannXiEntire ρ : ℝ)) ≤
      ((∑ᶠ u, divisor riemannXiEntire
        (closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ)) u : ℤ) : ℝ) := by
    exact_mod_cast hZ
  exact hR.trans (riemannXiEntire_local_zero_count_seven_halves_le_log hT)

/-- One explicit constant converting the logarithmic Jensen bound into the
linear shell-mass hypothesis used by `SummableShellEnvelope`. -/
noncomputable def zetaShellLinearConstant : ℝ :=
  (max 0 (Real.log jensenQuotientPolynomialConstant) + 24) /
    Real.log (8 / 7)

theorem zetaShellLinearConstant_nonneg : 0 ≤ zetaShellLinearConstant := by
  unfold zetaShellLinearConstant
  exact div_nonneg (add_nonneg (le_max_left _ _) (by norm_num))
    (Real.log_pos (by norm_num)).le

/-- The actual multiplicity mass in `[n+2,n+3)` is bounded linearly in its
shell index.  This is stronger than needed for fourth-power summability. -/
theorem positiveUnitZetaShell_multiplicity_le_linear (n : ℕ) :
    ∑ ρ ∈ positiveUnitZetaShellFinset (n + 2),
        (analyticOrderNatAt riemannXiEntire ρ : ℝ) ≤
      zetaShellLinearConstant * (n + 1) := by
  have hj := positiveUnitZetaShell_multiplicity_le_log
    (T := (n + 2 : ℕ)) (by exact_mod_cast Nat.le_add_left 2 n)
  have hlog : Real.log ((n + 2 : ℕ) : ℝ) ≤ (n + 2 : ℕ) :=
    Real.log_le_self (by positivity)
  have hden : 0 < Real.log (8 / 7) := Real.log_pos (by norm_num)
  norm_num [Nat.cast_add] at hj hlog ⊢
  apply hj.trans
  unfold zetaShellLinearConstant
  rw [div_mul_eq_mul_div]
  apply (div_le_div_iff_of_pos_right hden).2
  have hmax : Real.log jensenQuotientPolynomialConstant ≤
      max 0 (Real.log jensenQuotientPolynomialConstant) := le_max_right _ _
  nlinarith [le_max_left 0 (Real.log jensenQuotientPolynomialConstant)]

end RiemannLab
