import RiemannLab.Tasks.RiemannLiSequence
import Mathlib.Analysis.Calculus.IteratedDeriv.WithinZpow

namespace RiemannLab

open Complex
open scoped ArithmeticFunction.vonMangoldt LSeries.notation

/-!
# The literal completed arithmetic ledger for the Riemann Li sequence

The pole at `s = 1` prevents the prime Dirichlet series from being Taylor
expanded there term by term.  The correct object is its analytic finite part.
This file defines that finite part as the unique residual in the already
verified completed-xi identity.  On the half-plane of absolute convergence it
is exactly the von Mangoldt series minus the polar term.

This closes the bookkeeping problem without asserting the RH-level dominance
inequality.
-/

/-- The elementary pole contribution after the Li-disk pullback. -/
noncomputable def riemannLiPoleDiskFunction (z : ℂ) : ℂ :=
  1 / (1 - z)

/-- The completed archimedean contribution after the Li-disk pullback. -/
noncomputable def riemannLiArchimedeanDiskFunction (z : ℂ) : ℂ :=
  (1 - z)⁻¹ ^ 2 * logDeriv Gammaℝ (liDiskToHalfPlane z)

/-- The analytically continued finite-prime contribution.  It is defined as
the residual after the pole and Gamma terms are removed from the completed
xi logarithmic derivative. -/
noncomputable def riemannLiFinitePlaceDiskFunction (z : ℂ) : ℂ :=
  riemannLiArchimedeanDiskFunction z + riemannLiPoleDiskFunction z -
    riemannLiGeneratingDerivative z

/-- Exact completed ledger on the full Li disk wherever the expressions are
defined; no termwise prime expansion is used. -/
theorem riemannLiGeneratingDerivative_eq_places (z : ℂ) :
    riemannLiGeneratingDerivative z =
      riemannLiArchimedeanDiskFunction z -
        riemannLiFinitePlaceDiskFunction z +
          riemannLiPoleDiskFunction z := by
  simp only [riemannLiFinitePlaceDiskFunction]
  ring

/-- On the absolute-convergence side, the analytic finite-place residual is
literally the von Mangoldt series with the zeta pole subtracted. -/
theorem riemannLiFinitePlaceDiskFunction_eq_vonMangoldt
    {z : ℂ} (hz : 1 < (liDiskToHalfPlane z).re) :
    riemannLiFinitePlaceDiskFunction z =
      (1 - z)⁻¹ ^ 2 *
        (L ↗ArithmeticFunction.vonMangoldt (liDiskToHalfPlane z) -
          1 / (liDiskToHalfPlane z - 1)) := by
  have hz1 : z ≠ 1 := by
    intro h
    subst z
    simp [liDiskToHalfPlane] at hz
    linarith
  rw [riemannLiFinitePlaceDiskFunction, riemannLiGeneratingDerivative,
    completedLiDiskFunction_eq_primeGammaPole hz]
  unfold riemannLiArchimedeanDiskFunction riemannLiPoleDiskFunction
    primeGammaPoleDiskFunction
  dsimp only
  have hs : liDiskToHalfPlane z = 1 / (1 - z) := rfl
  rw [hs]
  field_simp [hz1]
  ring

/-- Real Taylor coefficient convention shared by all three places. -/
noncomputable def realLiDiskCoefficient (f : ℂ → ℂ) : ℕ → ℝ
  | 0 => 0
  | n + 1 => (iteratedDeriv n f 0 / (n.factorial : ℂ)).re

/-- Literal archimedean ledger sequence. -/
noncomputable def riemannLiSInfinity : ℕ → ℝ :=
  realLiDiskCoefficient riemannLiArchimedeanDiskFunction

/-- Literal finite-prime ledger sequence, defined by analytic continuation of
the regularized von Mangoldt expression. -/
noncomputable def riemannLiSFinite : ℕ → ℝ :=
  realLiDiskCoefficient riemannLiFinitePlaceDiskFunction

@[simp] theorem realLiDiskCoefficient_zero (f : ℂ → ℂ) :
    realLiDiskCoefficient f 0 = 0 := rfl

