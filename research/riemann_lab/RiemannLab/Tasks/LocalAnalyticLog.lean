import RiemannLab.Tasks.QuantitativeZeroSeparation
import Mathlib.Analysis.Complex.BorelCaratheodory
import Mathlib.Analysis.Complex.HasPrimitives
import Mathlib.Analysis.Complex.Liouville

namespace RiemannLab

open Complex Set

/-!
Quantitative logarithmic-derivative work is most economical on a zero-free
analytic remainder.  This module builds the required analytic logarithm on a
ball from Mathlib's primitive theorem, avoiding any choice of a global branch
of `Complex.log`.
-/

/-- A nonvanishing analytic function on a ball has a normalized analytic
logarithm whose derivative is its logarithmic derivative. -/
theorem exists_normalized_analyticLog_on_ball
    {g : ℂ → ℂ} {c : ℂ} {R : ℝ} (hR : 0 < R)
    (hg : AnalyticOnNhd ℂ g (Metric.ball c R))
    (hzero : ∀ z ∈ Metric.ball c R, g z ≠ 0) :
    ∃ h : ℂ → ℂ,
      h c = 0 ∧
      (∀ z ∈ Metric.ball c R, HasDerivAt h (logDeriv g z) z) ∧
      ∀ z ∈ Metric.ball c R,
        Complex.exp (h z) = (g c)⁻¹ * g z := by
  have hc : c ∈ Metric.ball c R := Metric.mem_ball_self hR
  have hlog : AnalyticOnNhd ℂ (logDeriv g) (Metric.ball c R) := by
    intro z hz
    unfold logDeriv
    exact (hg z hz).deriv.div (hg z hz) (hzero z hz)
  obtain ⟨h, hh0, hh⟩ :=
    hlog.differentiableOn.isExactOn_ball.with_val_at c 0
  refine ⟨h, hh0, hh, ?_⟩
  let q : ℂ → ℂ := fun z ↦ Complex.exp (h z)
  let p : ℂ → ℂ := fun z ↦ (g c)⁻¹ * g z
  have hhdiff : DifferentiableOn ℂ h (Metric.ball c R) :=
    fun z hz ↦ (hh z hz).differentiableAt.differentiableWithinAt
  have hqdiff : DifferentiableOn ℂ q (Metric.ball c R) := by
    intro z hz
    exact ((Complex.hasDerivAt_exp (h z)).comp z (hh z hz)).differentiableAt.differentiableWithinAt
  have hpdiff : DifferentiableOn ℂ p (Metric.ball c R) := by
    intro z hz
    exact (hg z hz).differentiableAt.const_mul ((g c)⁻¹)
      |>.differentiableWithinAt
  have hqzero : ∀ z ∈ Metric.ball c R, q z ≠ 0 := by
    intro z hz
    exact Complex.exp_ne_zero _
  have hgc : g c ≠ 0 := hzero c hc
  have hpzero : ∀ z ∈ Metric.ball c R, p z ≠ 0 := by
    intro z hz
    exact mul_ne_zero (inv_ne_zero hgc) (hzero z hz)
  have hlogeq : Set.EqOn (logDeriv q) (logDeriv p) (Metric.ball c R) := by
    intro z hz
    have hqderiv := (Complex.hasDerivAt_exp (h z)).comp z (hh z hz)
    have hqderiv' : HasDerivAt q
        (Complex.exp (h z) * logDeriv g z) z := by
      simpa [q, Function.comp_def] using hqderiv
    calc
      logDeriv q z = logDeriv g z := by
        rw [logDeriv_apply, hqderiv'.deriv]
        dsimp [q]
        field_simp [Complex.exp_ne_zero]
      _ = logDeriv p z := by
        symm
        exact logDeriv_const_mul z (g c)⁻¹ (inv_ne_zero hgc)
  obtain ⟨a, ha0, hae⟩ :=
    ((logDeriv_eqOn_iff hqdiff hpdiff Metric.isOpen_ball
      Metric.isPreconnected_ball hpzero hqzero).1 hlogeq)
  have hqc : q c = 1 := by simp [q, hh0]
  have hpc : p c = 1 := by simp [p, hgc]
  have hacoeff : a = 1 := by
    have := hae hc
    simp [hqc, hpc, q, p, hh0, hgc] at this
    exact this.symm
  intro z hz
  have := hae hz
  simpa [q, p, hacoeff] using this

noncomputable def analyticLogBorelBound (A : ℝ) : ℝ :=
  max 1 (Real.log A)

theorem analyticLogBorelBound_pos (A : ℝ) :
    0 < analyticLogBorelBound A :=
  lt_of_lt_of_le zero_lt_one (le_max_left _ _)

/-- Borel--Carathéodory applied to the normalized analytic logarithm.  The
hypothesis is deliberately stated for the normalized function, exactly as it
arises from the canonical decomposition. -/
theorem exists_normalized_analyticLog_norm_le
    {g : ℂ → ℂ} {c : ℂ} {R A : ℝ} (hR : 0 < R)
    (hA : 1 ≤ A)
    (hg : AnalyticOnNhd ℂ g (Metric.ball c R))
    (hzero : ∀ z ∈ Metric.ball c R, g z ≠ 0)
    (hbound : ∀ z ∈ Metric.ball c R, ‖(g c)⁻¹ * g z‖ ≤ A) :
    ∃ h : ℂ → ℂ,
      h c = 0 ∧
      (∀ z ∈ Metric.ball c R, HasDerivAt h (logDeriv g z) z) ∧
      (∀ z ∈ Metric.ball c R,
        Complex.exp (h z) = (g c)⁻¹ * g z) ∧
      ∀ z ∈ Metric.ball c R,
        ‖h z‖ ≤ 2 * analyticLogBorelBound A * ‖z - c‖ /
          (R - ‖z - c‖) := by
  obtain ⟨h, hc, hh, hexp⟩ :=
    exists_normalized_analyticLog_on_ball hR hg hzero
  refine ⟨h, hc, hh, hexp, ?_⟩
  let H : ℂ → ℂ := fun w ↦ h (c + w)
  have hHdiff : DifferentiableOn ℂ H (Metric.ball 0 R) := by
    intro w hw
    have hcw : c + w ∈ Metric.ball c R := by
      simpa [Metric.mem_ball, dist_eq_norm] using hw
    exact ((hh (c + w) hcw).differentiableAt.comp w
      ((hasDerivAt_const w c).add (hasDerivAt_id w)).differentiableAt).differentiableWithinAt
  have hmaps : Set.MapsTo H (Metric.ball 0 R)
      {w : ℂ | w.re ≤ analyticLogBorelBound A} := by
    intro w hw
    have hcw : c + w ∈ Metric.ball c R := by
      simpa [Metric.mem_ball, dist_eq_norm] using hw
    have hnorm : ‖Complex.exp (h (c + w))‖ ≤ A := by
      rw [hexp (c + w) hcw]
      exact hbound (c + w) hcw
    have hApos : 0 < A := zero_lt_one.trans_le hA
    have hrelog : (h (c + w)).re ≤ Real.log A := by
      apply (Real.le_log_iff_exp_le hApos).2
      simpa [Complex.norm_exp] using hnorm
    exact hrelog.trans (le_max_right _ _)
  have hH0 : H 0 = 0 := by simp [H, hc]
  intro z hz
  have hzc : z - c ∈ Metric.ball 0 R := by
    simpa [Metric.mem_ball, dist_eq_norm] using hz
  have hbc := Complex.borelCaratheodory_zero
    (M := analyticLogBorelBound A) (R := R) (f := H) (z := z - c)
    (analyticLogBorelBound_pos A) hHdiff hmaps hR hzc hH0
  simpa [H] using hbc

/-- Cauchy's derivative estimate turns the Borel bound for an analytic
logarithm into a uniform logarithmic-derivative bound on every smaller
concentric disk. -/
theorem norm_logDeriv_le_of_analyticLog_borel
    {g h : ℂ → ℂ} {c z : ℂ} {R r B : ℝ}
    (hR : 0 < R) (hr0 : 0 ≤ r) (hrR : r < R) (hB : 0 ≤ B)
    (hh : ∀ w ∈ Metric.ball c R, HasDerivAt h (logDeriv g w) w)
    (hhnorm : ∀ w ∈ Metric.ball c R,
      ‖h w‖ ≤ 2 * B * ‖w - c‖ / (R - ‖w - c‖))
    (hz : z ∈ Metric.closedBall c r) :
    ‖logDeriv g z‖ ≤ 8 * B * R / (R - r) ^ 2 := by
  let d : ℝ := (R - r) / 2
  have hd : 0 < d := by dsimp [d]; linarith
  have hzr : ‖z - c‖ ≤ r := by
    simpa [Metric.mem_closedBall, dist_eq_norm] using hz
  have hsubset : Metric.closedBall z d ⊆ Metric.ball c R := by
    intro w hw
    have hwz : ‖w - z‖ ≤ d := by
      simpa [Metric.mem_closedBall, dist_eq_norm] using hw
    have hwc : ‖w - c‖ ≤ d + r := by
      calc
        ‖w - c‖ = ‖(w - z) + (z - c)‖ := by congr 1 <;> ring
        _ ≤ ‖w - z‖ + ‖z - c‖ := norm_add_le _ _
        _ ≤ d + r := add_le_add hwz hzr
    have hdr : d + r < R := by dsimp [d]; linarith
    simpa [Metric.mem_ball, dist_eq_norm] using hwc.trans_lt hdr
  have hdiff : DifferentiableOn ℂ h (Metric.closedBall z d) := by
    intro w hw
    exact (hh w (hsubset hw)).differentiableAt.differentiableWithinAt
  have hC : ∀ w ∈ Metric.sphere z d,
      ‖h w‖ ≤ 2 * B * R / d := by
    intro w hw
    have hwclosed : w ∈ Metric.closedBall z d :=
      Metric.sphere_subset_closedBall hw
    have hwball := hsubset hwclosed
    have hwc_lt : ‖w - c‖ < R := by
      simpa [Metric.mem_ball, dist_eq_norm] using hwball
    have hwz : ‖w - z‖ = d := by
      simpa [Metric.mem_sphere, dist_eq_norm] using hw
    have hwc_le : ‖w - c‖ ≤ d + r := by
      calc
        ‖w - c‖ = ‖(w - z) + (z - c)‖ := by congr 1 <;> ring
        _ ≤ ‖w - z‖ + ‖z - c‖ := norm_add_le _ _
        _ ≤ d + r := by rw [hwz]; gcongr
    have hden : d ≤ R - ‖w - c‖ := by
      dsimp [d] at *
      linarith
    have hdenpos : 0 < R - ‖w - c‖ := sub_pos.mpr hwc_lt
    calc
      ‖h w‖ ≤ 2 * B * ‖w - c‖ / (R - ‖w - c‖) := hhnorm w hwball
      _ ≤ 2 * B * R / (R - ‖w - c‖) :=
        div_le_div_of_nonneg_right
          (mul_le_mul_of_nonneg_left hwc_lt.le (mul_nonneg (by norm_num) hB))
          hdenpos.le
      _ ≤ 2 * B * R / d :=
        div_le_div_of_nonneg_left
          (mul_nonneg (mul_nonneg (by norm_num) hB) hR.le) hd hden
  have hcauchy := Complex.norm_deriv_le_of_forall_mem_sphere_norm_le
    (f := h) hd (hdiff.mono Metric.closure_ball_subset_closedBall).diffContOnCl hC
  have hzball : z ∈ Metric.ball c R := hsubset (by simp [hd.le])
  rw [(hh z hzball).deriv] at hcauchy
  calc
    ‖logDeriv g z‖ ≤ (2 * B * R / d) / d := hcauchy
    _ = 8 * B * R / (R - r) ^ 2 := by
      dsimp [d]
      field_simp [sub_ne_zero.mpr hrR.ne]
      ring

theorem norm_logDeriv_le_of_normalized_bound
    {g : ℂ → ℂ} {c z : ℂ} {R r A : ℝ}
    (hR : 0 < R) (hr0 : 0 ≤ r) (hrR : r < R) (hA : 1 ≤ A)
    (hg : AnalyticOnNhd ℂ g (Metric.ball c R))
    (hzero : ∀ w ∈ Metric.ball c R, g w ≠ 0)
    (hbound : ∀ w ∈ Metric.ball c R, ‖(g c)⁻¹ * g w‖ ≤ A)
    (hz : z ∈ Metric.closedBall c r) :
    ‖logDeriv g z‖ ≤
      8 * analyticLogBorelBound A * R / (R - r) ^ 2 := by
  obtain ⟨h, hc, hh, hexp, hhnorm⟩ :=
    exists_normalized_analyticLog_norm_le hR hA hg hzero hbound
  exact norm_logDeriv_le_of_analyticLog_borel hR hr0 hrR
    (analyticLogBorelBound_pos A).le hh hhnorm hz

end RiemannLab
