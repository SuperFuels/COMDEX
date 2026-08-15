import RiemannLab.Tasks.RightHalfPlaneLogDerivBound
import Mathlib.Analysis.MellinInversion
import Mathlib.Analysis.Complex.JensenFormula

namespace RiemannLab

open Complex MeasureTheory MeromorphicOn
open scoped FourierTransform

/-!
Growth infrastructure for the entire completed-zeta function.  The key
observation is that Mathlib constructs it as a Mellin transform of a rapidly
decreasing modified theta kernel.  On a fixed vertical line the Mellin
transform is a Fourier transform, hence its norm is bounded by an `L¹` norm
which is independent of the ordinate.
-/

/-- The `L¹` majorant controlling a Mellin transform on the vertical line
`Re(s)=σ`. -/
noncomputable def mellinVerticalMajorant {E : Type*}
    [NormedAddCommGroup E] [NormedSpace ℂ E]
    (f : ℝ → E) (σ : ℝ) : ℝ :=
  ∫ u : ℝ, ‖Real.exp (-σ * u) • f (Real.exp (-u))‖

/-- The equivalent positive-axis norm majorant.  This form is convenient
because `MellinConvergent` gives its integrability directly. -/
noncomputable def mellinNormMajorant {E : Type*}
    [NormedAddCommGroup E] [NormedSpace ℂ E]
    (f : ℝ → E) (σ : ℝ) : ℝ :=
  ∫ t : ℝ in Set.Ioi 0,
    ‖(t : ℂ) ^ ((σ : ℂ) - 1) • f t‖

theorem mellinNormMajorant_nonneg {E : Type*}
    [NormedAddCommGroup E] [NormedSpace ℂ E]
    (f : ℝ → E) (σ : ℝ) : 0 ≤ mellinNormMajorant f σ := by
  unfold mellinNormMajorant
  exact integral_nonneg fun _ ↦ norm_nonneg _

/-- A Mellin transform is uniformly bounded in the imaginary direction by
the `L¹` norm of its logarithmic-coordinate kernel. -/
theorem norm_mellin_le_verticalMajorant {E : Type*}
    [NormedAddCommGroup E] [NormedSpace ℂ E]
    (f : ℝ → E) (s : ℂ) :
    ‖mellin f s‖ ≤ mellinVerticalMajorant f s.re := by
  rw [mellin_eq_fourier]
  rw [Real.fourier_eq]
  refine (norm_integral_le_integral_norm _).trans_eq ?_
  simp only [mellinVerticalMajorant, Circle.norm_smul]

/-- Direct positive-axis version of the same ordinate-independent bound. -/
theorem norm_mellin_le_normMajorant {E : Type*}
    [NormedAddCommGroup E] [NormedSpace ℂ E]
    (f : ℝ → E) (s : ℂ) :
    ‖mellin f s‖ ≤ mellinNormMajorant f s.re := by
  rw [mellin]
  refine (norm_integral_le_integral_norm _).trans_eq ?_
  apply setIntegral_congr_fun measurableSet_Ioi
  intro t ht
  change ‖(t : ℂ) ^ (s - 1) • f t‖ =
    ‖(t : ℂ) ^ ((s.re : ℂ) - 1) • f t‖
  rw [norm_smul, norm_smul,
    Complex.norm_cpow_eq_rpow_re_of_pos ht,
    Complex.norm_cpow_eq_rpow_re_of_pos ht]
  simp

private theorem norm_mellin_integrand_le_endpoints {E : Type*}
    [NormedAddCommGroup E] [NormedSpace ℂ E]
    (f : ℝ → E) {a σ b t : ℝ} (ht : 0 < t)
    (haσ : a ≤ σ) (hσb : σ ≤ b) :
    ‖(t : ℂ) ^ ((σ : ℂ) - 1) • f t‖ ≤
      ‖(t : ℂ) ^ ((a : ℂ) - 1) • f t‖ +
      ‖(t : ℂ) ^ ((b : ℂ) - 1) • f t‖ := by
  simp only [norm_smul, Complex.norm_cpow_eq_rpow_re_of_pos ht,
    sub_re, ofReal_re, one_re]
  by_cases ht1 : t ≤ 1
  · have hpow : t ^ (σ - 1) ≤ t ^ (a - 1) :=
      Real.rpow_le_rpow_of_exponent_ge ht ht1 (by linarith)
    exact (mul_le_mul_of_nonneg_right hpow (norm_nonneg _)).trans
      (le_add_of_nonneg_right (mul_nonneg (Real.rpow_nonneg ht.le _) (norm_nonneg _)))
  · have hpow : t ^ (σ - 1) ≤ t ^ (b - 1) :=
      Real.rpow_le_rpow_of_exponent_le (le_of_not_ge ht1) (by linarith)
    exact (mul_le_mul_of_nonneg_right hpow (norm_nonneg _)).trans
      (le_add_of_nonneg_left (mul_nonneg (Real.rpow_nonneg ht.le _) (norm_nonneg _)))

