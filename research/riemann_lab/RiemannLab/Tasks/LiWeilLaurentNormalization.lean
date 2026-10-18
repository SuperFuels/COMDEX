import RiemannLab.Tasks.LiWitnessAssembly
import Mathlib.Algebra.Polynomial.Laurent

namespace RiemannLab

open ComplexConjugate
open LaurentPolynomial

/-!
# Laurent-polynomial normalization of the complete localized amplifier

The seed, damping, oscillator, and finite reciprocal-coordinate annihilator
are one finite Laurent polynomial.  This removes an ambiguity between the
algebraic detector and the finite Fourier/Weil test normalization.
-/

/-- Evaluation of a Laurent polynomial at a nonzero complex point. -/
noncomputable def laurentEvalAt (q : ℂ) (hq : q ≠ 0)
    (P : LaurentPolynomial ℂ) : ℂ :=
  LaurentPolynomial.eval₂ (RingHom.id ℂ) (Units.mk0 q hq) P

@[simp]
theorem laurentEvalAt_C (q : ℂ) (hq : q ≠ 0) (a : ℂ) :
    laurentEvalAt q hq (LaurentPolynomial.C a) = a := by
  simp [laurentEvalAt, LaurentPolynomial.eval₂_C]

@[simp]
theorem laurentEvalAt_T_one (q : ℂ) (hq : q ≠ 0) :
    laurentEvalAt q hq (LaurentPolynomial.T 1) = q := by
  simpa [laurentEvalAt] using
    LaurentPolynomial.eval₂_T_n (RingHom.id ℂ) (Units.mk0 q hq) 1

@[simp]
theorem laurentEvalAt_T_neg_one (q : ℂ) (hq : q ≠ 0) :
    laurentEvalAt q hq (LaurentPolynomial.T (-1)) = q⁻¹ := by
  simpa [laurentEvalAt] using
    LaurentPolynomial.eval₂_T_neg_n (RingHom.id ℂ) (Units.mk0 q hq) 1

@[simp]
theorem laurentEvalAt_T_nat (q : ℂ) (hq : q ≠ 0) (n : ℕ) :
    laurentEvalAt q hq (LaurentPolynomial.T (n : ℤ)) = q ^ n := by
  simpa [laurentEvalAt] using
    LaurentPolynomial.eval₂_T_n (RingHom.id ℂ) (Units.mk0 q hq) n

/-- Laurent form of `q+q⁻¹`. -/
noncomputable def reciprocalLaurentCoordinate : LaurentPolynomial ℂ :=
  LaurentPolynomial.T 1 + LaurentPolynomial.T (-1)

@[simp]
theorem laurentEvalAt_reciprocalCoordinate
    (q : ℂ) (hq : q ≠ 0) :
    laurentEvalAt q hq reciprocalLaurentCoordinate = q + q⁻¹ := by
  simp [laurentEvalAt, reciprocalLaurentCoordinate]

/-- The complete polynomial part of the Toeplitz amplifier. -/
noncomputable def liToeplitzAmplifierLaurent
    (a : ℂ) (damping mode : ℕ) : LaurentPolynomial ℂ :=
    (LaurentPolynomial.T 2 -
      LaurentPolynomial.C a * LaurentPolynomial.T 1 + 1) *
    (1 - LaurentPolynomial.T 1) ^ (2 * damping) *
    (1 + LaurentPolynomial.T ((2 * mode : ℕ) : ℤ))

/-- Exact evaluation of the Laurent amplifier agrees with the original
finite polynomial amplifier. -/
theorem laurentEvalAt_liToeplitzAmplifier
    (a q : ℂ) (damping mode : ℕ) (hq : q ≠ 0) :
    laurentEvalAt q hq (liToeplitzAmplifierLaurent a damping mode) =
      liToeplitzAmplifier a damping mode q := by
  simp [laurentEvalAt, liToeplitzAmplifierLaurent,
    liToeplitzAmplifier]
  rw [show (2 : ℤ) * (mode : ℤ) = ((2 * mode : ℕ) : ℤ) by omega,
    zpow_natCast]
  rfl

