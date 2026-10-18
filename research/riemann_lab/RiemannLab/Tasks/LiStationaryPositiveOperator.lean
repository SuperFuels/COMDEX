import RiemannLab.Tasks.LiStationaryIncrement

namespace RiemannLab

open scoped BigOperators

/-!
# A positive-operator interface for the completed stationary Li kernel

A nonnegative atomic moment representation of the stationary lags gives an
exact sum-of-squares factorization of every finite Toeplitz quadratic form.
Together with the verified cumulative reconstruction, this is a precise
operator target for the coupled prime--Gamma--pole kernel.
-/

/-- Real cosine moments of a finite nonnegative spectral measure. -/
noncomputable def atomicStationaryLag
    {κ : Type*} (atoms : Finset κ) (weight angle : κ → ℝ) (n : ℕ) : ℝ :=
  ∑ x ∈ atoms, weight x * Real.cos (n * angle x)

/-- The stationary Toeplitz quadratic form associated with a lag sequence. -/
noncomputable def stationaryToeplitzQuadratic
    {ι : Type*} (indices : Finset ι) (position : ι → ℕ)
    (coeff : ι → ℝ) (lag : ℕ → ℝ) : ℝ :=
  ∑ i ∈ indices, ∑ j ∈ indices,
    coeff i * coeff j *
      lag ((position i - position j) + (position j - position i))

/-- The elementary cosine difference identity in a form suited to Toeplitz
moments. -/
theorem cos_nat_absDiff_eq
    (m n : ℕ) (θ : ℝ) :
    Real.cos ((((m - n) + (n - m) : ℕ) : ℝ) * θ) =
      Real.cos ((m : ℝ) * θ) * Real.cos ((n : ℝ) * θ) +
        Real.sin ((m : ℝ) * θ) * Real.sin ((n : ℝ) * θ) := by
  rcases le_total m n with hmn | hnm
  · have hsub : (m - n) + (n - m) = n - m := by omega
    rw [hsub]
    have hreal : ((n - m : ℕ) : ℝ) * θ = n * θ - m * θ := by
      push_cast
      rw [Nat.cast_sub hmn]
      ring
    rw [hreal, Real.cos_sub]
    ring
  · have hsub : (m - n) + (n - m) = m - n := by omega
    rw [hsub]
    have hreal : ((m - n : ℕ) : ℝ) * θ = m * θ - n * θ := by
      push_cast
      rw [Nat.cast_sub hnm]
      ring
    rw [hreal, Real.cos_sub]

/-- Exact Gram/SOS factorization for a finite atomic spectral measure. -/
theorem stationaryToeplitzQuadratic_atomic_eq_squares
    {ι κ : Type*} (indices : Finset ι) (atoms : Finset κ)
    (position : ι → ℕ) (coeff : ι → ℝ)
    (weight angle : κ → ℝ) :
    stationaryToeplitzQuadratic indices position coeff
        (atomicStationaryLag atoms weight angle) =
      ∑ x ∈ atoms, weight x *
        ((∑ i ∈ indices,
            coeff i * Real.cos (position i * angle x)) ^ 2 +
         (∑ i ∈ indices,
            coeff i * Real.sin (position i * angle x)) ^ 2) := by
  unfold stationaryToeplitzQuadratic atomicStationaryLag
  let F : ι → ι → κ → ℝ := fun i j x ↦
    coeff i * coeff j *
      (weight x * Real.cos
        ((((position i - position j) + (position j - position i) : ℕ) : ℝ) *
          angle x))
  have hcomm :
      (∑ i ∈ indices, ∑ j ∈ indices, ∑ x ∈ atoms, F i j x) =
        ∑ x ∈ atoms, ∑ i ∈ indices, ∑ j ∈ indices, F i j x := by
    calc
      _ = ∑ i ∈ indices, ∑ x ∈ atoms, ∑ j ∈ indices, F i j x := by
        apply Finset.sum_congr rfl
        intro i hi
        rw [Finset.sum_comm]
      _ = _ := by rw [Finset.sum_comm]
  calc
    (∑ i ∈ indices, ∑ j ∈ indices,
        coeff i * coeff j *
          ∑ x ∈ atoms, weight x *
            Real.cos
              ((((position i - position j) + (position j - position i) : ℕ) : ℝ) *
                angle x)) =
        ∑ i ∈ indices, ∑ j ∈ indices, ∑ x ∈ atoms, F i j x := by
          apply Finset.sum_congr rfl
          intro i hi
          apply Finset.sum_congr rfl
          intro j hj
          simp_rw [Finset.mul_sum]
          apply Finset.sum_congr rfl
          intro x hx
          simp [F]
    _ = ∑ x ∈ atoms, ∑ i ∈ indices, ∑ j ∈ indices, F i j x := hcomm
    _ = ∑ x ∈ atoms, weight x *
          ((∑ i ∈ indices,
              coeff i * Real.cos ((position i : ℝ) * angle x)) ^ 2 +
           (∑ i ∈ indices,
              coeff i * Real.sin ((position i : ℝ) * angle x)) ^ 2) := by
      apply Finset.sum_congr rfl
      intro x hx
      simp_rw [F, cos_nat_absDiff_eq, mul_add, Finset.sum_add_distrib]
      rw [pow_two, pow_two, Finset.sum_mul_sum, Finset.sum_mul_sum]
      simp_rw [Finset.mul_sum]
      congr 1 <;>
        apply Finset.sum_congr rfl <;> intro i hi <;>
        apply Finset.sum_congr rfl <;> intro j hj <;>
        ring