theorem iteratedDeriv_riemannLiPoleDiskFunction_zero (n : ℕ) :
    iteratedDeriv n riemannLiPoleDiskFunction 0 = (n.factorial : ℂ) := by
  have hdiv := iteratedDerivWithin_one_div (𝕜 := ℂ) n
    (s := Set.univ) isOpen_univ
  have hatOne := hdiv (show (1 : ℂ) ∈ Set.univ by simp)
  rw [iteratedDerivWithin_univ] at hatOne
  norm_num at hatOne
  have hshift := congrFun
    (iteratedDeriv_comp_const_sub n (fun w : ℂ ↦ 1 / w) 1) 0
  change iteratedDeriv n (fun z : ℂ ↦ 1 / (1 - z)) 0 = _
  rw [hshift]
  simp only [one_div] at hatOne ⊢
  rw [sub_zero, hatOne]
  simp only [smul_eq_mul]
  rw [← mul_assoc, ← mul_pow]
  simp

theorem realLiDiskCoefficient_pole (n : ℕ) :
    realLiDiskCoefficient riemannLiPoleDiskFunction n =
      if n = 0 then 0 else 1 := by
  cases n with
  | zero => simp
  | succ n =>
      simp only [realLiDiskCoefficient,
        iteratedDeriv_riemannLiPoleDiskFunction_zero, Nat.succ_ne_zero,
        ↓reduceIte]
      have hfac : (n.factorial : ℂ) ≠ 0 := by exact_mod_cast Nat.factorial_ne_zero n
      exact congrArg Complex.re (div_self hfac)

private theorem analyticAt_logDeriv_riemannXiEntire_one :
    AnalyticAt ℂ (logDeriv riemannXiEntire) 1 := by
  have hxi : AnalyticAt ℂ riemannXiEntire 1 := analyticAt_riemannXiEntire 1
  have hxi1 : riemannXiEntire 1 ≠ 0 := by
    simp [riemannXiEntire]
  exact hxi.deriv.div hxi hxi1

private theorem analyticAt_completedLiDiskFunction_zero :
    AnalyticAt ℂ completedLiDiskFunction 0 := by
  unfold completedLiDiskFunction liDiskToHalfPlane
  have hinner : AnalyticAt ℂ (fun z : ℂ ↦ 1 / (1 - z)) 0 := by
    exact analyticAt_const.div (analyticAt_const.sub analyticAt_id) (by norm_num)
  simpa [Function.comp_def, logDeriv_apply] using
    analyticAt_logDeriv_riemannXiEntire_one.comp_of_eq hinner (by norm_num)

private theorem analyticAt_riemannLiGeneratingDerivative_zero :
    AnalyticAt ℂ riemannLiGeneratingDerivative 0 := by
  unfold riemannLiGeneratingDerivative
  exact (by fun_prop : AnalyticAt ℂ (fun z : ℂ ↦ (1 - z)⁻¹ ^ 2) 0).mul
    analyticAt_completedLiDiskFunction_zero

private theorem analyticAt_riemannLiArchimedeanDiskFunction_zero :
    AnalyticAt ℂ riemannLiArchimedeanDiskFunction 0 := by
  unfold riemannLiArchimedeanDiskFunction liDiskToHalfPlane
  have hgamma : AnalyticAt ℂ Gammaℝ 1 := analyticAt_Gammaℝ_of_re_pos (by norm_num)
  have hgamma0 : Gammaℝ (1 : ℂ) ≠ 0 := Gammaℝ_ne_zero_of_re_pos (by norm_num)
  have hlog : AnalyticAt ℂ (logDeriv Gammaℝ) 1 :=
    hgamma.deriv.div hgamma hgamma0
  apply (by fun_prop : AnalyticAt ℂ (fun z : ℂ ↦ (1 - z)⁻¹ ^ 2) 0).mul
  have hinner : AnalyticAt ℂ (fun z : ℂ ↦ 1 / (1 - z)) 0 := by
    exact analyticAt_const.div (analyticAt_const.sub analyticAt_id) (by norm_num)
  simpa [Function.comp_def, logDeriv_apply] using
    hlog.comp_of_eq hinner (by norm_num)

private theorem analyticAt_riemannLiPoleDiskFunction_zero :
    AnalyticAt ℂ riemannLiPoleDiskFunction 0 := by
  unfold riemannLiPoleDiskFunction
  exact analyticAt_const.div (analyticAt_const.sub analyticAt_id) (by norm_num)

private theorem contDiffAt_riemannLiGeneratingDerivative_zero (n : ℕ) :
    ContDiffAt ℂ n riemannLiGeneratingDerivative 0 :=
  analyticAt_riemannLiGeneratingDerivative_zero.contDiffAt

private theorem contDiffAt_riemannLiArchimedeanDiskFunction_zero (n : ℕ) :
    ContDiffAt ℂ n riemannLiArchimedeanDiskFunction 0 :=
  analyticAt_riemannLiArchimedeanDiskFunction_zero.contDiffAt