/-- On a closed real-part strip, the Mellin norm majorant is bounded by the
sum of its two endpoint majorants. -/
theorem mellinNormMajorant_le_endpoints {E : Type*}
    [NormedAddCommGroup E] [NormedSpace ℂ E]
    (f : ℝ → E) {a σ b : ℝ} (haσ : a ≤ σ) (hσb : σ ≤ b)
    (ha : MellinConvergent f (a : ℂ))
    (hσ : MellinConvergent f (σ : ℂ))
    (hb : MellinConvergent f (b : ℂ)) :
    mellinNormMajorant f σ ≤
      mellinNormMajorant f a + mellinNormMajorant f b := by
  rw [MellinConvergent] at ha hσ hb
  have haNorm := ha.norm
  have hσNorm := hσ.norm
  have hbNorm := hb.norm
  unfold mellinNormMajorant
  rw [← integral_add haNorm hbNorm]
  apply integral_mono_ae hσNorm (haNorm.add hbNorm)
  filter_upwards [ae_restrict_mem measurableSet_Ioi] with t ht
  exact norm_mellin_integrand_le_endpoints f ht haσ hσb

/-- The modified theta kernel whose Mellin transform defines
`completedRiemannZeta₀`. -/
noncomputable def completedZetaModifiedKernel : ℝ → ℂ :=
  (HurwitzZeta.hurwitzEvenFEPair 0).f_modif

/-- The modified theta kernel is Mellin-integrable at every complex
parameter; this is the rapid-decay property built into Mathlib's strong
functional-equation pair. -/
theorem mellinConvergent_completedZetaModifiedKernel (s : ℂ) :
    MellinConvergent completedZetaModifiedKernel s := by
  have h := (HurwitzZeta.hurwitzEvenFEPair 0).isStrongFEPair_toStrongFEPair.hasMellin s
  exact h.1

/-- A vertical-line majorant for the entire pole-removed completed zeta. -/
noncomputable def completedRiemannZeta₀VerticalMajorant (σ : ℝ) : ℝ :=
  mellinNormMajorant completedZetaModifiedKernel (σ / 2) / 2

/-- A uniform majorant for `completedRiemannZeta₀` throughout the closed
strip `a ≤ Re(s) ≤ b`. -/
noncomputable def completedRiemannZeta₀StripMajorant (a b : ℝ) : ℝ :=
  (mellinNormMajorant completedZetaModifiedKernel (a / 2) +
    mellinNormMajorant completedZetaModifiedKernel (b / 2)) / 2

theorem completedRiemannZeta₀StripMajorant_nonneg (a b : ℝ) :
    0 ≤ completedRiemannZeta₀StripMajorant a b := by
  unfold completedRiemannZeta₀StripMajorant
  exact div_nonneg (add_nonneg
    (mellinNormMajorant_nonneg _ _)
    (mellinNormMajorant_nonneg _ _)) (by norm_num)

/-- The pole-removed completed zeta is uniformly bounded on each fixed
vertical line, independently of the ordinate. -/
theorem norm_completedRiemannZeta₀_le_verticalMajorant (s : ℂ) :
    ‖completedRiemannZeta₀ s‖ ≤
      completedRiemannZeta₀VerticalMajorant s.re := by
  rw [completedRiemannZeta₀, HurwitzZeta.completedHurwitzZetaEven₀,
    WeakFEPair.Λ₀]
  rw [norm_div]
  have h := norm_mellin_le_normMajorant
    completedZetaModifiedKernel (s / 2)
  have htwo : ‖(2 : ℂ)‖ = 2 := by norm_num
  rw [htwo]
  exact div_le_div_of_nonneg_right (by simpa [completedZetaModifiedKernel] using h)
    (by norm_num)

