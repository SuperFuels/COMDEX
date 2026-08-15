import RiemannLab.Tasks.SharpJensenZeroCount
import Mathlib.Data.Fintype.Pigeonhole

namespace RiemannLab

open Set MeromorphicOn

/-!
A finite, quantitative avoidance lemma used to turn the local Jensen count
into admissible contour heights.  The proof is a discrete pigeonhole
argument on an equally spaced grid, so it introduces no measure theory.
-/

/-- Among `card E + 1` equally spaced test heights in an interval, one stays
at least half a mesh away from every member of `E`. -/
theorem exists_height_separated_from_finset
    (E : Finset ℝ) {a b : ℝ} (hab : a < b) :
    ∃ T ∈ Icc a b, ∀ y ∈ E,
      (b - a) / (2 * (E.card + 2)) ≤ |T - y| := by
  let d : ℝ := (b - a) / (E.card + 2)
  let grid : Fin (E.card + 1) → ℝ := fun i ↦
    a + ((i.1 + 1 : ℕ) : ℝ) * d
  have hd : 0 < d := by
    dsimp [d]
    positivity
  have hgrid (i : Fin (E.card + 1)) : grid i ∈ Icc a b := by
    constructor
    · have hprod : 0 ≤ ((i.1 + 1 : ℕ) : ℝ) * d := by positivity
      dsimp [grid]
      linarith
    · have hi : (i.1 + 1 : ℝ) ≤ E.card + 1 := by
        exact_mod_cast i.2
      have hden : (0 : ℝ) < E.card + 2 := by positivity
      have hquot : ((i.1 + 1 : ℕ) : ℝ) * d ≤ b - a := by
        dsimp [d]
        calc
          ((i.1 + 1 : ℕ) : ℝ) * ((b - a) / (E.card + 2)) =
              (((i.1 + 1 : ℕ) : ℝ) * (b - a)) / (E.card + 2) := by ring
          _ ≤ b - a := by
            apply (div_le_iff₀ hden).2
            have hcoef : ((i.1 + 1 : ℕ) : ℝ) ≤ E.card + 2 := by
              norm_num only [Nat.cast_add, Nat.cast_one] at hi ⊢
              linarith
            nlinarith [mul_le_mul_of_nonneg_right hcoef (sub_nonneg.mpr hab.le)]
      dsimp [grid]
      linarith
  by_contra h
  push_neg at h
  have hnear : ∀ i : Fin (E.card + 1),
      ∃ y ∈ E, |grid i - y| < d / 2 := by
    intro i
    obtain ⟨y, hyE, hy⟩ := h (grid i) (hgrid i)
    refine ⟨y, hyE, ?_⟩
    have heq : (b - a) / (2 * (E.card + 2)) = d / 2 := by
      dsimp [d]
      field_simp
      <;> ring
    rw [← heq]
    exact hy
  let near : Fin (E.card + 1) → {y // y ∈ E} := fun i ↦
    ⟨Classical.choose (hnear i), (Classical.choose_spec (hnear i)).1⟩
  have hnear' (i : Fin (E.card + 1)) :
      |grid i - (near i : ℝ)| < d / 2 :=
    (Classical.choose_spec (hnear i)).2
  have hcard : Fintype.card {y // y ∈ E} <
      Fintype.card (Fin (E.card + 1)) := by
    simp
  obtain ⟨i, j, hij, hsame⟩ :=
    Fintype.exists_ne_map_eq_of_card_lt near hcard
  have hsum : |grid i - (near i : ℝ)| +
      |grid j - (near j : ℝ)| < d := by
    linarith [hnear' i, hnear' j]
  have hclose : |grid i - grid j| < d := by
    calc
      |grid i - grid j| =
          |(grid i - (near i : ℝ)) - (grid j - (near j : ℝ))| := by
        rw [hsame]
        congr 1
        ring
      _ ≤ |grid i - (near i : ℝ)| +
          |grid j - (near j : ℝ)| := abs_sub _ _
      _ < d := hsum
  have hvals : i.1 < j.1 ∨ j.1 < i.1 := by
    apply Nat.lt_or_gt_of_ne
    intro heq
    exact hij (Fin.ext heq)
  rcases hvals with hijv | hjiv
  · have hcast : ((i.1 : ℕ) : ℝ) + 1 ≤ (j.1 : ℕ) := by
      exact_mod_cast hijv
    have hcoef : ((i.1 + 1 : ℕ) : ℝ) + 1 ≤ (j.1 + 1 : ℕ) := by
      push_cast
      linarith
    have hmul := mul_le_mul_of_nonneg_right hcoef hd.le
    have hsep : d ≤ |grid i - grid j| := by
      have hsign : grid i - grid j ≤ 0 := by
        dsimp [grid]
        nlinarith
      rw [abs_of_nonpos hsign]
      dsimp [grid]
      nlinarith
    linarith
  · have hcast : ((j.1 : ℕ) : ℝ) + 1 ≤ (i.1 : ℕ) := by
      exact_mod_cast hjiv
    have hcoef : ((j.1 + 1 : ℕ) : ℝ) + 1 ≤ (i.1 + 1 : ℕ) := by
      push_cast
      linarith
    have hmul := mul_le_mul_of_nonneg_right hcoef hd.le
    have hsep : d ≤ |grid i - grid j| := by
      have hsign : 0 ≤ grid i - grid j := by
        dsimp [grid]
        nlinarith
      rw [abs_of_nonneg hsign]
      dsimp [grid]
      nlinarith
    linarith

/-- The finite support of the xi divisor in the radius-three Jensen disk. -/
noncomputable def xiJensenDivisorSupport (T : ℝ) : Finset ℂ :=
  ((divisor riemannXiEntire
    (Metric.closedBall (riemannXiJensenCenter T) 3)).finiteSupport
      (isCompact_closedBall _ _)).toFinset

@[simp] theorem mem_xiJensenDivisorSupport {T : ℝ} {z : ℂ} :
    z ∈ xiJensenDivisorSupport T ↔
      divisor riemannXiEntire
        (Metric.closedBall (riemannXiJensenCenter T) 3) z ≠ 0 := by
  simp [xiJensenDivisorSupport, Function.mem_support]

/-- Each point in the support contributes at least one to the analytic xi
divisor, so its cardinality is bounded by the multiplicity-aware Jensen sum. -/
theorem xiJensenDivisorSupport_card_le_finsum (T : ℝ) :
    (xiJensenDivisorSupport T).card ≤
      ∑ᶠ u, divisor riemannXiEntire
        (Metric.closedBall (riemannXiJensenCenter T) 3) u := by
  let D := divisor riemannXiEntire
    (Metric.closedBall (riemannXiJensenCenter T) 3)
  have hana : AnalyticOnNhd ℂ riemannXiEntire
      (Metric.closedBall (riemannXiJensenCenter T) 3) :=
    fun z _ ↦ analyticAt_riemannXiEntire z
  rw [finsum_eq_sum_of_support_subset (s := xiJensenDivisorSupport T)]
  · change ((xiJensenDivisorSupport T).card : ℤ) ≤
        ∑ u ∈ xiJensenDivisorSupport T, D u
    rw [Finset.card_eq_sum_ones]
    push_cast
    apply Finset.sum_le_sum
    intro z hz
    have hzD : D z ≠ 0 := by
      simpa [xiJensenDivisorSupport, D, Function.mem_support] using hz
    have hz0 : 0 ≤ D z := hana.divisor_nonneg z
    omega
  · intro z hz
    simpa [xiJensenDivisorSupport, D, Function.mem_support] using hz

theorem xiJensenDivisorSupport_card_le_log
    {T : ℝ} (hT : 2 ≤ T) :
    ((xiJensenDivisorSupport T).card : ℝ) ≤
      (Real.log jensenQuotientPolynomialConstant + 12 * Real.log T) /
        Real.log (4 / 3) := by
  have hcard := xiJensenDivisorSupport_card_le_finsum T
  have hcardR : ((xiJensenDivisorSupport T).card : ℝ) ≤
      ((∑ᶠ u, divisor riemannXiEntire
        (Metric.closedBall (riemannXiJensenCenter T) 3) u : ℤ) : ℝ) := by
    exact_mod_cast hcard
  exact hcardR.trans (riemannXiEntire_local_zero_count_le_log hT)

noncomputable def xiJensenZeroOrdinates (T : ℝ) : Finset ℝ :=
  (xiJensenDivisorSupport T).image Complex.im

/-- Quantitative height selection for the actual finite xi divisor support.
The following cardinal estimate turns this denominator into `O(log T)`. -/
theorem exists_height_separated_from_xiJensenZeros
    (T : ℝ) {a b : ℝ} (hab : a < b) :
    ∃ H ∈ Icc a b, ∀ z ∈ xiJensenDivisorSupport T,
      (b - a) / (2 * ((xiJensenZeroOrdinates T).card + 2)) ≤
        |H - z.im| := by
  obtain ⟨H, hHab, hH⟩ :=
    exists_height_separated_from_finset (xiJensenZeroOrdinates T) hab
  refine ⟨H, hHab, ?_⟩
  intro z hz
  exact hH z.im (Finset.mem_image.mpr ⟨z, hz, rfl⟩)

end RiemannLab
