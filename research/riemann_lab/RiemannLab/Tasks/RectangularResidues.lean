import RiemannLab.Tasks.TrivialZeroResidues
import Mathlib.Analysis.SpecialFunctions.Complex.LogDeriv

namespace RiemannLab

open Set
open scoped Interval

/-!
The rectangular Cauchy kernel and finite-pole residue theorem needed for the
global contour shift.  This file deliberately uses the same four oriented
interval integrals as `rectangleBoundaryIntegral`.
-/

private theorem integral_horizontal_cauchyKernel
    (a b u v : ℝ) (hv : v ≠ 0) :
    (∫ x in a..b, ((x - u : ℝ) + v * Complex.I : ℂ)⁻¹) =
      Complex.log ((b - u : ℝ) + v * Complex.I) -
        Complex.log ((a - u : ℝ) + v * Complex.I) := by
  apply intervalIntegral.integral_eq_sub_of_hasDerivAt
  · intro x hx
    have hslit : ((x - u : ℝ) + v * Complex.I : ℂ) ∈ Complex.slitPlane := by
      rw [Complex.mem_slitPlane_iff]
      right
      simpa using hv
    have hline : HasDerivAt (fun x : ℝ ↦ ((x - u : ℝ) + v * Complex.I : ℂ)) 1 x := by
      simpa using ((hasDerivAt_id x).sub_const u).ofReal_comp.add_const (v * Complex.I)
    simpa [div_eq_mul_inv] using hline.clog_real hslit
  · apply Continuous.intervalIntegrable
    apply Continuous.inv₀ (by fun_prop)
    intro x hzero
    have him := congrArg Complex.im hzero
    simp at him
    exact hv him

private theorem integral_vertical_cauchyKernel
    (a b u v : ℝ) (hu : 0 < u) :
    Complex.I * (∫ y in a..b, ((u : ℝ) + (y - v) * Complex.I : ℂ)⁻¹) =
      Complex.log ((u : ℝ) + (b - v) * Complex.I) -
        Complex.log ((u : ℝ) + (a - v) * Complex.I) := by
  have hIntegral :
      (∫ y in a..b, Complex.I * ((u : ℝ) + (y - v) * Complex.I : ℂ)⁻¹) =
        Complex.log ((u : ℝ) + (b - v) * Complex.I) -
          Complex.log ((u : ℝ) + (a - v) * Complex.I) := by
    apply intervalIntegral.integral_eq_sub_of_hasDerivAt
    · intro y hy
      have hslit : ((u : ℝ) + (y - v) * Complex.I : ℂ) ∈ Complex.slitPlane := by
        rw [Complex.mem_slitPlane_iff]
        left
        simpa using hu
      have hline : HasDerivAt (fun y : ℝ ↦ ((u : ℝ) + (y - v) * Complex.I : ℂ))
          Complex.I y := by
        simpa using (((hasDerivAt_id y).sub_const v).ofReal_comp.mul_const
          Complex.I).const_add (u : ℂ)
      simpa [div_eq_mul_inv] using hline.clog_real hslit
    · apply Continuous.intervalIntegrable
      apply Continuous.mul (by fun_prop)
      apply Continuous.inv₀ (by fun_prop)
      intro y hzero
      have hre := congrArg Complex.re hzero
      simp at hre
      exact hu.ne' hre
  calc
    Complex.I * (∫ y in a..b, ((u : ℝ) + (y - v) * Complex.I : ℂ)⁻¹) =
        ∫ y in a..b, Complex.I * ((u : ℝ) + (y - v) * Complex.I : ℂ)⁻¹ := by
          rw [intervalIntegral.integral_const_mul]
    _ = _ := hIntegral