/-- Uniform boundedness of the pole-removed completed zeta on an arbitrary
closed vertical strip. -/
theorem norm_completedRiemannZeta₀_le_stripMajorant
    {a b : ℝ} (s : ℂ) (has : a ≤ s.re) (hsb : s.re ≤ b) :
    ‖completedRiemannZeta₀ s‖ ≤ completedRiemannZeta₀StripMajorant a b := by
  refine (norm_completedRiemannZeta₀_le_verticalMajorant s).trans ?_
  unfold completedRiemannZeta₀VerticalMajorant completedRiemannZeta₀StripMajorant
  apply div_le_div_of_nonneg_right _ (by norm_num)
  exact mellinNormMajorant_le_endpoints completedZetaModifiedKernel
    (by linarith) (by linarith)
    (mellinConvergent_completedZetaModifiedKernel (a / 2 : ℝ))
    (mellinConvergent_completedZetaModifiedKernel (s.re / 2 : ℝ))
    (mellinConvergent_completedZetaModifiedKernel (b / 2 : ℝ))

/-- An entire xi-type function with exactly the completed zeta poles removed
multiplicatively.  Away from `0` and `1` it equals
`s(s-1) completedRiemannZeta(s)`. -/
noncomputable def riemannXiEntire (s : ℂ) : ℂ :=
  s * (s - 1) * completedRiemannZeta₀ s + 1

theorem differentiable_riemannXiEntire : Differentiable ℂ riemannXiEntire := by
  unfold riemannXiEntire
  exact ((differentiable_id.mul (differentiable_id.sub_const 1)).mul
    differentiable_completedZeta₀).add (differentiable_const 1)

theorem analyticAt_riemannXiEntire (s : ℂ) :
    AnalyticAt ℂ riemannXiEntire s :=
  differentiable_riemannXiEntire.analyticAt s

/-- Away from the two former poles, the entire xi-type function is exactly
`s(s-1)` times the completed zeta function. -/
theorem riemannXiEntire_eq_mul_completedRiemannZeta
    {s : ℂ} (hs0 : s ≠ 0) (hs1 : s ≠ 1) :
    riemannXiEntire s = s * (s - 1) * completedRiemannZeta s := by
  rw [completedRiemannZeta_eq]
  unfold riemannXiEntire
  field_simp [hs0, hs1]
  ring

/-- Every nontrivial zeta zero is a zero of the entire xi-type function. -/
theorem IsNontrivialZetaZero.riemannXiEntire_eq_zero
    {ρ : ℂ} (hρ : IsNontrivialZetaZero ρ) :
    riemannXiEntire ρ = 0 := by
  have hρ0 : ρ ≠ 0 := hρ.ne_zero
  have hρ1 : ρ ≠ 1 := by
    intro h
    subst ρ
    have := hρ.re_lt_one
    norm_num at this
  rw [riemannXiEntire_eq_mul_completedRiemannZeta hρ0 hρ1]
  have hGamma : Gammaℝ ρ ≠ 0 := Gammaℝ_ne_zero_of_re_pos hρ.re_pos
  have hcompleted : completedRiemannZeta ρ = 0 := by
    have hz := riemannZeta_def_of_ne_zero hρ0
    rw [hρ.1] at hz
    exact (div_eq_zero_iff.mp hz.symm).resolve_right hGamma
  simp [hcompleted]

/-- The xi-type function is nonzero in the absolute-convergence half-plane. -/
theorem riemannXiEntire_ne_zero_of_one_lt_re
    {s : ℂ} (hs : 1 < s.re) : riemannXiEntire s ≠ 0 := by
  have hs0 : s ≠ 0 := ne_zero_of_re_pos (zero_lt_one.trans hs)
  have hs1 : s ≠ 1 := by
    intro h
    subst s
    norm_num at hs
  rw [riemannXiEntire_eq_mul_completedRiemannZeta hs0 hs1]
  apply mul_ne_zero (mul_ne_zero hs0 (sub_ne_zero.mpr hs1))
  intro hcompleted
  apply riemannZeta_ne_zero_of_one_lt_re hs
  rw [riemannZeta_def_of_ne_zero hs0, hcompleted, zero_div]

