import RiemannLab.Tasks.LiUniversalPositiveKernel

namespace RiemannLab

/-!
# The minimal stationary energy target

Universal Toeplitz positivity is a powerful sufficient operator condition,
but termwise positivity of a normalized sequence only requires the all-ones
prefix quadratic forms.  This file isolates that exact minimal family.
-/

/-- The all-ones Toeplitz energy of the first `n` entries of any stationary
lag sequence. -/
noncomputable def stationaryPrefixEnergy (lag : ℕ → ℝ) (n : ℕ) : ℝ :=
  stationaryToeplitzQuadratic (Finset.range n) (fun i : ℕ ↦ i)
    (fun _ ↦ (1 : ℝ)) lag

/-- The prefix energy specialized to stationary Li increments. -/
noncomputable def liPrefixEnergy (a : ℕ → ℝ) (n : ℕ) : ℝ :=
  stationaryPrefixEnergy (liIncrementLag a) n

/-- For an atomic spectral measure, every prefix energy is the exact Fejér
sum of squares.  The research target therefore needs only this nested test
family, not every stationary quadratic form. -/
theorem stationaryPrefixEnergy_atomic_eq_fejerSquares
    {κ : Type*} (atoms : Finset κ) (weight angle : κ → ℝ) (n : ℕ) :
    stationaryPrefixEnergy (atomicStationaryLag atoms weight angle) n =
      ∑ x ∈ atoms, weight x *
        ((∑ i ∈ Finset.range n, Real.cos (i * angle x)) ^ 2 +
         (∑ i ∈ Finset.range n, Real.sin (i * angle x)) ^ 2) := by
  simpa [stationaryPrefixEnergy] using
    stationaryToeplitzQuadratic_atomic_eq_squares
      (Finset.range n) atoms (fun i : ℕ ↦ i) (fun _ ↦ (1 : ℝ))
        weight angle

/-- Exact telescoping identity: for a normalized sequence, its `n`th term
is precisely the all-ones prefix energy of the stationary kernel. -/
theorem liPrefixEnergy_eq
    (a : ℕ → ℝ) (ha0 : a 0 = 0) (n : ℕ) :
    liPrefixEnergy a n = a n := by
  have hcenter := centeredSequenceEntry_eq_sum_increment a ha0 n n
  simp_rw [centeredIncrementEntry_eq_liIncrementLag] at hcenter
  have hdiag : centeredSequenceEntry a n n = 2 * a n := by
    simp [centeredSequenceEntry, ha0]
    ring
  have henergy :
      (∑ i ∈ Finset.range n, ∑ j ∈ Finset.range n,
        liIncrementLag a ((i - j) + (j - i))) = liPrefixEnergy a n := by
    simp [liPrefixEnergy, stationaryPrefixEnergy, stationaryToeplitzQuadratic]
  rw [hdiag, henergy] at hcenter
  linarith

/-- Positivity of exactly the prefix energies, with no surplus matrix tests. -/
def HasNonnegativeLiPrefixEnergy (a : ℕ → ℝ) : Prop :=
  ∀ n, 0 ≤ liPrefixEnergy a n

/-- For a normalized sequence, prefix-energy positivity is exactly termwise
positivity. -/
theorem nonnegativeLiPrefixEnergy_iff
    (a : ℕ → ℝ) (ha0 : a 0 = 0) :
    HasNonnegativeLiPrefixEnergy a ↔ ∀ n, 0 ≤ a n := by
  constructor
  · intro h n
    simpa [liPrefixEnergy_eq a ha0 n] using h n
  · intro h n
    simpa [liPrefixEnergy_eq a ha0 n] using h n

/-- Universal stationary positivity implies the minimal prefix condition. -/
theorem nonnegativeLiPrefixEnergy_of_positiveKernel
    {a : ℕ → ℝ} (hkernel : HasPositiveLiIncrementKernel a) :
    HasNonnegativeLiPrefixEnergy a := by
  intro n
  exact hkernel (Finset.range n) (fun i : ℕ ↦ i) (fun _ ↦ (1 : ℝ))

/-! ## Strictness of the universal operator condition -/

/-- A simple normalized nonnegative sequence used to show that universal
Toeplitz positivity is genuinely stronger than termwise positivity. -/
def nonnegativeSpikeSequence : ℕ → ℝ
  | 0 => 0
  | 1 => 1
  | 2 => 10
  | _ => 0

theorem nonnegativeSpikeSequence_nonneg (n : ℕ) :
    0 ≤ nonnegativeSpikeSequence n := by
  rcases n with _ | _ | _ | n <;> simp [nonnegativeSpikeSequence]

theorem nonnegativeSpikeSequence_zero :
    nonnegativeSpikeSequence 0 = 0 := rfl

/-- Despite being termwise nonnegative, the spike sequence has a negative
two-point stationary quadratic form. -/
theorem nonnegativeSpikeSequence_not_positiveKernel :
    ¬HasPositiveLiIncrementKernel nonnegativeSpikeSequence := by
  intro h
  have htest := h (Finset.range 2) (fun i : ℕ ↦ i)
    (fun i ↦ if i = 0 then (1 : ℝ) else -1)
  simp [stationaryToeplitzQuadratic, Finset.sum_range_succ,
    liIncrementLag, nonnegativeSpikeSequence] at htest
  norm_num at htest

end RiemannLab