private theorem integral_left_vertical_cauchyKernel
    (a b u v : ℝ) (hu : u < 0) :
    Complex.I * (∫ y in a..b, ((u : ℝ) + (y - v) * Complex.I : ℂ)⁻¹) =
      Complex.log (-((u : ℝ) + (b - v) * Complex.I)) -
        Complex.log (-((u : ℝ) + (a - v) * Complex.I)) := by
  have hIntegral :
      (∫ y in a..b, Complex.I * ((u : ℝ) + (y - v) * Complex.I : ℂ)⁻¹) =
        Complex.log (-((u : ℝ) + (b - v) * Complex.I)) -
          Complex.log (-((u : ℝ) + (a - v) * Complex.I)) := by
    apply intervalIntegral.integral_eq_sub_of_hasDerivAt
    · intro y hy
      have hslit : -((u : ℝ) + (y - v) * Complex.I : ℂ) ∈ Complex.slitPlane := by
        rw [Complex.mem_slitPlane_iff]
        left
        simpa using hu
      have hline : HasDerivAt
          (fun y : ℝ ↦ -((u : ℝ) + (y - v) * Complex.I : ℂ)) (-Complex.I) y := by
        have hbase : HasDerivAt
            (fun y : ℝ ↦ (u : ℂ) + ((y - v : ℝ) : ℂ) * Complex.I) Complex.I y := by
          simpa using (((hasDerivAt_id y).sub_const v).ofReal_comp.mul_const
            Complex.I).const_add (u : ℂ)
        apply hbase.neg.congr_of_eventuallyEq
        filter_upwards with t
        simp
      have hqne : ((u : ℝ) + (y - v) * Complex.I : ℂ) ≠ 0 := by
        intro hzero
        have hre := congrArg Complex.re hzero
        simp at hre
        exact hu.ne hre
      simpa only [div_eq_mul_inv, inv_neg, neg_mul_neg] using hline.clog_real hslit
    · apply Continuous.intervalIntegrable
      apply Continuous.mul (by fun_prop)
      apply Continuous.inv₀ (by fun_prop)
      intro y hzero
      have hre := congrArg Complex.re hzero
      simp at hre
      exact hu.ne hre
  calc
    Complex.I * (∫ y in a..b, ((u : ℝ) + (y - v) * Complex.I : ℂ)⁻¹) =
        ∫ y in a..b, Complex.I * ((u : ℝ) + (y - v) * Complex.I : ℂ)⁻¹ := by
          rw [intervalIntegral.integral_const_mul]
    _ = _ := hIntegral

private theorem log_neg_eq_add_pi_I_of_im_neg {q : ℂ} (hq : q.im < 0) :
    Complex.log (-q) = Complex.log q + Real.pi * Complex.I := by
  apply Complex.ext
  · simp [Complex.log_re]
  · simp [Complex.log_im, Complex.arg_neg_eq_arg_add_pi_of_im_neg hq]

private theorem log_neg_eq_sub_pi_I_of_im_pos {q : ℂ} (hq : 0 < q.im) :
    Complex.log (-q) = Complex.log q - Real.pi * Complex.I := by
  apply Complex.ext
  · simp [Complex.log_re]
  · simp [Complex.log_im, Complex.arg_neg_eq_arg_sub_pi_of_im_pos hq]