/-- The entire xi-type function has an explicit quadratic norm bound on each
closed vertical strip. -/
theorem norm_riemannXiEntire_le_stripMajorant
    {a b : ℝ} (s : ℂ) (has : a ≤ s.re) (hsb : s.re ≤ b) :
    ‖riemannXiEntire s‖ ≤
      ‖s‖ * ‖s - 1‖ * completedRiemannZeta₀StripMajorant a b + 1 := by
  unfold riemannXiEntire
  calc
    ‖s * (s - 1) * completedRiemannZeta₀ s + 1‖ ≤
        ‖s * (s - 1) * completedRiemannZeta₀ s‖ + ‖(1 : ℂ)‖ := norm_add_le _ _
    _ = ‖s‖ * ‖s - 1‖ * ‖completedRiemannZeta₀ s‖ + 1 := by
      rw [norm_mul, norm_mul, norm_one]
    _ ≤ ‖s‖ * ‖s - 1‖ * completedRiemannZeta₀StripMajorant a b + 1 := by
      gcongr
      exact norm_completedRiemannZeta₀_le_stripMajorant s has hsb

/-- Jensen's zero-counting inequality specialized to the entire xi-type
function.  Later estimates only need to supply the boundary norm and the
nonzero center value. -/
theorem riemannXiEntire_jensen_zero_bound
    {c : ℂ} {r R M : ℝ}
    (hr : 0 < |r|) (hrR : |r| < |R|) (hM : 1 ≤ M)
    (hc : riemannXiEntire c ≠ 0)
    (hbound : ∀ z ∈ Metric.sphere c |R|, ‖riemannXiEntire z‖ ≤ M) :
    ∑ᶠ u, divisor riemannXiEntire (Metric.closedBall c |r|) u ≤
      Real.log (M / ‖riemannXiEntire c‖) / Real.log (R / r) := by
  apply AnalyticOnNhd.sum_divisor_le hr hrR hM
    (fun z _ ↦ analyticAt_riemannXiEntire z) hc hbound

/-- An explicit boundary majorant for a Jensen circle centered at `c`. -/
noncomputable def riemannXiJensenBoundaryMajorant (c : ℂ) (R : ℝ) : ℝ :=
  max 1 ((‖c‖ + |R|) * (‖c - 1‖ + |R|) *
    completedRiemannZeta₀StripMajorant (c.re - |R|) (c.re + |R|) + 1)

theorem one_le_riemannXiJensenBoundaryMajorant (c : ℂ) (R : ℝ) :
    1 ≤ riemannXiJensenBoundaryMajorant c R := by
  exact le_max_left _ _

/-- The explicit Jensen majorant controls xi on the complete boundary
circle. -/
theorem norm_riemannXiEntire_le_jensenBoundaryMajorant
    (c z : ℂ) (R : ℝ) (hz : z ∈ Metric.sphere c |R|) :
    ‖riemannXiEntire z‖ ≤ riemannXiJensenBoundaryMajorant c R := by
  have hdist : ‖z - c‖ = |R| := by
    simpa only [Metric.mem_sphere, dist_eq_norm] using hz
  have hreabs : |z.re - c.re| ≤ |R| := by
    calc
      |z.re - c.re| = |(z - c).re| := by simp
      _ ≤ ‖z - c‖ := Complex.abs_re_le_norm _
      _ = |R| := hdist
  have hza : c.re - |R| ≤ z.re := by
    have := neg_le_of_abs_le hreabs
    linarith
  have hzb : z.re ≤ c.re + |R| := by
    have := le_of_abs_le hreabs
    linarith
  have hnormz : ‖z‖ ≤ ‖c‖ + |R| := by
    calc
      ‖z‖ = ‖(z - c) + c‖ := by ring_nf
      _ ≤ ‖z - c‖ + ‖c‖ := norm_add_le _ _
      _ = ‖c‖ + |R| := by rw [hdist]; ring
  have hnormz1 : ‖z - 1‖ ≤ ‖c - 1‖ + |R| := by
    calc
      ‖z - 1‖ = ‖(z - c) + (c - 1)‖ := by ring_nf
      _ ≤ ‖z - c‖ + ‖c - 1‖ := norm_add_le _ _
      _ = ‖c - 1‖ + |R| := by rw [hdist]; ring
  refine (norm_riemannXiEntire_le_stripMajorant z hza hzb).trans ?_
  apply le_trans _ (le_max_right 1 _)
  gcongr
  exact completedRiemannZeta₀StripMajorant_nonneg _ _

