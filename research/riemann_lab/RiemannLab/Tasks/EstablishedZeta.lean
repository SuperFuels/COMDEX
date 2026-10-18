import Mathlib.NumberTheory.LSeries.RiemannZeta
import Mathlib.NumberTheory.LSeries.Dirichlet

namespace RiemannLab

/-!
Machine-checked reproduction targets. These are established Mathlib results and
are baselines for the research loop, not new progress on the Riemann Hypothesis.
-/

theorem reproduce_zeta_at_zero : riemannZeta 0 = -(1 : ℂ) / 2 := by
  exact riemannZeta_zero

theorem reproduce_trivial_zero (n : ℕ) :
    riemannZeta (-2 * ((n : ℂ) + 1)) = 0 := by
  exact riemannZeta_neg_two_mul_nat_add_one n

theorem reproduce_zero_free_right_half_plane {s : ℂ} (hs : 1 < s.re) :
    riemannZeta s ≠ 0 := by
  exact riemannZeta_ne_zero_of_one_lt_re hs

end RiemannLab
