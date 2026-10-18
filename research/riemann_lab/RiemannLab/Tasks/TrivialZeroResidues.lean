import RiemannLab.Tasks.ContourShift
import Mathlib.Analysis.Calculus.Deriv.Slope
import Mathlib.Analysis.SpecialFunctions.Log.Deriv

namespace RiemannLab

open Filter
open scoped Topology

/-!
Simplicity and residue infrastructure for the negative-even trivial zeros of
the Riemann zeta function.
-/

/-- The reciprocal real Gamma factor has derivative `1/2` at the origin. -/
theorem hasDerivAt_inv_Gammaℝ_zero :
    HasDerivAt (fun s : ℂ ↦ (Complex.Gammaℝ s)⁻¹) (1 / 2) 0 := by
  rw [hasDerivAt_iff_tendsto_slope]
  have hlim := Complex.Gammaℝ_residue_zero.inv₀ (by norm_num : (2 : ℂ) ≠ 0)
  have heq : (fun s : ℂ ↦ (s * Complex.Gammaℝ s)⁻¹) =ᶠ[𝓝[≠] 0]
      slope (fun s : ℂ ↦ (Complex.Gammaℝ s)⁻¹) 0 := by
    filter_upwards [self_mem_nhdsWithin] with s hs
    have hs0 : s ≠ 0 := by simpa using hs
    have hG0 : Complex.Gammaℝ 0 = 0 :=
      Complex.Gammaℝ_eq_zero_iff.mpr ⟨0, by simp⟩
    simp [slope, hG0, smul_eq_mul, hs0]
    ring
  simpa [one_div] using hlim.congr' heq

/-- Recurrence for the reciprocal real Gamma factor, oriented toward its
negative-even zeros. -/
theorem inv_Gammaℝ_eq_mul_inv_Gammaℝ_add_two {s : ℂ} (hs : s ≠ 0) :
    (Complex.Gammaℝ s)⁻¹ =
      (s / (2 * Real.pi)) * (Complex.Gammaℝ (s + 2))⁻¹ := by
  rw [Complex.Gammaℝ_add_two hs]
  field_simp [hs, Real.pi_ne_zero]

/-- Every zero of the reciprocal real Gamma factor at a nonpositive even
integer is simple. -/
theorem deriv_inv_Gammaℝ_neg_two_nat_ne_zero (n : ℕ) :
    deriv (fun s : ℂ ↦ (Complex.Gammaℝ s)⁻¹) (-2 * n) ≠ 0 := by
  induction n with
  | zero =>
      have hne : deriv (fun s : ℂ ↦ (Complex.Gammaℝ s)⁻¹) 0 ≠ 0 := by
        rw [hasDerivAt_inv_Gammaℝ_zero.deriv]
        norm_num
      simpa only [Nat.cast_zero, mul_zero, neg_zero] using hne
  | succ n ih =>
      let p : ℂ := -2 * (n + 1)
      have hp0 : p ≠ 0 := by
        dsimp [p]
        exact mul_ne_zero (by norm_num) (by exact_mod_cast Nat.succ_ne_zero n)
      have hpadd : p + 2 = (-2 * n : ℂ) := by
        dsimp [p]
        push_cast
        ring
      have heq : (fun s : ℂ ↦ (Complex.Gammaℝ s)⁻¹) =ᶠ[𝓝 p]
          (fun s ↦ (s / (2 * Real.pi)) * (Complex.Gammaℝ (s + 2))⁻¹) := by
        filter_upwards [eventually_ne_nhds hp0] with s hs
        exact inv_Gammaℝ_eq_mul_inv_Gammaℝ_add_two hs
      have hGzero : (Complex.Gammaℝ (p + 2))⁻¹ = 0 := by
        have hz : Complex.Gammaℝ (-2 * n : ℂ) = 0 :=
          Complex.Gammaℝ_eq_zero_iff.mpr ⟨n, by ring⟩
        rw [hpadd, hz, inv_zero]
      have hrightDeriv :
          deriv (fun s : ℂ ↦ (s / (2 * Real.pi)) * (Complex.Gammaℝ (s + 2))⁻¹) p =
            (p / (2 * Real.pi)) *
              deriv (fun z : ℂ ↦ (Complex.Gammaℝ z)⁻¹) (p + 2) := by
        have hcompDeriv :
            deriv (fun s : ℂ ↦ (Complex.Gammaℝ (s + 2))⁻¹) p =
              deriv (fun z : ℂ ↦ (Complex.Gammaℝ z)⁻¹) (p + 2) := by
          change deriv ((fun z : ℂ ↦ (Complex.Gammaℝ z)⁻¹) ∘
            (fun s : ℂ ↦ s + 2)) p = _
          rw [deriv_comp p Complex.differentiable_Gammaℝ_inv.differentiableAt (by fun_prop)]
          simp
        have hdcomp : DifferentiableAt ℂ
            (fun s : ℂ ↦ (Complex.Gammaℝ (s + 2))⁻¹) p := by
          exact Complex.differentiable_Gammaℝ_inv.differentiableAt.comp p (by fun_prop)
        change deriv ((fun s : ℂ ↦ s / (2 * Real.pi)) *
          (fun s : ℂ ↦ (Complex.Gammaℝ (s + 2))⁻¹)) p = _
        rw [deriv_mul (by fun_prop) hdcomp, deriv_div_const, deriv_id'',
          hGzero, hcompDeriv]
        ring
      have hderiv : deriv (fun s : ℂ ↦ (Complex.Gammaℝ s)⁻¹) p =
          (p / (2 * Real.pi)) *
            deriv (fun z : ℂ ↦ (Complex.Gammaℝ z)⁻¹) (p + 2) := by
        rw [heq.deriv_eq]
        exact hrightDeriv
      have hne : deriv (fun s : ℂ ↦ (Complex.Gammaℝ s)⁻¹) p ≠ 0 := by
        rw [hderiv, hpadd]
        exact mul_ne_zero (div_ne_zero hp0 (mul_ne_zero (by norm_num)
          (Complex.ofReal_ne_zero.mpr Real.pi_ne_zero))) ih
      simpa [p, Nat.cast_add, Nat.cast_one] using hne

