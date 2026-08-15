import RiemannLab.Tasks.ZetaJensenShells

namespace RiemannLab

/-!
# Globally summable positive-height zeta divisor

The verified unit shells are assembled into one countable dependent sum.
Fourth-power damping makes the complete multiplicity-weighted positive-height
divisor summable.  Every zero with ordinate at least two occurs in exactly one
shell.
-/

/-- A multiplicity-bearing point in the `n`th verified positive zeta shell. -/
def PositiveZetaShellPoint (n : ℕ) :=
  {ρ : ℂ // ρ ∈ positiveUnitZetaShellFinset (n + 2)}

noncomputable instance (n : ℕ) : Fintype (PositiveZetaShellPoint n) :=
  Fintype.ofFinset (positiveUnitZetaShellFinset (n + 2)) (by
    intro ρ
    rfl)

/-- The disjoint union of all verified positive-height shells. -/
def PositiveHighZetaShellIndex := Σ n : ℕ, PositiveZetaShellPoint n

/-- Fourth-power damped xi multiplicity on the shell union. -/
noncomputable def positiveHighZetaDampedMass
    (i : PositiveHighZetaShellIndex) : ℝ :=
  analyticOrderNatAt riemannXiEntire i.2.1 / (((i.1 + 1 : ℕ) : ℝ) ^ 4)

theorem positiveHighZetaDampedMass_nonneg
    (i : PositiveHighZetaShellIndex) :
    0 ≤ positiveHighZetaDampedMass i := by
  exact div_nonneg (Nat.cast_nonneg _) (pow_nonneg (Nat.cast_nonneg _) 4)

/-- The full positive-height multiplicity divisor is summable after fourth-
power shell damping. -/
theorem summable_positiveHighZetaDampedMass :
    Summable positiveHighZetaDampedMass := by
  unfold PositiveHighZetaShellIndex positiveHighZetaDampedMass
  apply (summable_sigma_of_nonneg (fun i ↦ div_nonneg (Nat.cast_nonneg _)
    (pow_nonneg (Nat.cast_nonneg _) 4))).2
  constructor
  · intro n
    exact Summable.of_finite
  · have hpseries : Summable (fun n : ℕ ↦
        zetaShellLinearConstant / (((n + 1 : ℕ) : ℝ) ^ 3)) := by
      have hbase : Summable (fun n : ℕ ↦ 1 / ((n : ℝ) ^ 3)) :=
        Real.summable_one_div_nat_pow.mpr (by norm_num)
      have hshift : Summable (fun n : ℕ ↦
          1 / (((n + 1 : ℕ) : ℝ) ^ 3)) :=
        (summable_nat_add_iff 1).mpr hbase
      simpa [div_eq_mul_inv] using hshift.mul_left zetaShellLinearConstant
    apply hpseries.of_nonneg_of_le
    · intro n
      exact tsum_nonneg fun i ↦ positiveHighZetaDampedMass_nonneg ⟨n, i⟩
    · intro n
      rw [tsum_fintype]
      change (∑ ρ : PositiveZetaShellPoint n,
          (analyticOrderNatAt riemannXiEntire ρ.1 : ℝ) /
            (((n + 1 : ℕ) : ℝ) ^ 4)) ≤ _
      rw [← Finset.sum_div]
      have hmass := positiveUnitZetaShell_multiplicity_le_linear n
      have hden : 0 < (((n + 1 : ℕ) : ℝ) ^ 4) := by positivity
      calc
        (∑ ρ : PositiveZetaShellPoint n,
            (analyticOrderNatAt riemannXiEntire ρ.1 : ℝ)) /
              (((n + 1 : ℕ) : ℝ) ^ 4) =
            (∑ ρ ∈ positiveUnitZetaShellFinset (n + 2),
              (analyticOrderNatAt riemannXiEntire ρ : ℝ)) /
              (((n + 1 : ℕ) : ℝ) ^ 4) := by
              congr 1
              exact (Finset.sum_subtype
                (positiveUnitZetaShellFinset (n + 2))
                (fun ρ ↦ Iff.rfl)
                (fun ρ ↦ (analyticOrderNatAt riemannXiEntire ρ : ℝ))).symm
        _ ≤ (zetaShellLinearConstant * (n + 1)) /
              (((n + 1 : ℕ) : ℝ) ^ 4) :=
            div_le_div_of_nonneg_right hmass hden.le
        _ = zetaShellLinearConstant / (((n + 1 : ℕ) : ℝ) ^ 3) := by
            have hn : (((n + 1 : ℕ) : ℝ)) ≠ 0 := by positivity
            field_simp
            push_cast
            ring

/-- Every nontrivial zero with ordinate at least two occurs in one of the
positive shells. -/
theorem exists_mem_positiveUnitZetaShellFinset
    {ρ : ℂ} (hρ : IsNontrivialZetaZero ρ) (him : 2 ≤ ρ.im) :
    ∃ n : ℕ, ρ ∈ positiveUnitZetaShellFinset (n + 2) := by
  let k : ℕ := ⌊ρ.im⌋₊
  have hk2 : 2 ≤ k := by
    exact (Nat.le_floor_iff (by linarith : 0 ≤ ρ.im)).mpr him
  let n := k - 2
  have hnk : n + 2 = k := Nat.sub_add_cancel hk2
  have hnkR : (n : ℝ) + 2 = k := by exact_mod_cast hnk
  refine ⟨n, mem_positiveUnitZetaShellFinset.mpr ⟨hρ, ?_, ?_⟩⟩
  · rw [hnkR]
    exact_mod_cast Nat.floor_le (by linarith : 0 ≤ ρ.im)
  · rw [hnkR]
    exact_mod_cast Nat.lt_floor_add_one ρ.im

/-- Distinct unit shells cannot contain the same zero. -/
theorem positiveUnitZetaShellFinset_index_unique
    {m n : ℕ} {ρ : ℂ}
    (hm : ρ ∈ positiveUnitZetaShellFinset (m + 2))
    (hn : ρ ∈ positiveUnitZetaShellFinset (n + 2)) :
    m = n := by
  have hm' := mem_positiveUnitZetaShellFinset.mp hm
  have hn' := mem_positiveUnitZetaShellFinset.mp hn
  have hmr : (m : ℝ) < n + 1 := by linarith [hm'.2.1, hn'.2.2]
  have hnr : (n : ℝ) < m + 1 := by linarith [hn'.2.1, hm'.2.2]
  exact_mod_cast (Nat.lt_succ_iff.mp (by exact_mod_cast hmr)).antisymm
    (Nat.lt_succ_iff.mp (by exact_mod_cast hnr))

end RiemannLab