/-- Laurent form of the finite conjugate-pair annihilator. -/
noncomputable def finiteConjugatePairAnnihilatorLaurent
    (competitors : Finset ℂ) : LaurentPolynomial ℂ :=
  ∏ v ∈ competitors,
    (reciprocalLaurentCoordinate - LaurentPolynomial.C v) *
      (reciprocalLaurentCoordinate - LaurentPolynomial.C (conj v))

/-- The Laurent annihilator evaluates to the previously verified reciprocal
coordinate annihilator. -/
theorem laurentEvalAt_finiteConjugatePairAnnihilator
    (competitors : Finset ℂ) (q : ℂ) (hq : q ≠ 0) :
    laurentEvalAt q hq
        (finiteConjugatePairAnnihilatorLaurent competitors) =
      finiteConjugatePairAnnihilator competitors (q + q⁻¹) := by
  simp [laurentEvalAt, finiteConjugatePairAnnihilatorLaurent,
    finiteConjugatePairAnnihilator, reciprocalLaurentCoordinate]

/-- One finite Laurent polynomial encoding every factor of the localized
zeta amplifier. -/
noncomputable def localizedZetaAmplifierLaurent
    (competitors : Finset ℂ) (a : ℂ) (mode : ℕ) :
    LaurentPolynomial ℂ :=
  liToeplitzAmplifierLaurent a 2 mode *
    finiteConjugatePairAnnihilatorLaurent competitors

/-- Exact target-normalization identity: evaluation of the single finite
Laurent test equals the complete localized amplitude used in the tail theorem. -/
theorem laurentEvalAt_localizedZetaAmplifier
    (competitors : Finset ℂ) (a : ℂ) (mode : ℕ)
    (q : ℂ) (hq : q ≠ 0) :
    laurentEvalAt q hq
        (localizedZetaAmplifierLaurent competitors a mode) =
      liToeplitzAmplifier a 2 mode q *
        finiteConjugatePairAnnihilator competitors (q + q⁻¹) := by
  rw [localizedZetaAmplifierLaurent]
  change LaurentPolynomial.eval₂ (RingHom.id ℂ) (Units.mk0 q hq) _ = _
  rw [map_mul]
  change laurentEvalAt q hq (liToeplitzAmplifierLaurent a 2 mode) *
      laurentEvalAt q hq (finiteConjugatePairAnnihilatorLaurent competitors) = _
  rw [laurentEvalAt_liToeplitzAmplifier,
    laurentEvalAt_finiteConjugatePairAnnihilator]

/-- Specialization to an actual zeta point: the Laurent test and the amplitude
used by global zeta summability are definitionally the same object. -/
theorem laurentEvalAt_eq_localizedZetaAmplifier
    (competitors : Finset ℂ) (a : ℂ) (mode : ℕ)
    {ρ : ℂ} (hq : zetaLiCoordinate ρ ≠ 0) :
    laurentEvalAt (zetaLiCoordinate ρ) hq
        (localizedZetaAmplifierLaurent competitors a mode) =
      localizedZetaAmplifier competitors a mode ρ := by
  rw [laurentEvalAt_localizedZetaAmplifier]
  rfl

/-- Autocorrelation of the normalized Laurent test is exactly the product of
its values at reciprocal modes. -/
noncomputable def laurentAutocorrelation
    (P : LaurentPolynomial ℂ) (q : ℂ) (hq : q ≠ 0) : ℂ :=
  laurentEvalAt q hq P * laurentEvalAt q⁻¹ (inv_ne_zero hq) P

/-- The complete localized autocorrelation is therefore the exact reciprocal
product of the same amplifier used in the infinite-tail theorem. -/
theorem localizedZetaAmplifierLaurent_autocorrelation
    (competitors : Finset ℂ) (a : ℂ) (mode : ℕ)
    (q : ℂ) (hq : q ≠ 0) :
    laurentAutocorrelation
        (localizedZetaAmplifierLaurent competitors a mode) q hq =
      (liToeplitzAmplifier a 2 mode q *
        finiteConjugatePairAnnihilator competitors (q + q⁻¹)) *
      (liToeplitzAmplifier a 2 mode q⁻¹ *
        finiteConjugatePairAnnihilator competitors (q⁻¹ + (q⁻¹)⁻¹)) := by
  unfold laurentAutocorrelation
  rw [laurentEvalAt_localizedZetaAmplifier,
    laurentEvalAt_localizedZetaAmplifier]

end RiemannLab
