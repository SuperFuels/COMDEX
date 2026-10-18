import RiemannLab.Tasks.ExplicitFormula
import RiemannLab.Tasks.FinitePerron
import Mathlib.Analysis.MellinInversion
import Mathlib.Analysis.Complex.CauchyIntegral
import Mathlib.Analysis.Normed.Group.Tannery

namespace RiemannLab

open Filter MeasureTheory
open scoped ArithmeticFunction.vonMangoldt LSeries.notation Interval Topology

/-!
The specialized Perron interface for the Chebyshev-psi route.

Pinned Mathlib contains general Mellin inversion and rectangle-integral
machinery, but no source-ready Perron theorem for an arithmetic Dirichlet
series.  This file defines the exact normalized finite-height integral, proves
its right-half-plane identification with the von Mangoldt L-series, and records
the remaining inversion limit as an open proposition rather than an axiom.
-/

/-- The logarithmic-derivative integrand used in Perron's formula. -/
noncomputable def zetaPerronKernel (x : ℝ) (s : ℂ) : ℂ :=
  (-deriv riemannZeta s / riemannZeta s) * (x : ℂ) ^ s / s

/-- The same Perron integrand expressed using the von Mangoldt L-series. -/
noncomputable def vonMangoldtPerronKernel (x : ℝ) (s : ℂ) : ℂ :=
  L ↗ArithmeticFunction.vonMangoldt s * (x : ℂ) ^ s / s

/-- The `n`th summand before passing from the absolutely convergent von
Mangoldt Dirichlet series to the Perron kernel. -/
noncomputable def vonMangoldtPerronSeriesTerm (x : ℝ) (s : ℂ) (n : ℕ) : ℂ :=
  LSeries.term ↗ArithmeticFunction.vonMangoldt s n * ((x : ℂ) ^ s / s)

/-- The first `N` terms of the von Mangoldt Perron kernel. -/
noncomputable def partialVonMangoldtPerronKernel
    (N : ℕ) (x : ℝ) (s : ℂ) : ℂ :=
  ∑ n ∈ Finset.range N, vonMangoldtPerronSeriesTerm x s n

/-- The Perron-kernel series is absolutely summable at each point of the
vertical half-plane `Re(s) > 1`. -/
theorem summable_vonMangoldtPerronSeriesTerm
    {x : ℝ} {s : ℂ} (hs : 1 < s.re) :
    Summable (vonMangoldtPerronSeriesTerm x s) := by
  unfold vonMangoldtPerronSeriesTerm
  exact (ArithmeticFunction.LSeriesSummable_vonMangoldt hs).mul_right _

/-- The absolutely convergent coefficient series sums pointwise to the
von Mangoldt Perron kernel on `Re(s) > 1`. -/
theorem hasSum_vonMangoldtPerronSeriesTerm
    {x : ℝ} {s : ℂ} (hs : 1 < s.re) :
    HasSum (vonMangoldtPerronSeriesTerm x s) (vonMangoldtPerronKernel x s) := by
  unfold vonMangoldtPerronSeriesTerm vonMangoldtPerronKernel
  simpa [LSeries, div_eq_mul_inv, mul_assoc] using
    (HasSum.mul_right ((x : ℂ) ^ s / s)
      (ArithmeticFunction.LSeriesSummable_vonMangoldt hs).hasSum)

/-- Partial von Mangoldt Perron kernels converge pointwise to the full kernel
throughout the half-plane of absolute convergence. The remaining global gate
is uniform domination strong enough to interchange this limit and the growing
vertical integral. -/
theorem tendsto_partialVonMangoldtPerronKernel
    {x : ℝ} {s : ℂ} (hs : 1 < s.re) :
    Tendsto (fun N : ℕ ↦ partialVonMangoldtPerronKernel N x s) atTop
      (nhds (vonMangoldtPerronKernel x s)) := by
  simpa [partialVonMangoldtPerronKernel] using
    (hasSum_vonMangoldtPerronSeriesTerm (x := x) hs).tendsto_sum_nat

