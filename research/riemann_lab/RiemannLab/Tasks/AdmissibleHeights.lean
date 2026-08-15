import RiemannLab.Tasks.ContourEdgeEstimates
import Mathlib.Order.Interval.Set.Infinite

namespace RiemannLab

open Filter Metric Set
open scoped Topology Interval

/-!
The geometric part of the admissible-height construction.  Compact
discreteness of the zeta zero set lets us select, in every unit interval high
in the upper half-plane, a horizontal line containing no zeta zero.  No growth
estimate for `ζ'/ζ` is asserted here.
-/

/-- The finite set of all zeta zeros in the closed ball of natural radius
`N`. -/
noncomputable def zetaZerosInClosedBall (N : ℕ) : Finset ℂ :=
  ((isCompact_closedBall (0 : ℂ) N).inter_riemannZetaZeros_finite).toFinset

@[simp]
theorem mem_zetaZerosInClosedBall {N : ℕ} {z : ℂ} :
    z ∈ zetaZerosInClosedBall N ↔ ‖z‖ ≤ N ∧ riemannZeta z = 0 := by
  simp [zetaZerosInClosedBall, mem_closedBall, mem_riemannZetaZeros]

/-- Ordinates of the finitely many zeros in a closed ball. -/
noncomputable def zetaZeroOrdinatesInClosedBall (N : ℕ) : Finset ℝ :=
  (zetaZerosInClosedBall N).image Complex.im

/-- Every interval `(n+2,n+3)` contains an ordinate which is not the
imaginary part of any zeta zero. -/
theorem exists_zero_free_horizontal_height (n : ℕ) :
    ∃ T : ℝ,
      (n : ℝ) + 2 < T ∧ T < (n : ℝ) + 3 ∧
      ∀ σ : ℝ, riemannZeta (σ + T * Complex.I) ≠ 0 := by
  let J : Set ℝ := Ioo ((n : ℝ) + 2) ((n : ℝ) + 3)
  let E : Finset ℝ := zetaZeroOrdinatesInClosedBall (n + 4)
  have hJinf : J.Infinite := by
    simpa only [J] using
      (Ioo_infinite (show (n : ℝ) + 2 < (n : ℝ) + 3 by linarith))
  have hnot : ¬ J ⊆ (E : Set ℝ) := by
    intro hsub
    exact hJinf ((E.finite_toSet).subset hsub)
  obtain ⟨T, hTJ, hTE⟩ := Set.not_subset.mp hnot
  refine ⟨T, hTJ.1, hTJ.2, ?_⟩
  intro σ hzeta
  let ρ : ℂ := σ + T * Complex.I
  have hρim : ρ.im = T := by simp [ρ]
  have hnontrivial : IsNontrivialZetaZero ρ := by
    refine ⟨hzeta, ?_⟩
    rintro ⟨k, hk⟩
    have him := congrArg Complex.im hk
    simp [ρ] at him
    linarith [hTJ.1]
  have hρnorm : ‖ρ‖ ≤ (n + 4 : ℕ) := by
    have hre : 0 < ρ.re := hnontrivial.re_pos
    have him : 0 < ρ.im := by rw [hρim]; linarith [hTJ.1]
    have hlt : ρ.re + ρ.im < (n : ℝ) + 4 := by
      rw [hρim]
      linarith [hnontrivial.re_lt_one, hTJ.2]
    have hbound := (Complex.norm_le_abs_re_add_abs_im ρ).trans
      (show |ρ.re| + |ρ.im| ≤ (n : ℝ) + 4 by
        rw [abs_of_pos hre, abs_of_pos him]
        exact hlt.le)
    simpa only [Nat.cast_add, Nat.cast_ofNat] using hbound
  have hρmem : ρ ∈ zetaZerosInClosedBall (n + 4) :=
    mem_zetaZerosInClosedBall.mpr ⟨hρnorm, hzeta⟩
  apply hTE
  simp only [E, zetaZeroOrdinatesInClosedBall, Finset.mem_coe,
    Finset.mem_image]
  exact ⟨ρ, hρmem, hρim⟩

/-- A canonical selected zero-free height in `(n+2,n+3)`. -/
noncomputable def admissibleZetaHeight (n : ℕ) : ℝ :=
  Classical.choose (exists_zero_free_horizontal_height n)

theorem admissibleZetaHeight_lower (n : ℕ) :
    (n : ℝ) + 2 < admissibleZetaHeight n :=
  (Classical.choose_spec (exists_zero_free_horizontal_height n)).1

theorem admissibleZetaHeight_upper (n : ℕ) :
    admissibleZetaHeight n < (n : ℝ) + 3 :=
  (Classical.choose_spec (exists_zero_free_horizontal_height n)).2.1

theorem riemannZeta_ne_zero_on_admissibleZetaHeight (n : ℕ) (σ : ℝ) :
    riemannZeta (σ + admissibleZetaHeight n * Complex.I) ≠ 0 :=
  (Classical.choose_spec (exists_zero_free_horizontal_height n)).2.2 σ

/-- By conjugation, the reflected lower horizontal line is also zero-free. -/
theorem riemannZeta_ne_zero_on_neg_admissibleZetaHeight (n : ℕ) (σ : ℝ) :
    riemannZeta (σ - admissibleZetaHeight n * Complex.I) ≠ 0 := by
  intro hz
  have hconj := riemannZeta_conj
    ((σ : ℂ) - admissibleZetaHeight n * Complex.I)
  rw [hz, map_zero] at hconj
  apply riemannZeta_ne_zero_on_admissibleZetaHeight n σ
  convert hconj using 1 <;> push_cast <;> simp

