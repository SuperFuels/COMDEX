import RiemannLab.Tasks.LiUniversalPositiveKernel
import RiemannLab.Tasks.XiZetaMultiplicity
import RiemannLab.Tasks.CriticalLineCriterion
import Mathlib.Analysis.SpecialFunctions.Gamma.Digamma

namespace RiemannLab

open Filter Topology Complex
open scoped ArithmeticFunction.vonMangoldt LSeries.notation

/-!
# Exact completed-xi logarithmic-derivative ledger

This is the analytic normalization required by the Carathéodory target.  In
the absolute-convergence half-plane it separates the completed logarithmic
derivative into elementary, archimedean, and prime terms.  No positivity is
asserted.
-/

/-- The standard factorization of the entire xi function holds on a full
neighborhood of every point in the half-plane `Re s > 1`. -/
theorem riemannXiEntire_eventuallyEq_factorization_of_one_lt_re
    {s : ℂ} (hs : 1 < s.re) :
    riemannXiEntire =ᶠ[nhds s]
      fun z ↦ ((z * (z - 1)) * Gammaℝ z) * riemannZeta z := by
  have hopen : IsOpen {z : ℂ | 1 < z.re} :=
    isOpen_lt continuous_const continuous_re
  filter_upwards [hopen.mem_nhds hs] with z hz
  exact riemannXiEntire_eq_mul_GammaR_riemannZeta
    (ne_zero_of_re_pos (zero_lt_one.trans hz))
    (by
      intro h
      have hre := congrArg Complex.re h
      norm_num at hre
      linarith)
    (zero_lt_one.trans hz)

/-- Exact four-place logarithmic-derivative decomposition on `Re s > 1`. -/
theorem logDeriv_riemannXiEntire_eq_places
    {s : ℂ} (hs : 1 < s.re) :
    logDeriv riemannXiEntire s =
      1 / s + 1 / (s - 1) + logDeriv Gammaℝ s +
        logDeriv riemannZeta s := by
  have hs0 : s ≠ 0 := ne_zero_of_re_pos (zero_lt_one.trans hs)
  have hs1 : s ≠ 1 := by
    intro h
    have hre := congrArg Complex.re h
    norm_num at hre
    linarith
  have hgamma0 : Gammaℝ s ≠ 0 :=
    Gammaℝ_ne_zero_of_re_pos (zero_lt_one.trans hs)
  have hzeta0 : riemannZeta s ≠ 0 := riemannZeta_ne_zero_of_one_lt_re hs
  have hgammaDiff : DifferentiableAt ℂ Gammaℝ s :=
    (analyticAt_Gammaℝ_of_re_pos (zero_lt_one.trans hs)).differentiableAt
  have hzetaDiff : DifferentiableAt ℂ riemannZeta s :=
    differentiableAt_riemannZeta hs1
  have heq := riemannXiEntire_eventuallyEq_factorization_of_one_lt_re hs
  have hlogeq : logDeriv riemannXiEntire s =
      logDeriv (fun z ↦ ((z * (z - 1)) * Gammaℝ z) * riemannZeta z) s := by
    simp only [logDeriv_apply, heq.deriv_eq, heq.eq_of_nhds]
  rw [hlogeq]
  rw [logDeriv_mul (f := fun z ↦ (z * (z - 1)) * Gammaℝ z)
      (g := riemannZeta) s
      (mul_ne_zero (mul_ne_zero hs0 (sub_ne_zero.mpr hs1)) hgamma0)
      hzeta0
      (((differentiableAt_id.mul (by fun_prop)).mul hgammaDiff))
      hzetaDiff]
  rw [logDeriv_mul (f := fun z ↦ z * (z - 1)) (g := Gammaℝ) s
      (mul_ne_zero hs0 (sub_ne_zero.mpr hs1)) hgamma0
      (differentiableAt_id.mul (by fun_prop)) hgammaDiff]
  rw [logDeriv_mul (f := fun z : ℂ ↦ z) (g := fun z ↦ z - 1) s
      hs0 (sub_ne_zero.mpr hs1)
      differentiableAt_id (by fun_prop)]
  simp [logDeriv_apply]

/-- Prime--Gamma--pole form of the same identity.  The prime term is the
von Mangoldt Dirichlet series and enters with a minus sign. -/
theorem logDeriv_riemannXiEntire_eq_primeGammaPole
    {s : ℂ} (hs : 1 < s.re) :
    logDeriv riemannXiEntire s =
      1 / s + 1 / (s - 1) + logDeriv Gammaℝ s -
        L ↗ArithmeticFunction.vonMangoldt s := by
  rw [logDeriv_riemannXiEntire_eq_places hs]
  have hvm := vonMangoldt_LSeries_eq_zeta_logDeriv hs
  have hlog : logDeriv riemannZeta s =
      -L ↗ArithmeticFunction.vonMangoldt s := by
    rw [logDeriv_apply, div_eq_mul_inv]
    rw [div_eq_mul_inv] at hvm
    calc
      deriv riemannZeta s * (riemannZeta s)⁻¹ =
          -(-deriv riemannZeta s * (riemannZeta s)⁻¹) := by ring
      _ = -L ↗ArithmeticFunction.vonMangoldt s := by rw [hvm]
  rw [hlog]
  ring

/-! ## Pullback to the Li disk -/

/-- The Möbius map used by the Li generating function.  It sends the open
unit disk to the half-plane `Re s > 1/2`. -/
noncomputable def liDiskToHalfPlane (z : ℂ) : ℂ :=
  1 / (1 - z)

/-- The completed logarithmic derivative in Li-disk coordinates. -/
noncomputable def completedLiDiskFunction (z : ℂ) : ℂ :=
  logDeriv riemannXiEntire (liDiskToHalfPlane z)

/-- The prime--Gamma--pole expression in the same coordinates.  Its
Dirichlet-series interpretation is used only where the mapped point has real
part greater than one. -/
noncomputable def primeGammaPoleDiskFunction (z : ℂ) : ℂ :=
  let s := liDiskToHalfPlane z
  1 / s + 1 / (s - 1) + logDeriv Gammaℝ s -
    L ↗ArithmeticFunction.vonMangoldt s

/-- Exact arithmetic normalization on the absolute-convergence portion of
the Li disk. -/
theorem completedLiDiskFunction_eq_primeGammaPole
    {z : ℂ} (hz : 1 < (liDiskToHalfPlane z).re) :
    completedLiDiskFunction z = primeGammaPoleDiskFunction z := by
  exact logDeriv_riemannXiEntire_eq_primeGammaPole hz

/-- The real part of the disk-to-half-plane map, written without complex
division.  This makes the restricted domain of the prime series explicit. -/
theorem liDiskToHalfPlane_re (z : ℂ) :
    (liDiskToHalfPlane z).re =
      (1 - z.re) / ((1 - z.re) ^ 2 + z.im ^ 2) := by
  rw [liDiskToHalfPlane, one_div, Complex.inv_re]
  simp only [Complex.sub_re, Complex.one_re, Complex.sub_im, Complex.one_im,
    zero_sub, Complex.normSq_apply]
  ring

end RiemannLab
