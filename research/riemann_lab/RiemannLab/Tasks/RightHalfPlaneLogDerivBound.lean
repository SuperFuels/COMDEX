import RiemannLab.Tasks.AdmissibleHeights
import RiemannLab.Tasks.CriticalLineCriterion

namespace RiemannLab

open scoped ArithmeticFunction.vonMangoldt LSeries.notation

/-!
Uniform control of the zeta logarithmic derivative in every closed
right half-plane `Re(s) ≥ c > 1`.  This follows directly from absolute
convergence of the von Mangoldt Dirichlet series and supplies the easy side of
the later global contour estimate.
-/

/-- The absolutely convergent von Mangoldt majorant on `Re(s) = c > 1`. -/
noncomputable def vonMangoldtLogDerivMajorant (c : ℝ) : ℝ :=
  ∑' n : ℕ, ‖LSeries.term
    (↗ArithmeticFunction.vonMangoldt) (c : ℂ) n‖

theorem summable_vonMangoldtLogDerivMajorant {c : ℝ} (hc : 1 < c) :
    Summable (fun n : ℕ ↦ ‖LSeries.term
      (↗ArithmeticFunction.vonMangoldt) (c : ℂ) n‖) := by
  exact (ArithmeticFunction.LSeriesSummable_vonMangoldt
    (s := (c : ℂ)) (by simpa using hc)).norm

theorem vonMangoldtLogDerivMajorant_nonneg (c : ℝ) :
    0 ≤ vonMangoldtLogDerivMajorant c := by
  exact tsum_nonneg fun _ ↦ norm_nonneg _

/-- Absolute convergence makes `ζ'/ζ` uniformly bounded independently of the
imaginary part on `Re(s) ≥ c > 1`. -/
theorem norm_logDeriv_riemannZeta_le_majorant
    {c : ℝ} (hc : 1 < c) {s : ℂ} (hs : c ≤ s.re) :
    ‖logDeriv riemannZeta s‖ ≤ vonMangoldtLogDerivMajorant c := by
  have hs1 : 1 < s.re := hc.trans_le hs
  have hseries := vonMangoldt_LSeries_eq_zeta_logDeriv hs1
  have hsumS : Summable (fun n : ℕ ↦ ‖LSeries.term
      (↗ArithmeticFunction.vonMangoldt) s n‖) :=
    (ArithmeticFunction.LSeriesSummable_vonMangoldt hs1).norm
  have hsumC := summable_vonMangoldtLogDerivMajorant hc
  have hterm : ∀ n : ℕ,
      ‖LSeries.term (↗ArithmeticFunction.vonMangoldt) s n‖ ≤
        ‖LSeries.term (↗ArithmeticFunction.vonMangoldt) (c : ℂ) n‖ := by
    intro n
    exact LSeries.norm_term_le_of_re_le_re
      (↗ArithmeticFunction.vonMangoldt) (by simpa using hs) n
  have hL : ‖L (↗ArithmeticFunction.vonMangoldt) s‖ ≤
      vonMangoldtLogDerivMajorant c := by
    unfold LSeries vonMangoldtLogDerivMajorant
    exact (norm_tsum_le_tsum_norm hsumS).trans
      (hsumS.tsum_mono hsumC hterm)
  rw [logDeriv_apply]
  rw [hseries] at hL
  simpa only [neg_div, norm_neg] using hL

end RiemannLab
