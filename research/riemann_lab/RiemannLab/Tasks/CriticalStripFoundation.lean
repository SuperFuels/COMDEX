import Mathlib.NumberTheory.LSeries.Nonvanishing
import Mathlib.NumberTheory.LSeries.ZetaZeros

open scoped LSeries.notation

namespace RiemannLab

/-!
A kernel-checked foundation for critical-strip work. Every result here is a
reconstruction or direct consequence of established Mathlib mathematics. The
strict upper boundary for zeta zeros is useful infrastructure; it is not new
progress on the Riemann Hypothesis.
-/

theorem zeta_differentiable_away_from_one {s : ℂ} (hs : s ≠ 1) :
    DifferentiableAt ℂ riemannZeta s := by
  exact differentiableAt_riemannZeta hs

theorem zeta_differentiable_on_complement_one :
    DifferentiableOn ℂ riemannZeta {1}ᶜ := by
  exact differentiableOn_riemannZeta

theorem zeta_analytic_on_complement_one :
    AnalyticOnNhd ℂ riemannZeta {1}ᶜ := by
  exact analyticOn_riemannZeta

theorem zeta_special_value_zero : riemannZeta 0 = -(1 : ℂ) / 2 := by
  exact riemannZeta_zero

theorem zeta_trivial_zero_family (n : ℕ) :
    riemannZeta (-2 * ((n : ℂ) + 1)) = 0 := by
  exact riemannZeta_neg_two_mul_nat_add_one n

theorem zeta_nonzero_of_one_lt_re {s : ℂ} (hs : 1 < s.re) :
    riemannZeta s ≠ 0 := by
  exact riemannZeta_ne_zero_of_one_lt_re hs

theorem zeta_nonzero_of_one_le_re {s : ℂ} (hs : 1 ≤ s.re) :
    riemannZeta s ≠ 0 := by
  exact riemannZeta_ne_zero_of_one_le_re hs

theorem zeta_zero_re_lt_one {s : ℂ} (hz : riemannZeta s = 0) : s.re < 1 := by
  by_contra h
  exact riemannZeta_ne_zero_of_one_le_re (le_of_not_gt h) hz

theorem zeta_zero_re_le_one {s : ℂ} (hz : riemannZeta s = 0) : s.re ≤ 1 := by
  exact (zeta_zero_re_lt_one hz).le

theorem zeta_eq_dirichlet_series {s : ℂ} (hs : 1 < s.re) :
    L 1 s = riemannZeta s := by
  exact LSeries_one_eq_riemannZeta hs

theorem zeta_has_dirichlet_series_sum {s : ℂ} (hs : 1 < s.re) :
    LSeriesHasSum 1 s (riemannZeta s) := by
  exact LSeriesHasSum_one hs

theorem zeta_real_part_positive {x : ℝ} (hx : 1 < x) :
    0 < (riemannZeta x).re := by
  exact riemannZeta_re_pos_of_one_lt hx

theorem zeta_imaginary_part_zero {x : ℝ} (hx : 1 < x) :
    (riemannZeta x).im = 0 := by
  exact riemannZeta_im_eq_zero_of_one_lt hx

theorem zeta_zero_iff_mem {s : ℂ} :
    s ∈ riemannZetaZeros ↔ riemannZeta s = 0 := by
  exact mem_riemannZetaZeros

theorem zeta_zero_set_closed : IsClosed riemannZetaZeros := by
  exact isClosed_riemannZetaZeros

theorem zeta_zero_set_discrete : IsDiscrete riemannZetaZeros := by
  exact isDiscrete_riemannZetaZeros

theorem compact_inter_zeta_zeros_finite {S : Set ℂ} (hS : IsCompact S) :
    (S ∩ riemannZetaZeros).Finite := by
  exact hS.inter_riemannZetaZeros_finite

end RiemannLab