private theorem continuous_logDeriv_on_horizontalLine
    (n : ℕ) (sign : ℝ) (hsign : sign = 1 ∨ sign = -1)
    (hzero : ∀ σ : ℝ, riemannZeta
      ((σ : ℂ) + ((sign * admissibleZetaHeight n : ℝ) : ℂ) * Complex.I) ≠ 0) :
    Continuous (fun σ : ℝ ↦ ‖logDeriv riemannZeta
      ((σ : ℂ) + ((sign * admissibleZetaHeight n : ℝ) : ℂ) * Complex.I)‖) := by
  apply continuous_iff_continuousAt.2
  intro σ
  let s : ℂ := σ + ((sign * admissibleZetaHeight n : ℝ) : ℂ) * Complex.I
  have hheight : 0 < admissibleZetaHeight n :=
    lt_trans (by positivity) (admissibleZetaHeight_lower n)
  have hs1 : s ≠ 1 := by
    intro heq
    have him := congrArg Complex.im heq
    rcases hsign with rfl | rfl <;> simp [s] at him <;> linarith
  have hana : AnalyticAt ℂ riemannZeta s := analyticOn_riemannZeta s (by simpa using hs1)
  have hlog : ContinuousAt (logDeriv riemannZeta) s := by
    unfold logDeriv
    exact hana.deriv.continuousAt.div hana.continuousAt (hzero σ)
  have hline : ContinuousAt
      (fun t : ℝ ↦ (t : ℂ) +
        ((sign * admissibleZetaHeight n : ℝ) : ℂ) * Complex.I) σ := by
    fun_prop
  have houter : ContinuousAt (fun z : ℂ ↦ ‖logDeriv riemannZeta z‖)
      ((σ : ℂ) +
        ((sign * admissibleZetaHeight n : ℝ) : ℂ) * Complex.I) := by
    simpa only [s] using hlog.norm
  have hcomp : ContinuousAt
      ((fun z : ℂ ↦ ‖logDeriv riemannZeta z‖) ∘
        (fun t : ℝ ↦ (t : ℂ) +
          ((sign * admissibleZetaHeight n : ℝ) : ℂ) * Complex.I)) σ :=
    ContinuousAt.comp houter hline
  convert hcomp using 1
  funext t
  rfl

/-- On each selected upper and lower horizontal segment, `ζ'/ζ` has a
finite uniform bound.  The remaining classical issue is to control how these
bounds grow with `n`. -/
theorem exists_uniform_logDeriv_bound_on_admissible_segments
    (n : ℕ) (a b : ℝ) :
    ∃ C : ℝ, 0 ≤ C ∧ ∀ σ ∈ [[a, b]],
      ‖logDeriv riemannZeta
        ((σ : ℂ) + (admissibleZetaHeight n : ℂ) * Complex.I)‖ ≤ C ∧
      ‖logDeriv riemannZeta
        ((σ : ℂ) - (admissibleZetaHeight n : ℂ) * Complex.I)‖ ≤ C := by
  have hup : Continuous (fun σ : ℝ ↦ ‖logDeriv riemannZeta
      ((σ : ℂ) + (admissibleZetaHeight n : ℂ) * Complex.I)‖) := by
    simpa using continuous_logDeriv_on_horizontalLine n 1 (Or.inl rfl)
      (fun σ ↦ by simpa using riemannZeta_ne_zero_on_admissibleZetaHeight n σ)
  have hdown : Continuous (fun σ : ℝ ↦ ‖logDeriv riemannZeta
      ((σ : ℂ) - (admissibleZetaHeight n : ℂ) * Complex.I)‖) := by
    have h := continuous_logDeriv_on_horizontalLine n (-1) (Or.inr rfl)
      (fun σ ↦ ?_)
    · convert h using 1 <;> funext σ <;> congr 3 <;> push_cast <;> ring
    · convert riemannZeta_ne_zero_on_neg_admissibleZetaHeight n σ using 1 <;>
        push_cast <;> ring
  obtain ⟨Cu, hCu⟩ := bddAbove_def.mp
    (isCompact_uIcc.bddAbove_image hup.continuousOn)
  obtain ⟨Cd, hCd⟩ := bddAbove_def.mp
    (isCompact_uIcc.bddAbove_image hdown.continuousOn)
  refine ⟨max 0 (max Cu Cd), le_max_left _ _, ?_⟩
  intro σ hσ
  constructor
  · exact (hCu _ ⟨σ, hσ, rfl⟩).trans
      (le_trans (le_max_left Cu Cd) (le_max_right 0 (max Cu Cd)))
  · exact (hCd _ ⟨σ, hσ, rfl⟩).trans
      (le_trans (le_max_right Cu Cd) (le_max_right 0 (max Cu Cd)))

/-- The selected zero-free heights tend to infinity. -/
theorem tendsto_admissibleZetaHeight_atTop :
    Tendsto admissibleZetaHeight atTop atTop := by
  refine tendsto_atTop.2 fun b ↦ ?_
  obtain ⟨N, hN⟩ := exists_nat_ge b
  filter_upwards [eventually_ge_atTop N] with n hn
  calc
    b ≤ (N : ℝ) := hN
    _ ≤ (n : ℝ) := by exact_mod_cast hn
    _ ≤ admissibleZetaHeight n := le_of_lt
      (lt_trans (lt_add_of_pos_right _ (by norm_num))
        (admissibleZetaHeight_lower n))

end RiemannLab
