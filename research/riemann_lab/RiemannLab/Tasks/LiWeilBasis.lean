import RiemannLab.Tasks.LiDistanceGram

namespace RiemannLab

/-!
# Li modes as the Weil test-function basis

This file verifies the finite algebra behind Theorem 3.1 of Lagarias,
``Li coefficients for automorphic L-functions'' (2007).  It identifies the
distance--Gram matrix with the Weil scalar product in the Li basis.  The
analytic zero summation and explicit formula are separate obligations.
-/

/-- When `m ≤ n`, the product of a Li mode and its reflected mode collapses
to the three modes appearing in the Weil-basis Gram entry. -/
theorem liZeroMode_mul_reflected_eq_sub
    {n m : ℕ} {ρ : ℂ} (hρ0 : ρ ≠ 0) (hρ1 : ρ ≠ 1) (hmn : m ≤ n) :
    liZeroMode n ρ * liZeroMode m (1 - ρ) =
      liZeroMode n ρ + liZeroMode m (1 - ρ) - liZeroMode (n - m) ρ := by
  have hratio := liRatio_mul_reflected_liRatio hρ0 hρ1
  have hsplit :
      (1 - ρ⁻¹) ^ n = (1 - ρ⁻¹) ^ (n - m) * (1 - ρ⁻¹) ^ m := by
    rw [← pow_add]
    congr 1
    omega
  have hpowers :
      (1 - ρ⁻¹) ^ n * (1 - (1 - ρ)⁻¹) ^ m =
        (1 - ρ⁻¹) ^ (n - m) := by
    rw [hsplit, mul_assoc, ← mul_pow, hratio, one_pow, mul_one]
  unfold liZeroMode
  calc
    (1 - (1 - ρ⁻¹) ^ n) * (1 - (1 - (1 - ρ)⁻¹) ^ m) =
        1 - (1 - ρ⁻¹) ^ n - (1 - (1 - ρ)⁻¹) ^ m +
          (1 - ρ⁻¹) ^ n * (1 - (1 - ρ)⁻¹) ^ m := by ring
    _ = 1 - (1 - ρ⁻¹) ^ n + (1 - (1 - (1 - ρ)⁻¹) ^ m) -
        (1 - (1 - ρ⁻¹) ^ (n - m)) := by rw [hpowers]; ring

/-- The centered matrix construction is linear in the underlying sequence.
This permits a checked archimedean/finite-place/pole decomposition once the
corresponding Li coefficient identity is supplied. -/
theorem centeredSequenceEntry_add
    (a b : ℕ → ℝ) (i j : ℕ) :
    centeredSequenceEntry (fun n => a n + b n) i j =
      centeredSequenceEntry a i j + centeredSequenceEntry b i j := by
  simp [centeredSequenceEntry]
  ring

theorem centeredSequenceEntry_sub
    (a b : ℕ → ℝ) (i j : ℕ) :
    centeredSequenceEntry (fun n => a n - b n) i j =
      centeredSequenceEntry a i j - centeredSequenceEntry b i j := by
  simp [centeredSequenceEntry]
  ring

end RiemannLab
