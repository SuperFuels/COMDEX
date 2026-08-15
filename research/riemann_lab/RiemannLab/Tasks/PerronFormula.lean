import RiemannLab.Tasks.ExplicitFormula
import Mathlib.Analysis.MellinInversion
import Mathlib.Analysis.Complex.CauchyIntegral

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

/-- The exact specialized Perron inversion theorem still required.

For nonintegral `x > 1` and any vertical line `c > 1`, the normalized truncated
integral should converge to `Chebyshev.psi x`.  The nonintegrality condition
avoids a jump-value convention. -/
def ChebyshevPerronInversionTarget : Prop :=
  ∀ x c : ℝ, 1 < x → (∀ m : ℕ, x ≠ m) → 1 < c →
    Tendsto (fun T : ℝ ↦ truncatedZetaPerronIntegral c T x) atTop
      (𝓝 (Chebyshev.psi x : ℂ))

/-- Equivalent formulation of the open Perron target using the von Mangoldt
L-series integral.  The equivalence itself is kernel-checked from the finite
height identity above; neither side is asserted. -/
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