/-- The completed zeta factor does not vanish at a negative-even trivial-zero
point. -/
theorem completedRiemannZeta_neg_two_mul_nat_add_one_ne_zero (n : ℕ) :
    completedRiemannZeta (-2 * (n + 1)) ≠ 0 := by
  let p : ℂ := -2 * (n + 1)
  have hqre : 1 ≤ (1 - p).re := by
    dsimp [p]
    push_cast
    norm_num
    positivity
  have hq0 : 1 - p ≠ 0 := by
    intro h
    have hbad := hqre
    rw [h] at hbad
    norm_num at hbad
  have hzeta : riemannZeta (1 - p) ≠ 0 :=
    riemannZeta_ne_zero_of_one_le_re hqre
  have hcompleted : completedRiemannZeta (1 - p) ≠ 0 := by
    intro hzero
    apply hzeta
    rw [riemannZeta_def_of_ne_zero hq0, hzero, zero_div]
  rw [completedRiemannZeta_one_sub p] at hcompleted
  simpa [p, Nat.cast_add, Nat.cast_one] using hcompleted

/-- The derivative of zeta is nonzero at every negative-even trivial zero. -/
theorem deriv_riemannZeta_neg_two_mul_nat_add_one_ne_zero (n : ℕ) :
    deriv riemannZeta (-2 * (n + 1)) ≠ 0 := by
  let p : ℂ := -2 * (n + 1)
  have hp0 : p ≠ 0 := by
    dsimp [p]
    exact mul_ne_zero (by norm_num) (by
      exact_mod_cast Nat.succ_ne_zero n)
  have hp1 : p ≠ 1 := by
    intro h
    have hpneg : p.re < 0 := by
      dsimp [p]
      push_cast
      norm_num
      positivity
    rw [h] at hpneg
    norm_num at hpneg
  have heq : riemannZeta =ᶠ[𝓝 p]
      (fun s ↦ completedRiemannZeta s * (Complex.Gammaℝ s)⁻¹) := by
    filter_upwards [eventually_ne_nhds hp0] with s hs
    rw [riemannZeta_def_of_ne_zero hs]
    rfl
  have hGzero : (Complex.Gammaℝ p)⁻¹ = 0 := by
    have hz : Complex.Gammaℝ p = 0 := by
      apply Complex.Gammaℝ_eq_zero_iff.mpr
      refine ⟨n + 1, ?_⟩
      simp [p, Nat.cast_add, Nat.cast_one]
    simp [hz]
  have hproductDeriv :
      deriv (fun s ↦ completedRiemannZeta s * (Complex.Gammaℝ s)⁻¹) p =
        completedRiemannZeta p *
          deriv (fun s : ℂ ↦ (Complex.Gammaℝ s)⁻¹) p := by
    change deriv (completedRiemannZeta *
      (fun s : ℂ ↦ (Complex.Gammaℝ s)⁻¹)) p = _
    rw [deriv_mul (differentiableAt_completedZeta hp0 hp1)
      Complex.differentiable_Gammaℝ_inv.differentiableAt, hGzero]
    ring
  have hderiv : deriv riemannZeta p = completedRiemannZeta p *
      deriv (fun s : ℂ ↦ (Complex.Gammaℝ s)⁻¹) p := by
    rw [heq.deriv_eq]
    exact hproductDeriv
  have hcompleted : completedRiemannZeta p ≠ 0 := by
    simpa [p, Nat.cast_add, Nat.cast_one] using
      completedRiemannZeta_neg_two_mul_nat_add_one_ne_zero n
  have hgamma : deriv (fun s : ℂ ↦ (Complex.Gammaℝ s)⁻¹) p ≠ 0 := by
    simpa [p, Nat.cast_add, Nat.cast_one] using
      deriv_inv_Gammaℝ_neg_two_nat_ne_zero (n + 1)
  have hne : deriv riemannZeta p ≠ 0 := by
    rw [hderiv]
    exact mul_ne_zero hcompleted hgamma
  simpa [p, Nat.cast_add, Nat.cast_one] using hne

