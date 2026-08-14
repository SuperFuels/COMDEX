import Mathlib.NumberTheory.LSeries.Dirichlet

open Complex

namespace AionRiemannCatalogProbe

example : riemannZeta 0 = -(1 : ℂ) / 2 := by
  simpa using riemannZeta_zero

example (n : ℕ) : riemannZeta (-2 * ((n : ℂ) + 1)) = 0 := by
  simpa using riemannZeta_neg_two_mul_nat_add_one n

example (s : ℂ) (hs : 1 < s.re) : riemannZeta s ≠ 0 := by
  exact riemannZeta_ne_zero_of_one_lt_re hs

end AionRiemannCatalogProbe
