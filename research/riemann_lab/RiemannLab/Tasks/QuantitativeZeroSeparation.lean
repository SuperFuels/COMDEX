import RiemannLab.Tasks.SharpJensenZeroCount
import Mathlib.Data.Fintype.Pigeonhole

namespace RiemannLab

open Set

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

end RiemannLab