private theorem contDiffAt_riemannLiPoleDiskFunction_zero (n : ℕ) :
    ContDiffAt ℂ n riemannLiPoleDiskFunction 0 :=
  analyticAt_riemannLiPoleDiskFunction_zero.contDiffAt

/-- The Taylor-defined Riemann Li coefficients satisfy the literal completed
Riemann ledger `S_infinity - S_f + 1`. -/
theorem riemannLiCoefficient_eq_arithmeticLedger (n : ℕ) :
    riemannLiCoefficient n =
      riemannLiSInfinity n - riemannLiSFinite n +
        (if n = 0 then 0 else 1) := by
  cases n with
  | zero => simp [riemannLiCoefficient, riemannLiSInfinity, riemannLiSFinite]
  | succ n =>
      have harch := contDiffAt_riemannLiArchimedeanDiskFunction_zero n
      have hpole := contDiffAt_riemannLiPoleDiskFunction_zero n
      have hfull := contDiffAt_riemannLiGeneratingDerivative_zero n
      have hfinite : ContDiffAt ℂ n riemannLiFinitePlaceDiskFunction 0 :=
        (harch.add hpole).sub hfull
      have hderiv := congrArg (fun f : ℂ → ℂ ↦ iteratedDeriv n f 0)
        (funext riemannLiGeneratingDerivative_eq_places)
      rw [iteratedDeriv_fun_add, iteratedDeriv_fun_sub] at hderiv
      · simp only [riemannLiCoefficient, riemannLiSInfinity,
          riemannLiSFinite, realLiDiskCoefficient]
        rw [hderiv, iteratedDeriv_riemannLiPoleDiskFunction_zero]
        have hfac : (n.factorial : ℂ) ≠ 0 := by
          exact_mod_cast Nat.factorial_ne_zero n
        have hc :
            (iteratedDeriv n riemannLiArchimedeanDiskFunction 0 -
                iteratedDeriv n riemannLiFinitePlaceDiskFunction 0 +
                (n.factorial : ℂ)) / (n.factorial : ℂ) =
              iteratedDeriv n riemannLiArchimedeanDiskFunction 0 /
                  (n.factorial : ℂ) -
                iteratedDeriv n riemannLiFinitePlaceDiskFunction 0 /
                  (n.factorial : ℂ) + 1 := by
          field_simp [hfac]
        simpa only [Complex.add_re, Complex.sub_re, Complex.one_re,
          Nat.succ_ne_zero, ↓reduceIte] using congrArg Complex.re hc
      · exact harch
      · exact hfinite
      · exact harch.sub hfinite
      · exact hpole

/-- The completed ledger as an instance of the minimal abstract arithmetic
decomposition. -/
noncomputable def riemannLiArithmeticDecomposition :
    LiArithmeticDecomposition riemannLiCoefficient where
  archimedean := riemannLiSInfinity
  finitePlace := riemannLiSFinite
  pole := fun n ↦ if n = 0 then 0 else 1
  identity := riemannLiCoefficient_eq_arithmeticLedger

/-- The sole remaining all-index inequality is exactly positivity of the
actual Taylor-defined Riemann Li sequence. -/
theorem riemannLiDominance_iff_positivity :
    riemannLiArithmeticDecomposition.HasDominance ↔ RiemannLiPositivity := by
  exact riemannLiArithmeticDecomposition.dominance_iff_sequence_nonneg

/-- Fully unfolded form of the remaining all-index arithmetic target. -/
theorem riemannLiArithmeticDominance_iff :
    (∀ n, riemannLiSFinite n ≤ riemannLiSInfinity n +
      (if n = 0 then 0 else 1)) ↔ RiemannLiPositivity := by
  change riemannLiArithmeticDecomposition.HasDominance ↔ RiemannLiPositivity
  exact riemannLiDominance_iff_positivity

/-- Any strict failure of the literal arithmetic inequality gives a finite
negative Fejer-prefix certificate. -/
theorem negative_riemannLiPrefix_of_arithmeticFailure
    {n : ℕ}
    (hfail : riemannLiSInfinity n + (if n = 0 then 0 else 1) <
      riemannLiSFinite n) :
    liPrefixEnergy riemannLiCoefficient n < 0 := by
  exact riemannLiArithmeticDecomposition.negative_prefix_of_dominance_failure
    riemannLiCoefficient_zero hfail

end RiemannLab