/-- Every coefficient term is continuous along a positive vertical line. -/
theorem continuous_vonMangoldtPerronSeriesTerm_vertical
    {x c : ℝ} (hx : 0 < x) (hc : 0 < c) (n : ℕ) :
    Continuous (fun t : ℝ ↦
      vonMangoldtPerronSeriesTerm x (c + t * Complex.I) n) := by
  unfold vonMangoldtPerronSeriesTerm LSeries.term
  split_ifs with hn
  · simpa using (continuous_const : Continuous (fun _ : ℝ ↦ (0 : ℂ)))
  · have hnC : (n : ℂ) ≠ 0 := by exact_mod_cast hn
    have hxC : (x : ℂ) ≠ 0 := Complex.ofReal_ne_zero.mpr hx.ne'
    apply Continuous.mul
    · apply Continuous.div continuous_const
      · exact (continuous_id.const_cpow (Or.inl hnC)).comp (by fun_prop)
      · exact fun t ↦ Complex.cpow_ne_zero_iff.mpr (Or.inl hnC)
    · apply Continuous.div
      · exact (continuous_id.const_cpow (Or.inl hxC)).comp (by fun_prop)
      · fun_prop
      · intro t
        exact scalarPerron_vertical_ne_zero hc t

/-- A summable, height-independent majorant for each coefficient term on a
positive vertical line. -/
theorem norm_vonMangoldtPerronSeriesTerm_vertical_le
    {x c : ℝ} (hx : 0 < x) (hc : 0 < c) (n : ℕ) (t : ℝ) :
    ‖vonMangoldtPerronSeriesTerm x (c + t * Complex.I) n‖ ≤
      ‖LSeries.term ↗ArithmeticFunction.vonMangoldt (c : ℂ) n‖ *
        (x ^ c / c) := by
  unfold vonMangoldtPerronSeriesTerm
  rw [norm_mul, norm_div, Complex.norm_cpow_eq_rpow_re_of_pos hx]
  have hre : (c + t * Complex.I : ℂ).re = c := by simp
  rw [hre]
  have hterm :
      ‖LSeries.term ↗ArithmeticFunction.vonMangoldt
          (c + t * Complex.I) n‖ =
        ‖LSeries.term ↗ArithmeticFunction.vonMangoldt (c : ℂ) n‖ := by
    simp only [LSeries.norm_term_eq, Complex.add_re, Complex.ofReal_re,
      Complex.mul_re, Complex.ofReal_im, Complex.I_re, Complex.I_im,
      mul_zero, zero_mul, sub_zero, add_zero]
  rw [hterm]
  gcongr
  simpa using Complex.re_le_norm (c + t * Complex.I)

theorem summable_vonMangoldtPerronVerticalMajorant
    {x c : ℝ} (hc : 1 < c) :
    Summable (fun n : ℕ ↦
      ‖LSeries.term ↗ArithmeticFunction.vonMangoldt (c : ℂ) n‖ *
        (x ^ c / c)) := by
  have hs : LSeriesSummable ↗ArithmeticFunction.vonMangoldt (c : ℂ) :=
    ArithmeticFunction.LSeriesSummable_vonMangoldt (by simpa using hc)
  exact hs.norm.mul_right _