/-- The positively oriented boundary integral of the Cauchy kernel around an
axis-parallel rectangle is `2πi` when its pole is strictly inside. -/
theorem rectangleBoundaryIntegral_cauchyKernel
    {z w p : ℂ}
    (hre : z.re < p.re ∧ p.re < w.re)
    (him : z.im < p.im ∧ p.im < w.im) :
    rectangleBoundaryIntegral (fun s ↦ (s - p)⁻¹) z w =
      2 * Real.pi * Complex.I := by
  have hbottom := integral_horizontal_cauchyKernel z.re w.re p.re (z.im - p.im)
    (sub_ne_zero.mpr him.1.ne)
  have htop := integral_horizontal_cauchyKernel z.re w.re p.re (w.im - p.im)
    (sub_ne_zero.mpr him.2.ne')
  have hright := integral_vertical_cauchyKernel z.im w.im (w.re - p.re) p.im
    (sub_pos.mpr hre.2)
  have hleft := integral_left_vertical_cauchyKernel z.im w.im (z.re - p.re) p.im
    (sub_neg.mpr hre.1)
  rw [rectangleBoundaryIntegral]
  rw [← Complex.re_add_im p]
  have hdecomp (a b c d : ℝ) :
      (a : ℂ) + (b : ℂ) * Complex.I - ((c : ℂ) + (d : ℂ) * Complex.I) =
        ((a - c : ℝ) : ℂ) + ((b - d : ℝ) : ℂ) * Complex.I := by
    push_cast
    ring
  simp_rw [hdecomp]
  push_cast at hbottom htop hright hleft ⊢
  rw [hbottom, htop, hright, hleft]
  have hAlog := log_neg_eq_add_pi_I_of_im_neg
    (q := (z.re : ℂ) - p.re + ((z.im : ℂ) - p.im) * Complex.I)
    (by simpa using sub_neg.mpr him.1)
  have hDlog := log_neg_eq_sub_pi_I_of_im_pos
    (q := (z.re : ℂ) - p.re + ((w.im : ℂ) - p.im) * Complex.I)
    (by simpa using sub_pos.mpr him.2)
  rw [hAlog, hDlog]
  ring

/-- Integrability on the four real parametrizations of a rectangular
boundary.  Keeping this condition explicit makes the global theorem usable
for meromorphic functions without pretending they are continuous in the
rectangle's interior. -/
structure RectangleBoundaryIntegrable (f : ℂ → ℂ) (z w : ℂ) : Prop where
  bottom : IntervalIntegrable (fun x : ℝ ↦ f (x + z.im * Complex.I))
    MeasureTheory.volume z.re w.re
  top : IntervalIntegrable (fun x : ℝ ↦ f (x + w.im * Complex.I))
    MeasureTheory.volume z.re w.re
  right : IntervalIntegrable (fun y : ℝ ↦ f (w.re + y * Complex.I))
    MeasureTheory.volume z.im w.im
  left : IntervalIntegrable (fun y : ℝ ↦ f (z.re + y * Complex.I))
    MeasureTheory.volume z.im w.im

namespace RectangleBoundaryIntegrable

/-- Continuity on the closed rectangle supplies all four edge integrals. -/
theorem of_continuousOn {f : ℂ → ℂ} {z w : ℂ}
    (hf : ContinuousOn f ([[z.re, w.re]] ×ℂ [[z.im, w.im]])) :
    RectangleBoundaryIntegrable f z w := by
  constructor
  · apply ContinuousOn.intervalIntegrable
    exact hf.comp (by fun_prop) (by
      intro x hx
      simp only [Complex.mem_reProdIm]
      exact ⟨by simpa using hx, by simp⟩)
  · apply ContinuousOn.intervalIntegrable
    exact hf.comp (by fun_prop) (by
      intro x hx
      simp only [Complex.mem_reProdIm]
      exact ⟨by simpa using hx, by simp⟩)
  · apply ContinuousOn.intervalIntegrable
    exact hf.comp (by fun_prop) (by
      intro y hy
      simp only [Complex.mem_reProdIm]
      exact ⟨by simp, by simpa using hy⟩)
  · apply ContinuousOn.intervalIntegrable
    exact hf.comp (by fun_prop) (by
      intro y hy
      simp only [Complex.mem_reProdIm]
      exact ⟨by simp, by simpa using hy⟩)

/-- A Cauchy principal part whose pole is strictly inside the rectangle is
integrable on every boundary edge. -/
theorem principalPart_of_inside (r p z w : ℂ)
    (hre : z.re < p.re ∧ p.re < w.re)
    (him : z.im < p.im ∧ p.im < w.im) :
    RectangleBoundaryIntegrable (fun s ↦ r * (s - p)⁻¹) z w := by
  have continuousPrincipal {a : ℝ} (hne : ∀ t : ℝ,
      ((a : ℂ) + (t : ℂ) * Complex.I - p) ≠ 0) :
      Continuous (fun t : ℝ ↦ r * ((a : ℂ) + t * Complex.I - p)⁻¹) := by
    have hc : Continuous (fun t : ℝ ↦ (a : ℂ) + t * Complex.I - p) := by fun_prop
    exact continuous_const.mul (hc.inv₀ hne)
  constructor
  · apply Continuous.intervalIntegrable
    have hne : ∀ x : ℝ, ((x : ℂ) + z.im * Complex.I - p) ≠ 0 := by
      intro x hzero
      have himEq := congrArg Complex.im (sub_eq_zero.mp hzero)
      simp at himEq
      linarith [him.1]
    have hc : Continuous (fun x : ℝ ↦ (x : ℂ) + z.im * Complex.I - p) := by fun_prop
    exact continuous_const.mul (hc.inv₀ hne)
  · apply Continuous.intervalIntegrable
    have hne : ∀ x : ℝ, ((x : ℂ) + w.im * Complex.I - p) ≠ 0 := by
      intro x hzero
      have himEq := congrArg Complex.im (sub_eq_zero.mp hzero)
      simp at himEq
      linarith [him.2]
    have hc : Continuous (fun x : ℝ ↦ (x : ℂ) + w.im * Complex.I - p) := by fun_prop
    exact continuous_const.mul (hc.inv₀ hne)
  · exact (continuousPrincipal (a := w.re) (by
      intro y hzero
      have hreEq := congrArg Complex.re (sub_eq_zero.mp hzero)
      simp at hreEq
      linarith [hre.2])).intervalIntegrable z.im w.im
  · exact (continuousPrincipal (a := z.re) (by
      intro y hzero
      have hreEq := congrArg Complex.re (sub_eq_zero.mp hzero)
      simp at hreEq
      linarith [hre.1])).intervalIntegrable z.im w.im

theorem add {f g : ℂ → ℂ} {z w : ℂ}
    (hf : RectangleBoundaryIntegrable f z w)
    (hg : RectangleBoundaryIntegrable g z w) :
    RectangleBoundaryIntegrable (fun s ↦ f s + g s) z w :=
  ⟨hf.bottom.add hg.bottom, hf.top.add hg.top,
    hf.right.add hg.right, hf.left.add hg.left⟩

theorem finsetSum {ι : Type*} (P : Finset ι) {f : ι → ℂ → ℂ} {z w : ℂ}
    (hf : ∀ p ∈ P, RectangleBoundaryIntegrable (f p) z w) :
    RectangleBoundaryIntegrable (fun s ↦ ∑ p ∈ P, f p s) z w := by
  classical
  induction P using Finset.induction_on with
  | empty =>
      simp only [Finset.sum_empty]
      exact ⟨intervalIntegrable_const, intervalIntegrable_const,
        intervalIntegrable_const, intervalIntegrable_const⟩
  | @insert p P hp ih =>
      have hpint := hf p (Finset.mem_insert_self p P)
      have hPint : ∀ q ∈ P, RectangleBoundaryIntegrable (f q) z w :=
        fun q hq ↦ hf q (Finset.mem_insert_of_mem hq)
      have hadd := hpint.add (ih hPint)
      simpa only [Finset.sum_insert hp] using hadd

end RectangleBoundaryIntegrable

/-- Additivity of the oriented rectangle integral. -/
theorem rectangleBoundaryIntegral_add {f g : ℂ → ℂ} {z w : ℂ}
    (hf : RectangleBoundaryIntegrable f z w)
    (hg : RectangleBoundaryIntegrable g z w) :
    rectangleBoundaryIntegral (fun s ↦ f s + g s) z w =
      rectangleBoundaryIntegral f z w + rectangleBoundaryIntegral g z w := by
  unfold rectangleBoundaryIntegral
  rw [intervalIntegral.integral_add hf.bottom hg.bottom,
    intervalIntegral.integral_add hf.top hg.top,
    intervalIntegral.integral_add hf.right hg.right,
    intervalIntegral.integral_add hf.left hg.left]
  ring

/-- Scalar linearity of the oriented rectangle integral. -/
theorem rectangleBoundaryIntegral_const_mul (r : ℂ) (f : ℂ → ℂ) (z w : ℂ) :
    rectangleBoundaryIntegral (fun s ↦ r * f s) z w =
      r * rectangleBoundaryIntegral f z w := by
  unfold rectangleBoundaryIntegral
  simp only [intervalIntegral.integral_const_mul]
  ring

/-- A rectangular boundary integral commutes with a finite sum of
boundary-integrable functions. -/
theorem rectangleBoundaryIntegral_finsetSum {ι : Type*} (P : Finset ι)
    {f : ι → ℂ → ℂ} {z w : ℂ}
    (hf : ∀ p ∈ P, RectangleBoundaryIntegrable (f p) z w) :
    rectangleBoundaryIntegral (fun s ↦ ∑ p ∈ P, f p s) z w =
      ∑ p ∈ P, rectangleBoundaryIntegral (f p) z w := by
  classical
  induction P using Finset.induction_on with
  | empty => simp [rectangleBoundaryIntegral]
  | @insert p P hp ih =>
      have hpint := hf p (Finset.mem_insert_self p P)
      have hPint : ∀ q ∈ P, RectangleBoundaryIntegrable (f q) z w :=
        fun q hq ↦ hf q (Finset.mem_insert_of_mem hq)
      have hsumint := RectangleBoundaryIntegrable.finsetSum P hPint
      have hfun : (fun s ↦ ∑ q ∈ insert p P, f q s) =
          fun s ↦ f p s + ∑ q ∈ P, f q s := by
        funext s
        simp [hp]
      rw [hfun, rectangleBoundaryIntegral_add hpint hsumint, ih hPint]
      simp [hp]

/-- Finite global residue collection on a rectangle.  The meromorphic
function is presented as a holomorphic remainder plus its finite principal
parts.  Each pole must lie strictly inside, and no pole may occur on an edge.
-/
theorem rectangleBoundaryIntegral_holomorphic_add_principalParts
    {ι : Type*} (P : Finset ι) (g : ℂ → ℂ) (pole : ι → ℂ) (residue : ι → ℂ)
    {z w : ℂ}
    (hgcont : ContinuousOn g ([[z.re, w.re]] ×ℂ [[z.im, w.im]]))
    (hgdiff : DifferentiableOn ℂ g
      (Ioo (min z.re w.re) (max z.re w.re) ×ℂ
        Ioo (min z.im w.im) (max z.im w.im)))
    (hgint : RectangleBoundaryIntegrable g z w)
    (hpinside : ∀ p ∈ P,
      z.re < (pole p).re ∧ (pole p).re < w.re ∧
      z.im < (pole p).im ∧ (pole p).im < w.im)
    (hpint : ∀ p ∈ P, RectangleBoundaryIntegrable
      (fun s ↦ residue p * (s - pole p)⁻¹) z w) :
    rectangleBoundaryIntegral
        (fun s ↦ g s + ∑ p ∈ P, residue p * (s - pole p)⁻¹) z w =
      2 * Real.pi * Complex.I * ∑ p ∈ P, residue p := by
  have hsumint : RectangleBoundaryIntegrable
      (fun s ↦ ∑ p ∈ P, residue p * (s - pole p)⁻¹) z w :=
    RectangleBoundaryIntegrable.finsetSum P hpint
  rw [rectangleBoundaryIntegral_add hgint hsumint,
    rectangleBoundaryIntegral_eq_zero g z w hgcont hgdiff,
    zero_add, rectangleBoundaryIntegral_finsetSum P hpint]
  simp_rw [rectangleBoundaryIntegral_const_mul]
  have hp : ∀ p ∈ P,
      rectangleBoundaryIntegral (fun s ↦ (s - pole p)⁻¹) z w =
        2 * Real.pi * Complex.I := by
    intro p hp
    exact rectangleBoundaryIntegral_cauchyKernel
      ⟨(hpinside p hp).1, (hpinside p hp).2.1⟩
      ⟨(hpinside p hp).2.2.1, (hpinside p hp).2.2.2⟩
  rw [Finset.mul_sum]
  apply Finset.sum_congr rfl
  intro p hpP
  rw [hp p hpP]
  ring

/-- Assumption-minimal finite rectangular residue theorem.  All edge
integrability obligations are discharged from continuity and strict interior
containment. -/
theorem rectangleBoundaryIntegral_residue_finset
    {ι : Type*} (P : Finset ι) (g : ℂ → ℂ) (pole : ι → ℂ) (residue : ι → ℂ)
    {z w : ℂ}
    (hgcont : ContinuousOn g ([[z.re, w.re]] ×ℂ [[z.im, w.im]]))
    (hgdiff : DifferentiableOn ℂ g
      (Ioo (min z.re w.re) (max z.re w.re) ×ℂ
        Ioo (min z.im w.im) (max z.im w.im)))
    (hpinside : ∀ p ∈ P,
      z.re < (pole p).re ∧ (pole p).re < w.re ∧
      z.im < (pole p).im ∧ (pole p).im < w.im) :
    rectangleBoundaryIntegral
        (fun s ↦ g s + ∑ p ∈ P, residue p * (s - pole p)⁻¹) z w =
      2 * Real.pi * Complex.I * ∑ p ∈ P, residue p := by
  apply rectangleBoundaryIntegral_holomorphic_add_principalParts P g pole residue
    hgcont hgdiff (RectangleBoundaryIntegrable.of_continuousOn hgcont) hpinside
  intro p hp
  exact RectangleBoundaryIntegrable.principalPart_of_inside _ _ _ _
    ⟨(hpinside p hp).1, (hpinside p hp).2.1⟩
    ⟨(hpinside p hp).2.2.1, (hpinside p hp).2.2.2⟩

end RiemannLab