/-- Nonnegative atomic weights make every stationary Toeplitz quadratic form
nonnegative, in every finite dimension. -/
theorem stationaryToeplitzQuadratic_atomic_nonneg
    {ι κ : Type*} (indices : Finset ι) (atoms : Finset κ)
    (position : ι → ℕ) (coeff : ι → ℝ)
    (weight angle : κ → ℝ) (hweight : ∀ x ∈ atoms, 0 ≤ weight x) :
    0 ≤ stationaryToeplitzQuadratic indices position coeff
      (atomicStationaryLag atoms weight angle) := by
  rw [stationaryToeplitzQuadratic_atomic_eq_squares]
  exact Finset.sum_nonneg fun x hx ↦
    mul_nonneg (hweight x hx) (by positivity)

/-- Abstract positive-measure certificate for a stationary lag sequence.  A
future completed arithmetic operator must construct this data without using
any information about the location of the zeta zeros. -/
structure FiniteStationaryPositiveCertificate (lag : ℕ → ℝ) where
  Atom : Type
  atoms : Finset Atom
  weight : Atom → ℝ
  angle : Atom → ℝ
  weight_nonneg : ∀ x ∈ atoms, 0 ≤ weight x
  moments : ∀ n, lag n = atomicStationaryLag atoms weight angle n

/-- A stationary positive certificate immediately gives all finite Toeplitz
quadratic inequalities. -/
theorem FiniteStationaryPositiveCertificate.quadratic_nonneg
    {lag : ℕ → ℝ} (certificate : FiniteStationaryPositiveCertificate lag)
    {ι : Type*} (indices : Finset ι) (position : ι → ℕ)
    (coeff : ι → ℝ) :
    0 ≤ stationaryToeplitzQuadratic indices position coeff lag := by
  rw [show lag = atomicStationaryLag certificate.atoms
      certificate.weight certificate.angle from funext certificate.moments]
  exact stationaryToeplitzQuadratic_atomic_nonneg
    indices certificate.atoms position coeff certificate.weight
    certificate.angle certificate.weight_nonneg

/-- The operator target specialized to the stationary increments of an
arbitrary sequence. -/
def HasFiniteStationaryPositiveOperator (a : ℕ → ℝ) : Prop :=
  Nonempty (FiniteStationaryPositiveCertificate (liIncrementLag a))

/-- A positive stationary operator forces every finite quadratic form of the
increment kernel to be nonnegative. -/
theorem increment_quadratic_nonneg_of_positiveOperator
    {a : ℕ → ℝ} (hoperator : HasFiniteStationaryPositiveOperator a)
    {ι : Type*} (indices : Finset ι) (position : ι → ℕ)
    (coeff : ι → ℝ) :
    0 ≤ stationaryToeplitzQuadratic indices position coeff
      (liIncrementLag a) := by
  exact hoperator.some.quadratic_nonneg indices position coeff

/-- A positive stationary operator forces the original normalized sequence
to be termwise nonnegative.  This is the exact finite-to-infinite bridge used
by the Li programme: the all-ones Toeplitz quadratic reconstructs the
diagonal of the centered distance kernel. -/
theorem sequence_nonneg_of_positiveOperator
    {a : ℕ → ℝ} (ha0 : a 0 = 0)
    (hoperator : HasFiniteStationaryPositiveOperator a) :
    ∀ n, 0 ≤ a n := by
  apply sequence_nonneg_of_centered_diagonal_nonneg ha0
  intro n
  rw [centeredSequenceEntry_eq_sum_increment a ha0 n n]
  apply mul_nonneg (by norm_num)
  simp_rw [centeredIncrementEntry_eq_liIncrementLag]
  have hquad := increment_quadratic_nonneg_of_positiveOperator hoperator
    (Finset.range n) (fun i : ℕ ↦ i) (fun _ ↦ (1 : ℝ))
  simpa [stationaryToeplitzQuadratic] using hquad

end RiemannLab
