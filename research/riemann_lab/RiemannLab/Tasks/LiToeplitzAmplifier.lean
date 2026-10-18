import RiemannLab.Tasks.LiToeplitzQuartet

namespace RiemannLab

open ComplexConjugate

/-!
# A damped Chebyshev amplifier for an off-critical Li quartet

The seed `z² - a z + 1` gives the exact three-coordinate defect from
`LiToeplitzQuartet`. Multiplying it by an even power of `1-z` suppresses
high zeros, while `1+z^(2M)` supplies a sparse oscillatory localizer.

This file locks the exact reciprocal-product factorization. It contains no
assumption about the location of the zeta zeros.
-/

/-- The finite polynomial used by the first spectral-amplifier search. -/
noncomputable def liToeplitzAmplifier
    (a : ℂ) (damping mode : ℕ) (z : ℂ) : ℂ :=
  (z ^ 2 - a * z + 1) *
    (1 - z) ^ (2 * damping) *
    (1 + z ^ (2 * mode))

/-- The seed factor evaluated at reciprocal points depends only on
`u = z + z⁻¹`: it is exactly `(u-a)²`. -/
theorem liToeplitzAmplifier_seed_mul_inv
    (a z : ℂ) (hz : z ≠ 0) :
    (z ^ 2 - a * z + 1) *
        ((z⁻¹) ^ 2 - a * z⁻¹ + 1) =
      (z + z⁻¹ - a) ^ 2 := by
  field_simp [hz]
  ring

/-- The even damping factor also collapses to a polynomial in the reciprocal
coordinate `u`: its product is `(2-u)^(2r)`. -/
theorem liToeplitzAmplifier_damping_mul_inv
    (damping : ℕ) (z : ℂ) (hz : z ≠ 0) :
    (1 - z) ^ (2 * damping) *
        (1 - z⁻¹) ^ (2 * damping) =
      (2 - (z + z⁻¹)) ^ (2 * damping) := by
  rw [← mul_pow]
  congr 1
  field_simp [hz]
  ring

/-- Exact reciprocal-product factorization of the complete amplifier. The
three factors respectively encode the off-line defect, height damping, and
oscillatory localization. -/
theorem liToeplitzAmplifier_mul_inv
    (a z : ℂ) (damping mode : ℕ) (hz : z ≠ 0) :
    liToeplitzAmplifier a damping mode z *
        liToeplitzAmplifier a damping mode z⁻¹ =
      (z + z⁻¹ - a) ^ 2 *
        (2 - (z + z⁻¹)) ^ (2 * damping) *
        ((1 + z ^ (2 * mode)) *
          (1 + (z⁻¹) ^ (2 * mode))) := by
  unfold liToeplitzAmplifier
  calc
    _ = ((z ^ 2 - a * z + 1) *
          ((z⁻¹) ^ 2 - a * z⁻¹ + 1)) *
        ((1 - z) ^ (2 * damping) *
          (1 - z⁻¹) ^ (2 * damping)) *
        ((1 + z ^ (2 * mode)) *
          (1 + (z⁻¹) ^ (2 * mode))) := by ring
    _ = _ := by
      rw [liToeplitzAmplifier_seed_mul_inv a z hz,
        liToeplitzAmplifier_damping_mul_inv damping z hz]

/-- Real amplifier coefficients commute with complex conjugation. -/
theorem liToeplitzAmplifier_conj
    (a : ℝ) (damping mode : ℕ) (z : ℂ) :
    liToeplitzAmplifier (a : ℂ) damping mode (conj z) =
      conj (liToeplitzAmplifier (a : ℂ) damping mode z) := by
  simp [liToeplitzAmplifier]

/-- On the reciprocal/conjugate locus (in particular on the unit circle),
the complete amplifier contribution is an exact norm square and therefore
nonnegative. -/
theorem liToeplitzAmplifier_mul_inv_eq_normSq
    (a : ℝ) (damping mode : ℕ) (z : ℂ)
    (hinv : z⁻¹ = conj z) :
    liToeplitzAmplifier (a : ℂ) damping mode z *
        liToeplitzAmplifier (a : ℂ) damping mode z⁻¹ =
      (Complex.normSq
        (liToeplitzAmplifier (a : ℂ) damping mode z) : ℂ) := by
  rw [hinv, liToeplitzAmplifier_conj, Complex.mul_conj]

end RiemannLab
