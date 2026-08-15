import RiemannLab.Tasks.LiStationaryPositiveOperator
import RiemannLab.Tasks.LiCaratheodoryTransform

namespace RiemannLab

/-!
# The universal stationary positivity target

A finite atomic moment model is useful for exact experiments, but it is not
the universal operator notion required by the Li sequence.  The correct
target is positivity of every finite Toeplitz compression.  This file makes
that distinction formal and removes finite atomicity from the proof route.
-/

/-- Universal positive definiteness of a real stationary lag sequence. -/
def HasPositiveStationaryKernel (lag : ℕ → ℝ) : Prop :=
  ∀ {ι : Type} (indices : Finset ι) (position : ι → ℕ)
    (coeff : ι → ℝ),
    0 ≤ stationaryToeplitzQuadratic indices position coeff lag

/-- The universal target specialized to stationary Li increments. -/
def HasPositiveLiIncrementKernel (a : ℕ → ℝ) : Prop :=
  HasPositiveStationaryKernel (liIncrementLag a)

/-- A finite atomic representation remains a valid sufficient certificate,
but is no longer built into the definition of the universal target. -/
theorem positiveStationaryKernel_of_finiteCertificate
    {lag : ℕ → ℝ} (certificate : FiniteStationaryPositiveCertificate lag) :
    HasPositiveStationaryKernel lag := by
  intro ι indices position coeff
  exact certificate.quadratic_nonneg indices position coeff

/-- The earlier finite-operator interface maps into the correct universal
positive-kernel interface. -/
theorem positiveLiIncrementKernel_of_finiteOperator
    {a : ℕ → ℝ} (hoperator : HasFiniteStationaryPositiveOperator a) :
    HasPositiveLiIncrementKernel a := by
  exact positiveStationaryKernel_of_finiteCertificate hoperator.some

/-- Universal stationary positivity reconstructs every normalized sequence
term.  No spectral measure, atomicity, or zero-location assumption occurs in
this finite algebraic implication. -/
theorem sequence_nonneg_of_positiveLiIncrementKernel
    {a : ℕ → ℝ} (ha0 : a 0 = 0)
    (hkernel : HasPositiveLiIncrementKernel a) :
    ∀ n, 0 ≤ a n := by
  apply sequence_nonneg_of_centered_diagonal_nonneg ha0
  intro n
  rw [centeredSequenceEntry_eq_sum_increment a ha0 n n]
  apply mul_nonneg (by norm_num)
  simp_rw [centeredIncrementEntry_eq_liIncrementLag]
  have hquad := hkernel (Finset.range n) (fun i : ℕ ↦ i)
    (fun _ ↦ (1 : ℝ))
  simpa [stationaryToeplitzQuadratic] using hquad

/-- Exact theorem interface for a future arithmetic proof: it is enough to
prove the stationary quadratic inequality directly for every finite test.
This avoids requiring an a priori construction of a finite spectral model. -/
theorem sequence_nonneg_of_arithmetic_quadratic
    {a : ℕ → ℝ} (ha0 : a 0 = 0)
    (harithmetic : ∀ {ι : Type} (indices : Finset ι)
      (position : ι → ℕ) (coeff : ι → ℝ),
      0 ≤ stationaryToeplitzQuadratic indices position coeff
        (liIncrementLag a)) :
    ∀ n, 0 ≤ a n :=
  sequence_nonneg_of_positiveLiIncrementKernel ha0 harithmetic

end RiemannLab