/-- At every fixed height, the absolutely convergent von Mangoldt coefficient
series may be integrated term by term along the Perron vertical segment. -/
theorem hasSum_intervalIntegral_vonMangoldtPerronSeriesTerm
    {x c T : ℝ} (hx : 0 < x) (hc : 1 < c) :
    HasSum
      (fun n : ℕ ↦ ∫ t in -T..T,
        vonMangoldtPerronSeriesTerm x (c + t * Complex.I) n)
      (∫ t in -T..T, vonMangoldtPerronKernel x (c + t * Complex.I)) := by
  apply intervalIntegral.hasSum_integral_of_dominated_convergence
    (fun n : ℕ ↦ fun _ : ℝ ↦
      ‖LSeries.term ↗ArithmeticFunction.vonMangoldt (c : ℂ) n‖ *
        (x ^ c / c))
  · intro n
    exact (continuous_vonMangoldtPerronSeriesTerm_vertical hx
      (lt_trans (by norm_num) hc) n).aestronglyMeasurable
  · intro n
    exact Filter.Eventually.of_forall fun t _ ↦
      norm_vonMangoldtPerronSeriesTerm_vertical_le hx
        (lt_trans (by norm_num) hc) n t
  · exact Filter.Eventually.of_forall fun _ _ ↦
      summable_vonMangoldtPerronVerticalMajorant hc
  · exact intervalIntegrable_const
  · exact Filter.Eventually.of_forall fun t _ ↦
      hasSum_vonMangoldtPerronSeriesTerm (x := x)
        (by simpa using hc)

/-- Complex powers respect division by a positive natural denominator when the
base is a positive real number. -/
theorem cpow_div_nat {x : ℝ} {n : ℕ} (hx : 0 < x) (hn : n ≠ 0) (s : ℂ) :
    ((x / n : ℝ) : ℂ) ^ s = (x : ℂ) ^ s / (n : ℂ) ^ s := by
  have hnpos : 0 < (n : ℝ) := by exact_mod_cast Nat.pos_of_ne_zero hn
  have hmul := Complex.mul_cpow_ofReal_nonneg
    (div_nonneg hx.le hnpos.le) hnpos.le s
  have hbase : (x / (n : ℝ)) * n = x := div_mul_cancel₀ x hnpos.ne'
  have hpow_ne : (n : ℂ) ^ s ≠ 0 :=
    Complex.cpow_ne_zero_iff.mpr (Or.inl (by exact_mod_cast hn))
  apply (eq_div_iff hpow_ne).2
  calc
    ((x / n : ℝ) : ℂ) ^ s * (n : ℂ) ^ s =
        ((((x / n : ℝ) : ℂ) * (n : ℂ)) ^ s) := by
          simpa using hmul.symm
    _ = (x : ℂ) ^ s := by
      congr 1
      exact_mod_cast hbase

/-- A nonzero von Mangoldt Perron coefficient is exactly a scalar Perron
kernel with base `x / n`. -/
theorem vonMangoldtPerronSeriesTerm_vertical_eq_scalar
    {x c t : ℝ} {n : ℕ} (hx : 0 < x) (hn : n ≠ 0) :
    vonMangoldtPerronSeriesTerm x (c + t * Complex.I) n =
      (Λ n : ℂ) * scalarPerronKernel c (x / n) t := by
  unfold vonMangoldtPerronSeriesTerm scalarPerronKernel
  rw [LSeries.term_of_ne_zero hn, cpow_div_nat hx hn]
  ring

/-- The normalized vertical integral of one von Mangoldt coefficient term. -/
noncomputable def normalizedVonMangoldtPerronTermIntegral
    (c T x : ℝ) (n : ℕ) : ℂ :=
  (1 / (2 * (Real.pi : ℂ))) *
    ∫ t in -T..T, vonMangoldtPerronSeriesTerm x (c + t * Complex.I) n

theorem normalizedVonMangoldtPerronTermIntegral_eq_scalar
    {c T x : ℝ} {n : ℕ} (hx : 0 < x) (hn : n ≠ 0) :
    normalizedVonMangoldtPerronTermIntegral c T x n =
      (Λ n : ℂ) * scalarTruncatedPerronIntegral c (x / n) T := by
  unfold normalizedVonMangoldtPerronTermIntegral scalarTruncatedPerronIntegral
  rw [intervalIntegral.integral_congr
    (fun t _ ↦ vonMangoldtPerronSeriesTerm_vertical_eq_scalar hx hn)]
  rw [intervalIntegral.integral_const_mul]
  ring

