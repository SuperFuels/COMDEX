import RiemannLab.Tasks.OffCriticalQuartet

namespace RiemannLab

open Complex ComplexConjugate

/-!
# Reflection-paired Li modes

This file isolates the exact finite algebra behind the positivity programme.
On the critical line, reflection agrees with conjugation, so each reflected
pair contribution is a norm square.  The statement is conditional on the
zero's real part being one half; the frontier problem is to obtain an
unconditional prime-side positivity certificate with the same structure.
-/

/-- The contribution attached to one point in Li's `n`th zero sum. -/
noncomputable def liZeroMode (n : ℕ) (ρ : ℂ) : ℂ :=
  1 - (1 - ρ⁻¹) ^ n

theorem liZeroMode_conj (n : ℕ) (ρ : ℂ) :
    liZeroMode n (conj ρ) = conj (liZeroMode n ρ) := by
  simp [liZeroMode]

/-- The Möbius ratios at reflected points are multiplicative inverses. -/
theorem liRatio_mul_reflected_liRatio {ρ : ℂ} (hρ0 : ρ ≠ 0) (hρ1 : ρ ≠ 1) :
    (1 - ρ⁻¹) * (1 - (1 - ρ)⁻¹) = 1 := by
  field_simp
  ring

/-- Bombieri--Lagarias' elementary reflection factorization for one Li mode. -/
theorem liZeroMode_add_reflection_eq_mul
    (n : ℕ) {ρ : ℂ} (hρ0 : ρ ≠ 0) (hρ1 : ρ ≠ 1) :
    liZeroMode n ρ + liZeroMode n (1 - ρ) =
      liZeroMode n ρ * liZeroMode n (1 - ρ) := by
  have hratio := liRatio_mul_reflected_liRatio hρ0 hρ1
  have hpow : (1 - ρ⁻¹) ^ n * (1 - (1 - ρ)⁻¹) ^ n = 1 := by
    rw [← mul_pow, hratio, one_pow]
  unfold liZeroMode
  calc
    (1 - (1 - ρ⁻¹) ^ n) + (1 - (1 - (1 - ρ)⁻¹) ^ n) =
        2 - (1 - ρ⁻¹) ^ n - (1 - (1 - ρ)⁻¹) ^ n := by ring
    _ = 1 - (1 - ρ⁻¹) ^ n - (1 - (1 - ρ)⁻¹) ^ n +
        (1 - ρ⁻¹) ^ n * (1 - (1 - ρ)⁻¹) ^ n := by rw [hpow]; ring
    _ = (1 - (1 - ρ⁻¹) ^ n) * (1 - (1 - (1 - ρ)⁻¹) ^ n) := by ring

/-- On the critical line, functional-equation reflection is complex
conjugation. -/
theorem one_sub_eq_conj_of_re_eq_half {ρ : ℂ} (hre : ρ.re = 1 / 2) :
    1 - ρ = conj ρ := by
  apply Complex.ext
  · simp
    linarith
  · simp

/-- A reflected Li pair on the critical line is exactly a norm square. -/
theorem liZeroMode_pair_eq_normSq
    (n : ℕ) {ρ : ℂ} (hρ0 : ρ ≠ 0) (hρ1 : ρ ≠ 1)
    (hre : ρ.re = 1 / 2) :
    liZeroMode n ρ + liZeroMode n (1 - ρ) =
      (Complex.normSq (liZeroMode n ρ) : ℂ) := by
  rw [liZeroMode_add_reflection_eq_mul n hρ0 hρ1,
    one_sub_eq_conj_of_re_eq_half hre, liZeroMode_conj, Complex.mul_conj]

/-- In particular the real part of every critical-line reflected pair is
nonnegative. -/
theorem liZeroMode_pair_re_nonneg
    (n : ℕ) {ρ : ℂ} (hρ0 : ρ ≠ 0) (hρ1 : ρ ≠ 1)
    (hre : ρ.re = 1 / 2) :
    0 ≤ (liZeroMode n ρ + liZeroMode n (1 - ρ)).re := by
  rw [liZeroMode_pair_eq_normSq n hρ0 hρ1 hre]
  simp [Complex.normSq_nonneg]

end RiemannLab