/-- Fully instantiated Jensen inequality for the xi-type function. -/
theorem riemannXiEntire_jensen_zero_bound_explicit
    {c : ℂ} {r R : ℝ}
    (hr : 0 < |r|) (hrR : |r| < |R|)
    (hc : riemannXiEntire c ≠ 0) :
    ∑ᶠ u, divisor riemannXiEntire (Metric.closedBall c |r|) u ≤
      Real.log (riemannXiJensenBoundaryMajorant c R /
        ‖riemannXiEntire c‖) / Real.log (R / r) := by
  exact riemannXiEntire_jensen_zero_bound hr hrR
    (one_le_riemannXiJensenBoundaryMajorant c R) hc
    (norm_riemannXiEntire_le_jensenBoundaryMajorant c · R)

/-- The standard Jensen center on the absolute-convergence line, at
ordinate `T`.  Centering at real part two gives a uniform zero-free center
while a radius-three disk covers the complete critical strip in a
unit-height window. -/
noncomputable def riemannXiJensenCenter (T : ℝ) : ℂ := 2 + T * I

@[simp] theorem riemannXiJensenCenter_re (T : ℝ) :
    (riemannXiJensenCenter T).re = 2 := by
  simp [riemannXiJensenCenter]

@[simp] theorem riemannXiJensenCenter_im (T : ℝ) :
    (riemannXiJensenCenter T).im = T := by
  simp [riemannXiJensenCenter]

theorem riemannXiEntire_ne_zero_jensenCenter (T : ℝ) :
    riemannXiEntire (riemannXiJensenCenter T) ≠ 0 := by
  apply riemannXiEntire_ne_zero_of_one_lt_re
  simp

/-- A completely instantiated local Jensen estimate at height `T`.  This is
already a finite, machine-checked zero-count bound.  Making it asymptotically
useful requires the remaining quantitative comparison between the boundary
majorant and the center value. -/
theorem riemannXiEntire_local_jensen_bound (T : ℝ) :
    ∑ᶠ u, divisor riemannXiEntire
        (Metric.closedBall (riemannXiJensenCenter T) 3) u ≤
      Real.log (riemannXiJensenBoundaryMajorant
        (riemannXiJensenCenter T) 4 /
          ‖riemannXiEntire (riemannXiJensenCenter T)‖) /
        Real.log (4 / 3) := by
  have h := riemannXiEntire_jensen_zero_bound_explicit
      (c := riemannXiJensenCenter T) (r := 3) (R := 4)
      (by norm_num) (by norm_num)
      (riemannXiEntire_ne_zero_jensenCenter T)
  have habs3 : |(3 : ℝ)| = 3 := abs_of_nonneg (by norm_num)
  rw [habs3] at h
  norm_num at h
  exact h

/-- Every nontrivial zero whose ordinate is within one of `T` lies in the
radius-three Jensen disk centered at `2+iT`. -/
theorem IsNontrivialZetaZero.mem_jensenClosedBall
    {ρ : ℂ} (hρ : IsNontrivialZetaZero ρ) {T : ℝ}
    (him : |ρ.im - T| ≤ 1) :
    ρ ∈ Metric.closedBall (riemannXiJensenCenter T) 3 := by
  rw [Metric.mem_closedBall, dist_eq_norm]
  apply (Complex.norm_le_abs_re_add_abs_im _).trans
  have hre : |ρ.re - 2| ≤ 2 := by
    rw [abs_le]
    constructor <;> linarith [hρ.re_pos, hρ.re_lt_one]
  have hre' : |(ρ - riemannXiJensenCenter T).re| ≤ 2 := by
    simpa using hre
  have him' : |(ρ - riemannXiJensenCenter T).im| ≤ 1 := by
    simpa using him
  linarith

end RiemannLab