/-- Every negative-even trivial zero of zeta has analytic multiplicity one. -/
theorem zetaZeroOrder_neg_two_mul_nat_add_one (n : ℕ) :
    zetaZeroOrder (-2 * (n + 1)) = 1 := by
  unfold zetaZeroOrder
  apply AnalyticAt.analyticOrderAt_eq_one_of_zero_deriv_ne_zero
    (analyticOn_riemannZeta (-2 * (n + 1)) (by
      intro h
      have hneg : (-2 * (n + 1) : ℂ).re < 0 := by
        push_cast
        norm_num
        positivity
      rw [h] at hneg
      norm_num at hneg))
  · exact riemannZeta_neg_two_mul_nat_add_one n
  · exact deriv_riemannZeta_neg_two_mul_nat_add_one_ne_zero n

/-- The contour-kernel residue at a negative-even trivial zero is the usual
simple-zero contribution `-x^ρ/ρ`. -/
theorem tendsto_mul_explicitFormulaContourKernel_at_trivialZero
    (n : ℕ) {x : ℝ} (hx : 0 < x) :
    let ρ : ℂ := -2 * (n + 1)
    Tendsto (fun s : ℂ ↦ (s - ρ) * explicitFormulaContourKernel x s)
      (𝓝[≠] ρ) (𝓝 (-explicitFormulaZeroKernel x ρ)) := by
  dsimp only
  let ρ : ℂ := -2 * (n + 1)
  have hρ0 : ρ ≠ 0 := by
    dsimp [ρ]
    exact mul_ne_zero (by norm_num) (by exact_mod_cast Nat.succ_ne_zero n)
  have hρ1 : ρ ≠ 1 := by
    intro h
    have hneg : ρ.re < 0 := by
      dsimp [ρ]
      norm_num
      positivity
    rw [h] at hneg
    norm_num at hneg
  have hlog : Tendsto (fun s : ℂ ↦ (s - ρ) * logDeriv riemannZeta s)
      (𝓝[≠] ρ) (𝓝 1) := by
    exact (analyticOn_riemannZeta ρ (by simpa using hρ1)).tendsto_mul_logDeriv_simple_zero
      (by simpa [ρ, Nat.cast_add, Nat.cast_one] using
        riemannZeta_neg_two_mul_nat_add_one n)
      (by simpa [ρ, Nat.cast_add, Nat.cast_one] using
        deriv_riemannZeta_neg_two_mul_nat_add_one_ne_zero n)
  have hweight : Tendsto (fun s : ℂ ↦ (x : ℂ) ^ s / s) (𝓝[≠] ρ)
      (𝓝 ((x : ℂ) ^ ρ / ρ)) := by
    exact ((continuousAt_const_cpow (Complex.ofReal_ne_zero.mpr hx.ne')).div
      continuousAt_id hρ0).tendsto.mono_left nhdsWithin_le_nhds
  have hproduct := hlog.neg.mul hweight
  simpa [explicitFormulaContourKernel, explicitFormulaZeroKernel, mul_assoc, ρ,
    sub_eq_add_neg] using hproduct

/-- The real residue term contributed by the trivial zero `-2(n+1)`. -/
noncomputable def trivialZeroResidueTerm (x : ℝ) (n : ℕ) : ℝ :=
  x⁻¹ ^ (2 * (n + 1)) / (2 * (n + 1))

/-- Complex form of the same residue, directly from the contour kernel. -/
noncomputable def trivialZeroContourResidue (x : ℝ) (n : ℕ) : ℂ :=
  -explicitFormulaZeroKernel x (-2 * (n + 1))

/-- For positive `x`, the complex contour residue is the real power-series
term embedded in `ℂ`. -/
theorem trivialZeroContourResidue_eq_ofReal {x : ℝ} (hx : 0 < x) (n : ℕ) :
    trivialZeroContourResidue x n = (trivialZeroResidueTerm x n : ℂ) := by
  unfold trivialZeroContourResidue explicitFormulaZeroKernel trivialZeroResidueTerm
  rw [show (-2 * (n + 1) : ℂ) = -(2 * (n + 1) : ℕ) by
    push_cast
    ring]
  rw [Complex.cpow_neg, Complex.cpow_natCast]
  push_cast
  rw [inv_pow]
  field_simp [Complex.ofReal_ne_zero.mpr hx.ne', Nat.succ_ne_zero n]

/-- The complete trivial-zero residue series is the classical logarithmic
correction in the Chebyshev explicit formula. -/
theorem hasSum_trivialZeroResidueTerm {x : ℝ} (hx : 1 < x) :
    HasSum (trivialZeroResidueTerm x)
      (-(1 / 2 : ℝ) * Real.log (1 - x⁻¹ ^ 2)) := by
  have hinv0 : 0 ≤ x⁻¹ := (inv_pos.mpr (lt_trans zero_lt_one hx)).le
  have hinv1 : x⁻¹ < 1 := inv_lt_one_of_one_lt₀ hx
  have hq0 : 0 ≤ x⁻¹ ^ 2 := sq_nonneg _
  have hq1 : x⁻¹ ^ 2 < 1 := pow_lt_one₀ hinv0 hinv1 (by norm_num)
  have hlog := Real.hasSum_pow_div_log_of_abs_lt_one
    (x := x⁻¹ ^ 2) (by simpa [abs_of_nonneg hq0] using hq1)
  have hscaled := hlog.mul_left (1 / 2 : ℝ)
  have hs : HasSum (trivialZeroResidueTerm x)
      ((1 / 2 : ℝ) * -Real.log (1 - x⁻¹ ^ 2)) := by
    apply hscaled.congr_fun
    intro n
    unfold trivialZeroResidueTerm
    rw [pow_mul]
    norm_num [Nat.cast_add, Nat.cast_mul]
    field_simp
  simpa only [mul_neg, neg_mul] using hs

/-- Tsum form of the evaluated trivial-zero residue contribution. -/
theorem tsum_trivialZeroResidueTerm {x : ℝ} (hx : 1 < x) :
    ∑' n : ℕ, trivialZeroResidueTerm x n =
      -(1 / 2 : ℝ) * Real.log (1 - x⁻¹ ^ 2) :=
  (hasSum_trivialZeroResidueTerm hx).tsum_eq

/-- Complex tsum form, matching the residues used by the contour theorem. -/
theorem tsum_trivialZeroContourResidue {x : ℝ} (hx : 1 < x) :
    ∑' n : ℕ, trivialZeroContourResidue x n =
      (-(1 / 2 : ℝ) * Real.log (1 - x⁻¹ ^ 2) : ℝ) := by
  rw [tsum_congr (trivialZeroContourResidue_eq_ofReal (lt_trans zero_lt_one hx)),
    ← Complex.ofReal_tsum]
  · rw [tsum_trivialZeroResidueTerm hx]

end RiemannLab
