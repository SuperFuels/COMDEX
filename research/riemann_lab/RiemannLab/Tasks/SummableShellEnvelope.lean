import RiemannLab.Tasks.XiZetaMultiplicity
import Mathlib.Analysis.PSeries

namespace RiemannLab

/-!
# Summability from linear shell counts

This is the global analytic engine required by the damped zeta amplifier.  A
countable family whose multiplicity mass in shell `n` is `O(n+1)` becomes
summable after fourth-power damping.  The theorem is deliberately formulated
for an arbitrary shell map so the geometric zeta-shell estimate is the only
remaining specialization.
-/

/-- Linear shell mass and fourth-power damping imply global summability. -/
theorem summable_mass_div_shell_add_one_pow_four
    {ι : Type*} [Countable ι]
    (shell : ι → ℕ) (mass : ι → ℝ) (C : ℝ)
    (hmass : ∀ i, 0 ≤ mass i)
    (hfiber : ∀ n, Summable (fun i : {i : ι // shell i = n} ↦ mass i.1))
    (hlinear : ∀ n,
      ∑' i : {i : ι // shell i = n}, mass i.1 ≤ C * (n + 1)) :
    Summable (fun i ↦ mass i / ((shell i + 1 : ℕ) : ℝ) ^ 4) := by
  have hpartition : ∀ i : ι, ∃! n : ℕ, i ∈ ({i | shell i = n} : Set ι) := by
    intro i
    refine ⟨shell i, rfl, ?_⟩
    intro n hn
    exact hn.symm
  rw [summable_partition (s := fun n ↦ {i | shell i = n})
    (fun i ↦ div_nonneg (hmass i) (pow_nonneg (Nat.cast_nonneg _) 4))
    hpartition]
  constructor
  · intro n
    apply ((hfiber n).div_const (((n + 1 : ℕ) : ℝ) ^ 4)).congr
    intro i
    rw [i.2]
  · have hpseries : Summable (fun n : ℕ ↦ C / (((n + 1 : ℕ) : ℝ) ^ 3)) := by
      have hbase : Summable (fun n : ℕ ↦ 1 / ((n : ℝ) ^ 3)) :=
        Real.summable_one_div_nat_pow.mpr (by norm_num)
      have hshift : Summable (fun n : ℕ ↦ 1 / (((n + 1 : ℕ) : ℝ) ^ 3)) := by
        exact (summable_nat_add_iff 1).mpr hbase
      simpa [div_eq_mul_inv] using hshift.mul_left C
    apply hpseries.of_nonneg_of_le
    · intro n
      exact tsum_nonneg fun i ↦ div_nonneg (hmass i.1)
        (pow_nonneg (Nat.cast_nonneg _) 4)
    · intro n
      have hden : 0 < (((n + 1 : ℕ) : ℝ) ^ 4) := by positivity
      calc
        ∑' i : {i : ι // shell i = n},
            mass i.1 / ((shell i.1 + 1 : ℕ) : ℝ) ^ 4 =
            (∑' i : {i : ι // shell i = n}, mass i.1) /
              (((n + 1 : ℕ) : ℝ) ^ 4) := by
              have hshell : ∀ i : {i : ι // shell i = n}, shell i.1 = n := fun i ↦ i.2
              simp_rw [hshell, tsum_div_const]
        _ ≤ (C * (n + 1)) / (((n + 1 : ℕ) : ℝ) ^ 4) :=
          div_le_div_of_nonneg_right (hlinear n) hden.le
        _ = C / (((n + 1 : ℕ) : ℝ) ^ 3) := by
          have hn : (((n + 1 : ℕ) : ℝ)) ≠ 0 := by positivity
          field_simp
          push_cast
          ring

end RiemannLab