/-- Uniform-in-height bound for the scalar Perron truncation away from its
jump. This is the analytic input for Tannery domination of the coefficient
series. -/
theorem norm_scalarTruncatedPerronIntegral_le
    {c y T : ℝ} (hc : 0 < c) (hy : 0 < y) (hy1 : y ≠ 1) :
    ‖scalarTruncatedPerronIntegral c y T‖ ≤
      Real.exp (Real.log y * c) *
        ((2 * Real.pi)⁻¹ *
          (|Real.log y|⁻¹ * (2 * c⁻¹ + c⁻¹ * Real.pi))) := by
  rw [scalarTruncatedPerronIntegral_eq_logarithmic hy,
    logarithmicTruncatedPerronIntegral_eq_exp_mul, norm_mul,
    Complex.norm_real, Real.norm_eq_abs, abs_of_pos (Real.exp_pos _)]
  gcongr
  unfold oscillatoryTruncatedCauchyIntegral
  rw [norm_mul]
  have hconst : ‖(1 / (2 * (Real.pi : ℂ)) : ℂ)‖ = (2 * Real.pi)⁻¹ := by
    rw [norm_div, norm_one, norm_mul, Complex.norm_real, Real.norm_eq_abs,
      abs_of_pos Real.pi_pos]
    norm_num
  rw [hconst]
  gcongr
  exact norm_integral_oscillatoryCauchyKernel_le hc
    (by rw [Real.log_ne_zero]; exact ⟨hy.ne', hy1, by linarith⟩)

theorem eventually_inv_abs_log_div_nat_le_one {x : ℝ} (hx : 0 < x) :
    ∀ᶠ n : ℕ in atTop, |Real.log (x / n)|⁻¹ ≤ 1 := by
  obtain ⟨N : ℕ, hN⟩ := exists_nat_gt (x * Real.exp 1)
  filter_upwards [eventually_ge_atTop N] with n hn
  have hnlarge : x * Real.exp 1 < (n : ℝ) :=
    hN.trans_le (by exact_mod_cast hn)
  have hnpos : (0 : ℝ) < n :=
    lt_trans (mul_pos hx (Real.exp_pos 1)) hnlarge
  have hratio_pos : 0 < x / (n : ℝ) := div_pos hx hnpos
  have hratio : x / (n : ℝ) < Real.exp (-1) := by
    rw [div_lt_iff₀ hnpos]
    have hdiv : x < (n : ℝ) / Real.exp 1 :=
      (lt_div_iff₀ (Real.exp_pos 1)).2 hnlarge
    simpa [Real.exp_neg, div_eq_mul_inv, mul_comm] using hdiv
  have hlog : Real.log (x / (n : ℝ)) < -1 :=
    (Real.log_lt_iff_lt_exp hratio_pos).2 hratio
  apply inv_le_one_of_one_le₀
  rw [le_abs]
  exact Or.inr (by linarith)

/-- The coefficientwise Tannery majorant obtained from the uniform scalar
Dirichlet bound. -/
noncomputable def perronCoefficientMajorant (c x : ℝ) (n : ℕ) : ℝ :=
  if n = 0 then 0 else
    ‖(Λ n : ℂ)‖ * ‖(((x / n : ℝ) : ℂ) ^ (c : ℂ))‖ *
      ((2 * Real.pi)⁻¹ *
        (|Real.log (x / n)|⁻¹ * (2 * c⁻¹ + c⁻¹ * Real.pi)))

theorem perronCoefficientMajorant_nonneg
    {c x : ℝ} (hc : 0 < c) (_hx : 0 < x) (n : ℕ) :
    0 ≤ perronCoefficientMajorant c x n := by
  unfold perronCoefficientMajorant
  split_ifs
  · rfl
  · positivity

theorem summable_perronCoefficientMajorant
    {c x : ℝ} (hc : 1 < c) (hx : 0 < x) :
    Summable (perronCoefficientMajorant c x) := by
  let C : ℝ := ‖(x : ℂ) ^ (c : ℂ)‖ *
    ((2 * Real.pi)⁻¹ * (2 * c⁻¹ + c⁻¹ * Real.pi))
  have hs : LSeriesSummable ↗ArithmeticFunction.vonMangoldt (c : ℂ) :=
    ArithmeticFunction.LSeriesSummable_vonMangoldt (by simpa using hc)
  have hsum : Summable (fun n : ℕ ↦
      ‖LSeries.term ↗ArithmeticFunction.vonMangoldt (c : ℂ) n‖ * C) :=
    hs.norm.mul_right C
  apply hsum.of_norm_bounded_eventually
  rw [Nat.cofinite_eq_atTop]
  filter_upwards [eventually_inv_abs_log_div_nat_le_one hx] with n hlog
  by_cases hn : n = 0
  · subst n
    simp [perronCoefficientMajorant]
  · have hcpow := cpow_div_nat hx hn (c : ℂ)
    have hcoeff :
        ‖(Λ n : ℂ)‖ * ‖(((x / n : ℝ) : ℂ) ^ (c : ℂ))‖ =
          ‖LSeries.term ↗ArithmeticFunction.vonMangoldt (c : ℂ) n‖ *
            ‖(x : ℂ) ^ (c : ℂ)‖ := by
      rw [LSeries.term_of_ne_zero hn, hcpow, norm_div, norm_div]
      ring
    rw [Real.norm_eq_abs, abs_of_nonneg (perronCoefficientMajorant_nonneg
      (lt_trans (by norm_num) hc) hx n)]
    unfold perronCoefficientMajorant
    rw [if_neg hn, hcoeff]
    unfold C
    have hK : 0 ≤ (2 * Real.pi)⁻¹ *
        (2 * c⁻¹ + c⁻¹ * Real.pi) := by positivity
    calc
      ‖LSeries.term ↗ArithmeticFunction.vonMangoldt (c : ℂ) n‖ *
          ‖(x : ℂ) ^ (c : ℂ)‖ *
          ((2 * Real.pi)⁻¹ *
            (|Real.log (x / n)|⁻¹ * (2 * c⁻¹ + c⁻¹ * Real.pi))) =
        ‖LSeries.term ↗ArithmeticFunction.vonMangoldt (c : ℂ) n‖ *
          ‖(x : ℂ) ^ (c : ℂ)‖ *
          (|Real.log (x / n)|⁻¹ *
            ((2 * Real.pi)⁻¹ * (2 * c⁻¹ + c⁻¹ * Real.pi))) := by ring
      _ ≤ ‖LSeries.term ↗ArithmeticFunction.vonMangoldt (c : ℂ) n‖ *
          ‖(x : ℂ) ^ (c : ℂ)‖ * (1 *
            ((2 * Real.pi)⁻¹ * (2 * c⁻¹ + c⁻¹ * Real.pi))) := by
        gcongr
      _ = ‖LSeries.term ↗ArithmeticFunction.vonMangoldt (c : ℂ) n‖ *
          (‖(x : ℂ) ^ (c : ℂ)‖ *
            ((2 * Real.pi)⁻¹ * (2 * c⁻¹ + c⁻¹ * Real.pi))) := by ring

theorem norm_normalizedVonMangoldtPerronTermIntegral_le_majorant
    {c T x : ℝ} (hc : 0 < c) (hx : 0 < x)
    (hnotnat : ∀ n : ℕ, x ≠ n) (n : ℕ) :
    ‖normalizedVonMangoldtPerronTermIntegral c T x n‖ ≤
      perronCoefficientMajorant c x n := by
  by_cases hn : n = 0
  · subst n
    simp [normalizedVonMangoldtPerronTermIntegral,
      vonMangoldtPerronSeriesTerm, LSeries.term, perronCoefficientMajorant]
  · have hnpos : (0 : ℝ) < n := by exact_mod_cast Nat.pos_of_ne_zero hn
    have hy : 0 < x / (n : ℝ) := div_pos hx hnpos
    have hy1 : x / (n : ℝ) ≠ 1 := by
      intro h
      have : x = n := (div_eq_one_iff_eq (by exact_mod_cast hn)).mp h
      exact hnotnat n this
    rw [normalizedVonMangoldtPerronTermIntegral_eq_scalar hx hn, norm_mul]
    unfold perronCoefficientMajorant
    rw [if_neg hn]
    have hexp : Real.exp (Real.log (x / (n : ℝ)) * c) =
        ‖(((x / n : ℝ) : ℂ) ^ (c : ℂ))‖ := by
      rw [Complex.norm_cpow_eq_rpow_re_of_pos hy]
      simp only [Complex.ofReal_re, Real.rpow_def_of_pos hy]
    rw [← hexp]
    simpa [mul_assoc] using mul_le_mul_of_nonneg_left
      (norm_scalarTruncatedPerronIntegral_le (T := T) hc hy hy1)
      (norm_nonneg (Λ n : ℂ))

/-- The sharp-cutoff limit of the `n`th normalized coefficient integral. -/
noncomputable def vonMangoldtPerronStepTerm (x : ℝ) (n : ℕ) : ℂ :=
  if (n : ℝ) < x then (Λ n : ℂ) else 0

theorem tendsto_normalizedVonMangoldtPerronTermIntegral
    {c x : ℝ} (hc : 0 < c) (hx : 0 < x)
    (hnotnat : ∀ n : ℕ, x ≠ n) (n : ℕ) :
    Tendsto (fun T : ℝ ↦ normalizedVonMangoldtPerronTermIntegral c T x n)
      atTop (nhds (vonMangoldtPerronStepTerm x n)) := by
  by_cases hn : n = 0
  · subst n
    simp [normalizedVonMangoldtPerronTermIntegral,
      vonMangoldtPerronSeriesTerm, LSeries.term, vonMangoldtPerronStepTerm, hx]
  · have hy := div_nat_pos hx hn
    have hy1 : x / (n : ℝ) ≠ 1 := by
      intro h
      have : x = n := (div_eq_one_iff_eq (by exact_mod_cast hn)).mp h
      exact hnotnat n this
    have hscalar := scalarPerronLimitTarget c (x / n) hc hy hy1
    have hmul := hscalar.const_mul (Λ n : ℂ)
    have hvalue : (Λ n : ℂ) * (if 1 < x / (n : ℝ) then 1 else 0) =
        vonMangoldtPerronStepTerm x n := by
      simp only [vonMangoldtPerronStepTerm, div_nat_gt_one_iff hn,
        mul_ite, mul_one, mul_zero]
    rw [hvalue] at hmul
    refine hmul.congr' ?_
    filter_upwards with T
    rw [normalizedVonMangoldtPerronTermIntegral_eq_scalar hx hn]

theorem tsum_vonMangoldtPerronStepTerm_eq_psi
    {x : ℝ} (hx : 0 < x) (hnotnat : ∀ n : ℕ, x ≠ n) :
    ∑' n : ℕ, vonMangoldtPerronStepTerm x n = (Chebyshev.psi x : ℂ) := by
  rw [tsum_eq_sum (s := Finset.Ioc 0 ⌊x⌋₊)]
  · rw [Chebyshev.psi]
    push_cast
    apply Finset.sum_congr rfl
    intro n hn
    unfold vonMangoldtPerronStepTerm
    rw [if_pos]
    have hnle : (n : ℝ) ≤ x :=
      (Nat.le_floor_iff hx.le).1 (Finset.mem_Ioc.1 hn).2
    exact lt_of_le_of_ne hnle (Ne.symm (hnotnat n))
  · intro n hnS
    unfold vonMangoldtPerronStepTerm
    by_cases hn0 : n = 0
    · subst n
      simp
    · rw [if_neg]
      intro hlt
      apply hnS
      exact Finset.mem_Ioc.2 ⟨Nat.pos_of_ne_zero hn0,
        (Nat.le_floor_iff hx.le).2 hlt.le⟩

/-- On the half-plane of absolute convergence, the two Perron kernels agree. -/
theorem vonMangoldtPerronKernel_eq_zeta {x : ℝ} {s : ℂ} (hs : 1 < s.re) :
    vonMangoldtPerronKernel x s = zetaPerronKernel x s := by
  rw [vonMangoldtPerronKernel, zetaPerronKernel,
    vonMangoldt_LSeries_eq_zeta_logDeriv hs]

/-- The normalized finite-height vertical integral
`(2 * pi * i)⁻¹ ∫ zetaPerronKernel x s ds`, parametrized by `s = c + it`.
The factor `i` from `ds = i dt` cancels the `i` in the normalization. -/
noncomputable def truncatedZetaPerronIntegral (c T x : ℝ) : ℂ :=
  (1 / (2 * (Real.pi : ℂ))) *
    ∫ t in -T..T, zetaPerronKernel x (c + t * Complex.I)

/-- The corresponding finite-height integral written with the von Mangoldt
Dirichlet series. -/
noncomputable def truncatedVonMangoldtPerronIntegral (c T x : ℝ) : ℂ :=
  (1 / (2 * (Real.pi : ℂ))) *
    ∫ t in -T..T, vonMangoldtPerronKernel x (c + t * Complex.I)

/-- The full finite-height Perron integral is the sum of the normalized
coefficient integrals. -/
theorem hasSum_normalizedVonMangoldtPerronTermIntegral
    {c T x : ℝ} (hx : 0 < x) (hc : 1 < c) :
    HasSum (normalizedVonMangoldtPerronTermIntegral c T x)
      (truncatedVonMangoldtPerronIntegral c T x) := by
  have h := hasSum_intervalIntegral_vonMangoldtPerronSeriesTerm
    (x := x) (T := T) hx hc
  unfold normalizedVonMangoldtPerronTermIntegral
  unfold truncatedVonMangoldtPerronIntegral
  exact HasSum.mul_left (1 / (2 * (Real.pi : ℂ))) h

theorem tsum_normalizedVonMangoldtPerronTermIntegral
    {c T x : ℝ} (hx : 0 < x) (hc : 1 < c) :
    ∑' n : ℕ, normalizedVonMangoldtPerronTermIntegral c T x n =
      truncatedVonMangoldtPerronIntegral c T x :=
  (hasSum_normalizedVonMangoldtPerronTermIntegral hx hc).tsum_eq

/-- Tannery domination interchanges the infinite coefficient sum with the
sharp height limit. -/
theorem tendsto_tsum_normalizedVonMangoldtPerronTermIntegral
    {c x : ℝ} (hc : 1 < c) (hx : 0 < x)
    (hnotnat : ∀ n : ℕ, x ≠ n) :
    Tendsto
      (fun T : ℝ ↦ ∑' n : ℕ,
        normalizedVonMangoldtPerronTermIntegral c T x n)
      atTop (nhds (Chebyshev.psi x : ℂ)) := by
  have h := tendsto_tsum_of_dominated_convergence
    (summable_perronCoefficientMajorant hc hx)
    (tendsto_normalizedVonMangoldtPerronTermIntegral
      (c := c) (x := x) (lt_trans (by norm_num) hc) hx hnotnat)
    (Filter.Eventually.of_forall fun T n ↦
      norm_normalizedVonMangoldtPerronTermIntegral_le_majorant
        (lt_trans (by norm_num) hc) hx hnotnat n)
  rw [tsum_vonMangoldtPerronStepTerm_eq_psi hx hnotnat] at h
  exact h

/-- Full von Mangoldt Perron inversion on `Re(s) > 1`, away from integer jump
points. -/
theorem tendsto_truncatedVonMangoldtPerronIntegral
    {c x : ℝ} (hc : 1 < c) (hx : 0 < x)
    (hnotnat : ∀ n : ℕ, x ≠ n) :
    Tendsto (fun T : ℝ ↦ truncatedVonMangoldtPerronIntegral c T x) atTop
      (nhds (Chebyshev.psi x : ℂ)) := by
  have h := tendsto_tsum_normalizedVonMangoldtPerronTermIntegral hc hx hnotnat
  apply h.congr'
  exact Filter.Eventually.of_forall fun T ↦
    tsum_normalizedVonMangoldtPerronTermIntegral hx hc

/-- Every point of the vertical line `c + it` stays in the half-plane of
absolute convergence when `c > 1`. -/
theorem verticalLine_re_gt_one {c t : ℝ} (hc : 1 < c) :
    1 < (c + t * Complex.I : ℂ).re := by
  simpa using hc

/-- At every finite height, the zeta and von Mangoldt forms of the normalized
Perron integral are exactly equal. -/
theorem truncatedVonMangoldtPerronIntegral_eq_zeta {c T x : ℝ} (hc : 1 < c) :
    truncatedVonMangoldtPerronIntegral c T x =
      truncatedZetaPerronIntegral c T x := by
  unfold truncatedVonMangoldtPerronIntegral truncatedZetaPerronIntegral
  congr 1
  apply intervalIntegral.integral_congr
  intro t _
  exact vonMangoldtPerronKernel_eq_zeta (verticalLine_re_gt_one hc)

@[simp]
theorem truncatedZetaPerronIntegral_zero_height (c x : ℝ) :
    truncatedZetaPerronIntegral c 0 x = 0 := by
  simp [truncatedZetaPerronIntegral]

@[simp]
theorem truncatedVonMangoldtPerronIntegral_zero_height (c x : ℝ) :
    truncatedVonMangoldtPerronIntegral c 0 x = 0 := by
  simp [truncatedVonMangoldtPerronIntegral]

/-- The exact specialized Perron inversion statement.

For nonintegral `x > 1` and any vertical line `c > 1`, the normalized truncated
integral converges to `Chebyshev.psi x`.  The nonintegrality condition
avoids a jump-value convention. -/
def ChebyshevPerronInversionTarget : Prop :=
  ∀ x c : ℝ, 1 < x → (∀ m : ℕ, x ≠ m) → 1 < c →
    Tendsto (fun T : ℝ ↦ truncatedZetaPerronIntegral c T x) atTop
      (𝓝 (Chebyshev.psi x : ℂ))

/-- The complete specialized Chebyshev Perron inversion theorem. -/
theorem chebyshevPerronInversion : ChebyshevPerronInversionTarget := by
  intro x c hx hnotnat hc
  have h := tendsto_truncatedVonMangoldtPerronIntegral hc
    (lt_trans (by norm_num) hx) hnotnat
  simpa only [truncatedVonMangoldtPerronIntegral_eq_zeta hc] using h

/-- Equivalent formulation of Perron inversion using the von Mangoldt
L-series integral. -/
theorem chebyshevPerronInversionTarget_iff_vonMangoldt :
    ChebyshevPerronInversionTarget ↔
      ∀ x c : ℝ, 1 < x → (∀ m : ℕ, x ≠ m) → 1 < c →
        Tendsto (fun T : ℝ ↦ truncatedVonMangoldtPerronIntegral c T x) atTop
          (𝓝 (Chebyshev.psi x : ℂ)) := by
  constructor
  · intro h x c hx hxi hc
    simpa only [truncatedVonMangoldtPerronIntegral_eq_zeta hc] using h x c hx hxi hc
  · intro h x c hx hxi hc
    simpa only [truncatedVonMangoldtPerronIntegral_eq_zeta hc] using h x c hx hxi hc

end RiemannLab
