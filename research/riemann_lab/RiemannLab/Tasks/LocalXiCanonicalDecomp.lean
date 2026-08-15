import RiemannLab.Tasks.LocalAnalyticLog
import Mathlib.Analysis.Complex.CanonicalDecomposition

namespace RiemannLab

open Complex Set MeromorphicOn

/-!
The radius-four Jensen geometry is most naturally centred at the origin after
translation.  This module locks that translation and applies Mathlib's local
canonical decomposition to the actual entire xi-function.  The resulting
remainder is in meromorphic normal form and has neither zeros nor poles in the
open disk; it is the object to which `LocalAnalyticLog` applies.
-/

/-- Xi translated so that the moving Jensen centre is the origin. -/
noncomputable def translatedXi (T : ℝ) (z : ℂ) : ℂ :=
  riemannXiEntire (z + riemannXiJensenCenter T)

@[simp] theorem translatedXi_zero (T : ℝ) :
    translatedXi T 0 = riemannXiEntire (riemannXiJensenCenter T) := by
  simp [translatedXi]

theorem translatedXi_zero_ne (T : ℝ) : translatedXi T 0 ≠ 0 := by
  simpa using riemannXiEntire_ne_zero_jensenCenter T

theorem analyticAt_translatedXi (T : ℝ) (z : ℂ) :
    AnalyticAt ℂ (translatedXi T) z := by
  unfold translatedXi
  simpa [Function.comp_def] using
    (analyticAt_riemannXiEntire _).comp (analyticAt_id.add analyticAt_const)

theorem analyticOnNhd_translatedXi (T : ℝ) (U : Set ℂ) :
    AnalyticOnNhd ℂ (translatedXi T) U :=
  fun z _ ↦ analyticAt_translatedXi T z

theorem meromorphicOn_translatedXi_closedBall_seven_halves (T : ℝ) :
    MeromorphicOn (translatedXi T) (Metric.closedBall 0 (7 / 2 : ℝ)) :=
  (analyticOnNhd_translatedXi T _).meromorphicOn

theorem translatedXi_order_ne_top (T : ℝ)
    (z : Metric.closedBall (0 : ℂ) (7 / 2 : ℝ)) :
    meromorphicOrderAt (translatedXi T) z ≠ ⊤ := by
  have horder : analyticOrderAt (translatedXi T) (z : ℂ) ≠ ⊤ :=
    (analyticOnNhd_translatedXi T (Metric.closedBall 0 (7 / 2 : ℝ))).analyticOrderAt_ne_top_of_isPreconnected
      Metric.isPreconnected_closedBall (x := (0 : ℂ)) (y := (z : ℂ))
      (by norm_num) z.2 (by
        rw [(analyticAt_translatedXi T 0).analyticOrderAt_eq_zero.2
          (translatedXi_zero_ne T)]
        simp)
  rw [(analyticAt_translatedXi T z).meromorphicOrderAt_eq]
  simp [horder]

/-- The canonical radius-seven-halves decomposition of the translated xi-function.
This is an existence theorem, not a choice of a global Hadamard product. -/
theorem exists_translatedXi_canonicalDecomp (T : ℝ) :
    ∃ g : ℂ → ℂ, CanonicalDecomp (translatedXi T) g (7 / 2 : ℝ) := by
  exact (meromorphicOn_translatedXi_closedBall_seven_halves T).exists_canonicalDecomp
    (translatedXi_order_ne_top T)

/-- A fixed canonical remainder, used only through its verified specification. -/
noncomputable def translatedXiRemainder (T : ℝ) : ℂ → ℂ :=
  Classical.choose (exists_translatedXi_canonicalDecomp T)

theorem translatedXiRemainder_spec (T : ℝ) :
    CanonicalDecomp (translatedXi T) (translatedXiRemainder T) (7 / 2 : ℝ) :=
  Classical.choose_spec (exists_translatedXi_canonicalDecomp T)

theorem translatedXiRemainder_ne_zero (T : ℝ) {z : ℂ}
    (hz : z ∈ Metric.ball (0 : ℂ) (7 / 2 : ℝ)) :
    translatedXiRemainder T z ≠ 0 :=
  (translatedXiRemainder_spec T).ne_zero z hz

theorem analyticOnNhd_translatedXiRemainder_ball (T : ℝ) :
    AnalyticOnNhd ℂ (translatedXiRemainder T) (Metric.ball 0 (7 / 2 : ℝ)) := by
  intro z hz
  have hnf := (translatedXiRemainder_spec T).meromorphicNFOn
    (Metric.ball_subset_closedBall hz)
  apply hnf.meromorphicOrderAt_nonneg_iff_analyticAt.1
  rw [hnf.meromorphicOrderAt_eq_zero_iff.2
    (translatedXiRemainder_ne_zero T hz)]

/-- Once the normalized canonical remainder is bounded by `A` on the
radius-seven-halves disk, its logarithmic derivative is bounded explicitly on
the radius-thirteen-quarters disk.  The constant `448` is the exact output of the
Borel--Carathéodory/Cauchy argument with these two radii. -/
theorem norm_logDeriv_translatedXiRemainder_le
    {T A : ℝ} (hA : 1 ≤ A)
    (hbound : ∀ w ∈ Metric.ball (0 : ℂ) (7 / 2 : ℝ),
      ‖(translatedXiRemainder T 0)⁻¹ * translatedXiRemainder T w‖ ≤ A)
    {z : ℂ} (hz : z ∈ Metric.closedBall (0 : ℂ) (13 / 4 : ℝ)) :
    ‖logDeriv (translatedXiRemainder T) z‖ ≤
      448 * analyticLogBorelBound A := by
  have h := norm_logDeriv_le_of_normalized_bound
    (g := translatedXiRemainder T) (c := (0 : ℂ)) (z := z)
    (R := (7 / 2 : ℝ)) (r := (13 / 4 : ℝ)) (A := A)
    (by norm_num) (by norm_num) (by norm_num) hA
    (analyticOnNhd_translatedXiRemainder_ball T)
    (fun w hw ↦ translatedXiRemainder_ne_zero T hw) hbound hz
  convert h using 1 <;> ring

end RiemannLab
