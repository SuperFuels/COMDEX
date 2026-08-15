import RiemannLab.Tasks.LiPairIdentity

namespace RiemannLab

open Complex ComplexConjugate

/-!
# The exact Li reflection defect

The critical line is precisely where functional-equation reflection agrees
with Hilbert-space conjugation.  This file separates a reflected Li pair into
the norm square which a positivity proof wants and an explicit defect term.
No zero-location hypothesis is hidden in the decomposition.
-/

/-- The difference between the reflected partner of a Li mode and its
conjugate partner.  It vanishes on the critical line. -/
noncomputable def liReflectionDefect (n : ℕ) (ρ : ℂ) : ℂ :=
  liZeroMode n (1 - ρ) - conj (liZeroMode n ρ)

/-- Every reflected pair is a norm square plus one completely explicit
off-line defect. -/
theorem liZeroMode_pair_eq_normSq_add_defect
    (n : ℕ) {ρ : ℂ} (hρ0 : ρ ≠ 0) (hρ1 : ρ ≠ 1) :
    liZeroMode n ρ + liZeroMode n (1 - ρ) =
      (Complex.normSq (liZeroMode n ρ) : ℂ) +
        liZeroMode n ρ * liReflectionDefect n ρ := by
  rw [liZeroMode_add_reflection_eq_mul n hρ0 hρ1]
  rw [← Complex.mul_conj]
  unfold liReflectionDefect
  ring

/-- Reflection and conjugation coincide exactly on the critical line. -/
theorem one_sub_eq_conj_iff_re_eq_half {ρ : ℂ} :
    1 - ρ = conj ρ ↔ ρ.re = 1 / 2 := by
  constructor
  · intro h
    have hre := congrArg Complex.re h
    simp at hre
    linarith
  · exact one_sub_eq_conj_of_re_eq_half

/-- Consequently the explicit reflection defect vanishes on the critical
line, for every Li index. -/
theorem liReflectionDefect_eq_zero_of_re_eq_half
    (n : ℕ) {ρ : ℂ} (hre : ρ.re = 1 / 2) :
    liReflectionDefect n ρ = 0 := by
  rw [liReflectionDefect, one_sub_eq_conj_of_re_eq_half hre,
    liZeroMode_conj]
  ring

/-- The full functional-equation/conjugation orbit contribution. -/
noncomputable def liQuartetMode (n : ℕ) (ρ : ℂ) : ℂ :=
  liZeroMode n ρ + liZeroMode n (1 - ρ) +
    liZeroMode n (conj ρ) + liZeroMode n (1 - conj ρ)

/-- On the critical line the quartet contribution is twice a norm square.
This is the exact positive structure that an unconditional proof would have
to recover without assuming the line condition. -/
theorem liQuartetMode_eq_two_mul_normSq
    (n : ℕ) {ρ : ℂ} (hρ0 : ρ ≠ 0) (hρ1 : ρ ≠ 1)
    (hre : ρ.re = 1 / 2) :
    liQuartetMode n ρ = 2 * (Complex.normSq (liZeroMode n ρ) : ℂ) := by
  have href : 1 - ρ = conj ρ := one_sub_eq_conj_of_re_eq_half hre
  have hrefc : 1 - conj ρ = ρ := by
    apply Complex.ext
    · simp
      linarith
    · simp
  calc
    liQuartetMode n ρ =
        2 * (liZeroMode n ρ + liZeroMode n (1 - ρ)) := by
          simp only [liQuartetMode, href, hrefc]
          ring
    _ = 2 * (Complex.normSq (liZeroMode n ρ) : ℂ) := by
          rw [liZeroMode_pair_eq_normSq n hρ0 hρ1 hre]

/-- In particular, a critical-line quartet is nonnegative as a real
contribution. -/
theorem liQuartetMode_re_nonneg
    (n : ℕ) {ρ : ℂ} (hρ0 : ρ ≠ 0) (hρ1 : ρ ≠ 1)
    (hre : ρ.re = 1 / 2) :
    0 ≤ (liQuartetMode n ρ).re := by
  rw [liQuartetMode_eq_two_mul_normSq n hρ0 hρ1 hre]
  simp [Complex.normSq_nonneg]

end RiemannLab
