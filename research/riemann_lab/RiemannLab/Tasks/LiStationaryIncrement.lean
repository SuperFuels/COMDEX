import RiemannLab.Tasks.LiDistanceGram

namespace RiemannLab

/-!
# Stationary increments of the Li distance kernel

The centered Li kernel is nonstationary, but its mixed first difference is a
Toeplitz kernel.  This converts positivity of every Li distance--Gram matrix
into a stationary moment problem for the second differences of the Li
sequence.  The result is finite algebra and assumes neither RH nor a formula
for the Li coefficients.
-/

/-- Mixed first difference of the centered distance kernel.  The factor
`1/2` gives the covariance normalization. -/
noncomputable def centeredIncrementEntry
    (a : ℕ → ℝ) (i j : ℕ) : ℝ :=
  (centeredSequenceEntry a (i + 1) (j + 1) -
      centeredSequenceEntry a i (j + 1) -
      centeredSequenceEntry a (i + 1) j +
      centeredSequenceEntry a i j) / 2

/-- The stationary lag sequence associated with the mixed difference. -/
noncomputable def liIncrementLag (a : ℕ → ℝ) : ℕ → ℝ
  | 0 => a 1 - a 0
  | n + 1 => (a n - 2 * a (n + 1) + a (n + 2)) / 2

/-- Above the diagonal, the mixed difference depends only on the lag. -/
theorem centeredIncrementEntry_of_lt
    (a : ℕ → ℝ) {i j : ℕ} (hij : i < j) :
    centeredIncrementEntry a i j = liIncrementLag a (j - i) := by
  have h0 : i - (j + 1) + (j + 1 - i) = j + 1 - i := by omega
  have h2 : i - j + (j - i) = j - i := by omega
  have h3 : (i + 1) - j + (j - (i + 1)) = j - i - 1 := by omega
  have hpos : 0 < j - i := Nat.sub_pos_of_lt hij
  obtain ⟨d, hd⟩ := Nat.exists_eq_succ_of_ne_zero hpos.ne'
  rw [hd]
  simp [centeredIncrementEntry, centeredSequenceEntry, liIncrementLag,
    h0, h2, h3]
  have : j - i - 1 = d := by omega
  have hnext : j + 1 - i = d + 2 := by omega
  rw [this, hd, hnext]
  simp only [Nat.succ_eq_add_one]
  ring

/-- On the diagonal, the mixed difference is the zeroth stationary lag. -/
theorem centeredIncrementEntry_diag
    (a : ℕ → ℝ) (i : ℕ) :
    centeredIncrementEntry a i i = liIncrementLag a 0 := by
  simp [centeredIncrementEntry, centeredSequenceEntry, liIncrementLag]
  ring

/-- Below the diagonal, symmetry gives the same lag formula. -/
theorem centeredIncrementEntry_of_gt
    (a : ℕ → ℝ) {i j : ℕ} (hji : j < i) :
    centeredIncrementEntry a i j = liIncrementLag a (i - j) := by
  have h0 : i - (j + 1) + (j + 1 - i) = i - j - 1 := by omega
  have h2 : i - j + (j - i) = i - j := by omega
  have h3 : (i + 1) - j + (j - (i + 1)) = i - j + 1 := by omega
  have hpos : 0 < i - j := Nat.sub_pos_of_lt hji
  obtain ⟨d, hd⟩ := Nat.exists_eq_succ_of_ne_zero hpos.ne'
  rw [hd]
  simp [centeredIncrementEntry, centeredSequenceEntry, liIncrementLag,
    h0, h2, h3]
  have : i - j - 1 = d := by omega
  rw [this, hd]
  simp only [Nat.succ_eq_add_one]
  ring

/-- Complete Toeplitz identity for the increment kernel. -/
theorem centeredIncrementEntry_eq_liIncrementLag
    (a : ℕ → ℝ) (i j : ℕ) :
    centeredIncrementEntry a i j =
      liIncrementLag a ((i - j) + (j - i)) := by
  rcases lt_trichotomy i j with hij | rfl | hji
  · rw [centeredIncrementEntry_of_lt a hij]
    congr 1
    omega
  · simpa using centeredIncrementEntry_diag a i
  · rw [centeredIncrementEntry_of_gt a hji]
    congr 1
    omega

/-- A two-dimensional mixed difference telescopes to the four corners. -/
theorem sum_mixed_difference
    (K : ℕ → ℕ → ℝ) (m n : ℕ) :
    (∑ i ∈ Finset.range m, ∑ j ∈ Finset.range n,
        ((K (i + 1) (j + 1) - K i (j + 1)) -
          (K (i + 1) j - K i j))) =
      K m n - K 0 n - K m 0 + K 0 0 := by
  have hinner : ∀ i : ℕ,
      (∑ j ∈ Finset.range n,
          ((K (i + 1) (j + 1) - K i (j + 1)) -
            (K (i + 1) j - K i j))) =
        (K (i + 1) n - K i n) - (K (i + 1) 0 - K i 0) := by
    intro i
    simpa using Finset.sum_range_sub
      (fun j ↦ K (i + 1) j - K i j) n
  simp_rw [hinner]
  rw [Finset.sum_sub_distrib]
  have htop : (∑ i ∈ Finset.range m, (K (i + 1) n - K i n)) =
      K m n - K 0 n := by
    simpa using Finset.sum_range_sub (fun i ↦ K i n) m
  have hbottom : (∑ i ∈ Finset.range m, (K (i + 1) 0 - K i 0)) =
      K m 0 - K 0 0 := by
    simpa using Finset.sum_range_sub (fun i ↦ K i 0) m
  rw [htop, hbottom]
  ring

/-- Cumulative summation reconstructs the centered kernel from its stationary
increment kernel when `a 0 = 0`.  This is the exact finite bridge needed to
transfer a Toeplitz positivity certificate back to the Li distance form. -/
theorem centeredSequenceEntry_eq_sum_increment
    (a : ℕ → ℝ) (ha0 : a 0 = 0) (m n : ℕ) :
    centeredSequenceEntry a m n =
      2 * ∑ i ∈ Finset.range m, ∑ j ∈ Finset.range n,
        centeredIncrementEntry a i j := by
  calc
    centeredSequenceEntry a m n =
        centeredSequenceEntry a m n - centeredSequenceEntry a 0 n -
          centeredSequenceEntry a m 0 + centeredSequenceEntry a 0 0 := by
            simp [centeredSequenceEntry, ha0]
    _ = ∑ i ∈ Finset.range m, ∑ j ∈ Finset.range n,
          ((centeredSequenceEntry a (i + 1) (j + 1) -
              centeredSequenceEntry a i (j + 1)) -
            (centeredSequenceEntry a (i + 1) j -
              centeredSequenceEntry a i j)) := by
            symm
            exact sum_mixed_difference (centeredSequenceEntry a) m n
    _ = 2 * ∑ i ∈ Finset.range m, ∑ j ∈ Finset.range n,
          centeredIncrementEntry a i j := by
            simp_rw [centeredIncrementEntry]
            rw [Finset.mul_sum]
            apply Finset.sum_congr rfl
            intro i hi
            rw [Finset.mul_sum]
            apply Finset.sum_congr rfl
            intro j hj
            ring

end RiemannLab
