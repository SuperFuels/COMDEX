import RiemannLab.Tasks.ExtendedXiStrip

namespace RiemannLab

open Complex Set Filter Topology MeromorphicOn

noncomputable def rawSharpJensenBoundaryMajorant (T : ℝ) : ℝ :=
  extendedXiBoundaryBound * (|T| + 10) ^ 6 *
    Real.exp (-(Real.pi * (T - 4) / 4))

noncomputable def sharpJensenBoundaryMajorant (T : ℝ) : ℝ :=
  max 1 (rawSharpJensenBoundaryMajorant T)

theorem one_le_sharpJensenBoundaryMajorant (T : ℝ) :
    1 ≤ sharpJensenBoundaryMajorant T := le_max_left _ _

/-- The sharp xi estimates now cover the complete Jensen circle, including
the portion between real parts four and six. -/
theorem norm_riemannXiEntire_le_rawSharpJensenBoundaryMajorant
    {T : ℝ} {z : ℂ}
    (hz : z ∈ Metric.sphere (riemannXiJensenCenter T) 4) :
    ‖riemannXiEntire z‖ ≤ rawSharpJensenBoundaryMajorant T := by
  have hdist : ‖z - riemannXiJensenCenter T‖ = 4 := by
    simpa only [Metric.mem_sphere, dist_eq_norm] using hz
  have hreabs : |z.re - 2| ≤ 4 := by
    calc
      |z.re - 2| = |(z - riemannXiJensenCenter T).re| := by simp
      _ ≤ ‖z - riemannXiJensenCenter T‖ := Complex.abs_re_le_norm _
      _ = 4 := hdist
  have hreLower : -3 ≤ z.re := by
    have := neg_le_of_abs_le hreabs
    linarith
  have hreUpper : z.re ≤ 6 := by
    have := le_of_abs_le hreabs
    linarith
  have himabs : |z.im - T| ≤ 4 := by
    calc
      |z.im - T| = |(z - riemannXiJensenCenter T).im| := by simp
      _ ≤ ‖z - riemannXiJensenCenter T‖ := Complex.abs_im_le_norm _
      _ = 4 := hdist
  have himLower : T - 4 ≤ z.im := by
    have := neg_le_of_abs_le himabs
    linarith
  have hnorm : ‖z + 4‖ ≤ |T| + 10 := by
    calc
      ‖z + 4‖ = ‖(z - riemannXiJensenCenter T) +
          (riemannXiJensenCenter T + 4)‖ := by congr 1 <;> ring
      _ ≤ ‖z - riemannXiJensenCenter T‖ +
          ‖riemannXiJensenCenter T + 4‖ := norm_add_le _ _
      _ ≤ 4 + (6 + |T|) := by
        rw [hdist]
        gcongr
        calc
          ‖riemannXiJensenCenter T + 4‖ ≤
              |(riemannXiJensenCenter T + 4).re| +
                |(riemannXiJensenCenter T + 4).im| :=
            Complex.norm_le_abs_re_add_abs_im _
          _ = 6 + |T| := by norm_num
      _ = |T| + 10 := by ring
  have hexp : Real.exp (-(Real.pi * z.im / 4)) ≤
      Real.exp (-(Real.pi * (T - 4) / 4)) := by
    apply Real.exp_le_exp.mpr
    nlinarith [Real.pi_pos]
  have hbase : ‖riemannXiEntire z‖ ≤
      extendedXiBoundaryBound * ‖z + 4‖ ^ 6 *
        Real.exp (-(Real.pi * z.im / 4)) := by
    by_cases hre : z.re ≤ 4
    · have h := norm_riemannXiEntire_le_sharpStripBound
          (s := z) ⟨hreLower, hre⟩
      have hd : 1 ≤ ‖z + 4‖ := by
        calc
          1 ≤ |(z + 4).re| := by
            rw [abs_of_nonneg (by simp; linarith)]
            simp
            linarith
          _ ≤ ‖z + 4‖ := Complex.abs_re_le_norm _
      have hp : ‖z + 4‖ ^ 4 ≤ ‖z + 4‖ ^ 6 := by
        calc
          ‖z + 4‖ ^ 4 = ‖z + 4‖ ^ 4 * 1 := by ring
          _ ≤ ‖z + 4‖ ^ 4 * ‖z + 4‖ ^ 2 := by
            gcongr
            nlinarith [sq_nonneg ‖z + 4‖]
          _ = ‖z + 4‖ ^ 6 := by ring
      have hp4 : 0 ≤ ‖z + 4‖ ^ 4 := by positivity
      calc
        ‖riemannXiEntire z‖ ≤ weightedXiBoundaryBound * ‖z + 4‖ ^ 4 *
            Real.exp (-(Real.pi * z.im / 4)) := h
        _ ≤ extendedXiBoundaryBound * ‖z + 4‖ ^ 6 *
            Real.exp (-(Real.pi * z.im / 4)) := by
          apply mul_le_mul_of_nonneg_right _ (Real.exp_nonneg _)
          calc
            weightedXiBoundaryBound * ‖z + 4‖ ^ 4 ≤
                extendedXiBoundaryBound * ‖z + 4‖ ^ 4 :=
              mul_le_mul_of_nonneg_right (le_max_left _ _) hp4
            _ ≤ extendedXiBoundaryBound * ‖z + 4‖ ^ 6 :=
              mul_le_mul_of_nonneg_left hp extendedXiBoundaryBound_pos.le
    · exact norm_riemannXiEntire_le_rightExtensionBound
        (s := z) ⟨le_of_not_ge hre, hreUpper⟩
  apply hbase.trans
  have hK : 0 ≤ extendedXiBoundaryBound := extendedXiBoundaryBound_pos.le
  have hp : ‖z + 4‖ ^ 6 ≤ (|T| + 10) ^ 6 := by gcongr
  calc
    extendedXiBoundaryBound * ‖z + 4‖ ^ 6 *
        Real.exp (-(Real.pi * z.im / 4)) ≤
        extendedXiBoundaryBound * (|T| + 10) ^ 6 *
          Real.exp (-(Real.pi * z.im / 4)) := by gcongr
    _ ≤ extendedXiBoundaryBound * (|T| + 10) ^ 6 *
        Real.exp (-(Real.pi * (T - 4) / 4)) := by gcongr

theorem norm_riemannXiEntire_le_sharpJensenBoundaryMajorant
    {T : ℝ} {z : ℂ}
    (hz : z ∈ Metric.sphere (riemannXiJensenCenter T) 4) :
    ‖riemannXiEntire z‖ ≤ sharpJensenBoundaryMajorant T :=
  (norm_riemannXiEntire_le_rawSharpJensenBoundaryMajorant hz).trans
    (le_max_right _ _)

/-- Fully instantiated sharp local Jensen bound. -/
theorem riemannXiEntire_local_jensen_bound_sharp (T : ℝ) :
    ∑ᶠ u, divisor riemannXiEntire
        (Metric.closedBall (riemannXiJensenCenter T) 3) u ≤
      Real.log (sharpJensenBoundaryMajorant T /
        ‖riemannXiEntire (riemannXiJensenCenter T)‖) /
        Real.log (4 / 3) := by
  have h := riemannXiEntire_jensen_zero_bound
    (c := riemannXiJensenCenter T) (r := 3) (R := 4)
    (M := sharpJensenBoundaryMajorant T)
    (by norm_num) (by norm_num) (one_le_sharpJensenBoundaryMajorant T)
    (riemannXiEntire_ne_zero_jensenCenter T)
    (fun z hz ↦ norm_riemannXiEntire_le_sharpJensenBoundaryMajorant
      (by simpa using hz))
  have habs3 : |(3 : ℝ)| = 3 := abs_of_nonneg (by norm_num)
  rw [habs3] at h
  norm_num at h
  exact h

noncomputable def jensenCenterGammaLowerSq (T : ℝ) : ℝ :=
  (Real.pi ^ (-1 : ℝ)) ^ 2 *
    (Real.pi * (T / 2) / (Real.exp (Real.pi * (T / 2)) / 2))

theorem six_div_pi_sq_le_norm_zeta_jensenCenter (T : ℝ) :
    6 / Real.pi ^ 2 ≤ ‖riemannZeta (riemannXiJensenCenter T)‖ := by
  have hA : 0 < Real.pi ^ 2 / 6 := by positivity
  have h := pi_sq_div_six_mul_norm_riemannZeta_ge_one
    (s := riemannXiJensenCenter T) (by simp)
  have hdiv : 1 / (Real.pi ^ 2 / 6) ≤
      ‖riemannZeta (riemannXiJensenCenter T)‖ :=
    (div_le_iff₀ hA).2 (by simpa [mul_comm] using h)
  convert hdiv using 1 <;> field_simp [Real.pi_ne_zero]

/-- Explicit squared lower bound for the moving Jensen centre. -/
theorem jensenCenter_sq_lower {T : ℝ} (hT : 2 ≤ T) :
    jensenCenterGammaLowerSq T * (6 / Real.pi ^ 2) ^ 2 ≤
      ‖riemannXiEntire (riemannXiJensenCenter T)‖ ^ 2 := by
  let s := riemannXiJensenCenter T
  let t := T / 2
  have ht : 0 < t := by dsimp [t]; linarith
  have hsSq : ‖s‖ ^ 2 = 4 + T ^ 2 := by
    rw [Complex.sq_norm]
    simp [s, riemannXiJensenCenter, Complex.normSq_apply]
    ring
  have hs1Sq : ‖s - 1‖ ^ 2 = 1 + T ^ 2 := by
    rw [Complex.sq_norm]
    simp [s, riemannXiJensenCenter, Complex.normSq_apply]
    ring
  have hsOne : 1 ≤ ‖s‖ ^ 2 := by rw [hsSq]; nlinarith [sq_nonneg T]
  have hs1One : 1 ≤ ‖s - 1‖ ^ 2 := by rw [hs1Sq]; nlinarith [sq_nonneg T]
  have hgamma := GammaR_jensenCenter_sq_lower ht
  have hcenter : s = 2 + ((2 * t : ℝ) : ℂ) * I := by
    apply Complex.ext <;> simp [s, t, riemannXiJensenCenter] <;> ring
  rw [← hcenter] at hgamma
  change jensenCenterGammaLowerSq T ≤ ‖Gammaℝ s‖ ^ 2 at hgamma
  have hzeta := six_div_pi_sq_le_norm_zeta_jensenCenter T
  change 6 / Real.pi ^ 2 ≤ ‖riemannZeta s‖ at hzeta
  rw [norm_riemannXiEntire_jensenCenter T]
  change _ ≤ (‖s‖ * ‖s - 1‖ * ‖Gammaℝ s‖ * ‖riemannZeta s‖) ^ 2
  simp only [mul_pow]
  have hG : 0 ≤ jensenCenterGammaLowerSq T := by
    unfold jensenCenterGammaLowerSq
    positivity
  have hz0 : 0 ≤ 6 / Real.pi ^ 2 := by positivity
  calc
    jensenCenterGammaLowerSq T * (6 / Real.pi ^ 2) ^ 2 =
        1 * 1 * jensenCenterGammaLowerSq T * (6 / Real.pi ^ 2) ^ 2 := by ring
    _ ≤ ‖s‖ ^ 2 * ‖s - 1‖ ^ 2 * ‖Gammaℝ s‖ ^ 2 *
        ‖riemannZeta s‖ ^ 2 := by
      gcongr

/-- Xi normalized to have value one at the moving Jensen centre. -/
noncomputable def centerScaledXi (T : ℝ) (z : ℂ) : ℂ :=
  (riemannXiEntire (riemannXiJensenCenter T))⁻¹ * riemannXiEntire z

@[simp] theorem centerScaledXi_center (T : ℝ) :
    centerScaledXi T (riemannXiJensenCenter T) = 1 := by
  unfold centerScaledXi
  exact inv_mul_cancel₀ (riemannXiEntire_ne_zero_jensenCenter T)

theorem analyticAt_centerScaledXi (T : ℝ) (z : ℂ) :
    AnalyticAt ℂ (centerScaledXi T) z := by
  unfold centerScaledXi
  exact analyticAt_const.mul (analyticAt_riemannXiEntire z)

/-- Multiplying xi by its nonzero inverse centre value does not alter its
divisor on the Jensen disk. -/
theorem divisor_centerScaledXi_eq (T r : ℝ) (hr : 0 ≤ r) :
    divisor (centerScaledXi T) (Metric.closedBall (riemannXiJensenCenter T) r) =
      divisor riemannXiEntire (Metric.closedBall (riemannXiJensenCenter T) r) := by
  let U := Metric.closedBall (riemannXiJensenCenter T) r
  let c : ℂ := (riemannXiEntire (riemannXiJensenCenter T))⁻¹
  have hc : c ≠ 0 := inv_ne_zero (riemannXiEntire_ne_zero_jensenCenter T)
  have hconst : MeromorphicOn (fun _ : ℂ ↦ c) U := MeromorphicOn.const c
  have hxi : MeromorphicOn riemannXiEntire U :=
    fun z _ ↦ (analyticAt_riemannXiEntire z).meromorphicAt
  have hconstOrder : ∀ z ∈ U,
      meromorphicOrderAt (fun _ : ℂ ↦ c) z ≠ ⊤ := by
    intro z hz
    simp [meromorphicOrderAt_const, hc]
  have hcenterMem : riemannXiJensenCenter T ∈ U := by
    simp [U, hr]
  have hcenterOrder : meromorphicOrderAt riemannXiEntire
      (riemannXiJensenCenter T) ≠ ⊤ := by
    rw [(analyticAt_riemannXiEntire _).meromorphicOrderAt_eq,
      (analyticAt_riemannXiEntire _).analyticOrderAt_eq_zero.2
        (riemannXiEntire_ne_zero_jensenCenter T)]
    simp
  have hxiOrder : ∀ z ∈ U, meromorphicOrderAt riemannXiEntire z ≠ ⊤ := by
    intro z hz
    exact hxi.meromorphicOrderAt_ne_top_of_isPreconnected
      Metric.isPreconnected_closedBall hcenterMem hz hcenterOrder
  have hmul := divisor_mul hconst hxi hconstOrder hxiOrder
  have hfun : centerScaledXi T = (fun _ : ℂ ↦ c) * riemannXiEntire := by
    funext z
    rfl
  rw [hfun, hmul]
  simpa [U]

theorem norm_jensenCenter_le_rawMajorant {T : ℝ} (hT : 2 ≤ T) :
    ‖riemannXiEntire (riemannXiJensenCenter T)‖ ≤
      rawSharpJensenBoundaryMajorant T := by
  let s := riemannXiJensenCenter T
  have hs : s ∈ xiVerticalClosedStrip := by
    change -3 ≤ s.re ∧ s.re ≤ 4
    norm_num [s]
  have h := norm_riemannXiEntire_le_sharpStripBound hs
  have hnorm : ‖s + 4‖ ≤ T + 10 := by
    calc
      ‖s + 4‖ ≤ |(s + 4).re| + |(s + 4).im| :=
        Complex.norm_le_abs_re_add_abs_im _
      _ = 6 + T := by norm_num [s, abs_of_nonneg (by linarith : 0 ≤ T)]
      _ ≤ T + 10 := by linarith
  have hbase : 1 ≤ T + 10 := by linarith
  have hp : ‖s + 4‖ ^ 4 ≤ (T + 10) ^ 6 := by
    calc
      ‖s + 4‖ ^ 4 ≤ (T + 10) ^ 4 := by gcongr
      _ ≤ (T + 10) ^ 6 := by
        nlinarith [sq_nonneg ((T + 10) ^ 2),
          sq_nonneg ((T + 10) ^ 2 - 1)]
  have hexp : Real.exp (-(Real.pi * s.im / 4)) ≤
      Real.exp (-(Real.pi * (T - 4) / 4)) := by
    apply Real.exp_le_exp.mpr
    simp [s]
    nlinarith [Real.pi_pos]
  have hp4 : 0 ≤ ‖s + 4‖ ^ 4 := by positivity
  have hp6 : 0 ≤ (T + 10) ^ 6 := by positivity
  calc
    ‖riemannXiEntire s‖ ≤ weightedXiBoundaryBound * ‖s + 4‖ ^ 4 *
        Real.exp (-(Real.pi * s.im / 4)) := h
    _ ≤ extendedXiBoundaryBound * (T + 10) ^ 6 *
        Real.exp (-(Real.pi * (T - 4) / 4)) := by
      apply mul_le_mul
      · exact mul_le_mul (le_max_left _ _) hp hp4
          extendedXiBoundaryBound_pos.le
      · exact hexp
      · exact Real.exp_nonneg _
      · exact mul_nonneg extendedXiBoundaryBound_pos.le hp6
    _ = rawSharpJensenBoundaryMajorant T := by
      unfold rawSharpJensenBoundaryMajorant
      rw [abs_of_nonneg (by linarith : 0 ≤ T)]

noncomputable def scaledJensenBoundaryMajorant (T : ℝ) : ℝ :=
  rawSharpJensenBoundaryMajorant T /
    ‖riemannXiEntire (riemannXiJensenCenter T)‖

theorem one_le_scaledJensenBoundaryMajorant {T : ℝ} (hT : 2 ≤ T) :
    1 ≤ scaledJensenBoundaryMajorant T := by
  unfold scaledJensenBoundaryMajorant
  exact (le_div_iff₀ (norm_pos_iff.mpr
    (riemannXiEntire_ne_zero_jensenCenter T))).2
      (by simpa using norm_jensenCenter_le_rawMajorant hT)

theorem norm_centerScaledXi_le_scaledMajorant
    {T : ℝ} {z : ℂ}
    (hz : z ∈ Metric.sphere (riemannXiJensenCenter T) 4) :
    ‖centerScaledXi T z‖ ≤ scaledJensenBoundaryMajorant T := by
  unfold centerScaledXi scaledJensenBoundaryMajorant
  rw [norm_mul, norm_inv]
  have hc : 0 < ‖riemannXiEntire (riemannXiJensenCenter T)‖ :=
    norm_pos_iff.mpr (riemannXiEntire_ne_zero_jensenCenter T)
  rw [inv_mul_eq_div]
  apply (div_le_div_iff_of_pos_right hc).2
  exact norm_riemannXiEntire_le_rawSharpJensenBoundaryMajorant hz

/-- Jensen's inequality in the correct centre-scaled form.  Its centre norm
is exactly one and its divisor is the original xi divisor. -/
theorem riemannXiEntire_local_jensen_bound_scaled
    {T : ℝ} (hT : 2 ≤ T) :
    ∑ᶠ u, divisor riemannXiEntire
        (Metric.closedBall (riemannXiJensenCenter T) 3) u ≤
      Real.log (scaledJensenBoundaryMajorant T) / Real.log (4 / 3) := by
  have hana : AnalyticOnNhd ℂ (centerScaledXi T)
      (Metric.closedBall (riemannXiJensenCenter T) 4) :=
    fun z _ ↦ analyticAt_centerScaledXi T z
  have h := AnalyticOnNhd.sum_divisor_le
    (f := centerScaledXi T) (c := riemannXiJensenCenter T)
    (r := 3) (R := 4) (M := scaledJensenBoundaryMajorant T)
    (by norm_num) (by norm_num) (one_le_scaledJensenBoundaryMajorant hT)
    (by simpa using hana) (by simp) (fun z hz ↦ norm_centerScaledXi_le_scaledMajorant
      (by simpa using hz))
  have habs3 : |(3 : ℝ)| = 3 := abs_of_nonneg (by norm_num)
  rw [habs3, divisor_centerScaledXi_eq T 3 (by norm_num)] at h
  norm_num at h
  simpa using h

/-- The Gamma lower factor at the moving centre, rewritten so that its
exponential cancellation against the boundary majorant is explicit. -/
theorem jensenCenterGammaLowerSq_eq (T : ℝ) :
    jensenCenterGammaLowerSq T =
      (Real.pi⁻¹) ^ 2 * (Real.pi * T) *
        Real.exp (-(Real.pi * T / 2)) := by
  unfold jensenCenterGammaLowerSq
  rw [Real.rpow_neg_one, Real.exp_neg]
  field_simp [Real.exp_ne_zero]
  <;> ring

theorem rawSharpJensenBoundaryMajorant_sq {T : ℝ} (hT : 0 ≤ T) :
    rawSharpJensenBoundaryMajorant T ^ 2 =
      extendedXiBoundaryBound ^ 2 * (T + 10) ^ 12 *
        Real.exp (-(Real.pi * (T - 4) / 2)) := by
  unfold rawSharpJensenBoundaryMajorant
  rw [abs_of_nonneg hT]
  simp only [mul_pow]
  rw [← Real.exp_nat_mul]
  congr 1 <;> ring

noncomputable def jensenCenterSqCoefficient : ℝ :=
  (Real.pi⁻¹) ^ 2 * Real.pi * (6 / Real.pi ^ 2) ^ 2

theorem jensenCenterSqCoefficient_pos : 0 < jensenCenterSqCoefficient := by
  unfold jensenCenterSqCoefficient
  positivity

theorem jensenCenter_sq_lower_explicit {T : ℝ} (hT : 2 ≤ T) :
    jensenCenterSqCoefficient * T * Real.exp (-(Real.pi * T / 2)) ≤
      ‖riemannXiEntire (riemannXiJensenCenter T)‖ ^ 2 := by
  have h := jensenCenter_sq_lower hT
  rw [jensenCenterGammaLowerSq_eq] at h
  convert h using 1 <;> unfold jensenCenterSqCoefficient <;> ring

noncomputable def jensenQuotientSqConstant : ℝ :=
  extendedXiBoundaryBound ^ 2 * Real.exp (2 * Real.pi) /
    jensenCenterSqCoefficient

theorem jensenQuotientSqConstant_pos : 0 < jensenQuotientSqConstant := by
  unfold jensenQuotientSqConstant
  exact div_pos
    (mul_pos (sq_pos_of_pos extendedXiBoundaryBound_pos) (Real.exp_pos _))
    jensenCenterSqCoefficient_pos

theorem scaledJensenBoundaryMajorant_sq_le {T : ℝ} (hT : 2 ≤ T) :
    scaledJensenBoundaryMajorant T ^ 2 ≤
      jensenQuotientSqConstant * (T + 10) ^ 12 / T := by
  have hT0 : 0 < T := by linarith
  have hnorm : 0 < ‖riemannXiEntire (riemannXiJensenCenter T)‖ ^ 2 := by
    exact sq_pos_of_pos (norm_pos_iff.mpr
      (riemannXiEntire_ne_zero_jensenCenter T))
  have hlower := jensenCenter_sq_lower_explicit hT
  have hfactor :
      0 ≤ jensenQuotientSqConstant * (T + 10) ^ 12 / T := by
    exact div_nonneg
      (mul_nonneg jensenQuotientSqConstant_pos.le (by positivity)) hT0.le
  unfold scaledJensenBoundaryMajorant
  rw [div_pow]
  apply (div_le_iff₀ hnorm).2
  calc
    rawSharpJensenBoundaryMajorant T ^ 2 =
        extendedXiBoundaryBound ^ 2 * (T + 10) ^ 12 *
          Real.exp (-(Real.pi * (T - 4) / 2)) :=
      rawSharpJensenBoundaryMajorant_sq hT0.le
    _ = (jensenQuotientSqConstant * (T + 10) ^ 12 / T) *
        (jensenCenterSqCoefficient * T *
          Real.exp (-(Real.pi * T / 2))) := by
      unfold jensenQuotientSqConstant
      field_simp [jensenCenterSqCoefficient_pos.ne', hT0.ne']
      rw [mul_assoc]
      congr 1
      rw [← Real.exp_add]
      congr 1 <;> ring
    _ ≤ (jensenQuotientSqConstant * (T + 10) ^ 12 / T) *
        ‖riemannXiEntire (riemannXiJensenCenter T)‖ ^ 2 :=
      mul_le_mul_of_nonneg_left hlower hfactor

noncomputable def jensenQuotientPolynomialConstant : ℝ :=
  jensenQuotientSqConstant * (6 : ℝ) ^ 12

theorem jensenQuotientPolynomialConstant_pos :
    0 < jensenQuotientPolynomialConstant := by
  unfold jensenQuotientPolynomialConstant
  exact mul_pos jensenQuotientSqConstant_pos (pow_pos (by norm_num) 12)

/-- After centre scaling, the exponential factors cancel completely: the
Jensen boundary quotient has a uniform polynomial majorant.  Degree twelve
is deliberately coarse; its logarithm is still `O(log T)`. -/
theorem scaledJensenBoundaryMajorant_le_polynomial
    {T : ℝ} (hT : 2 ≤ T) :
    scaledJensenBoundaryMajorant T ≤
      jensenQuotientPolynomialConstant * T ^ 12 := by
  have hT0 : 0 < T := by linarith
  have hscaledOne := one_le_scaledJensenBoundaryMajorant hT
  have hselfsq : scaledJensenBoundaryMajorant T ≤
      scaledJensenBoundaryMajorant T ^ 2 := by nlinarith
  have hsq := scaledJensenBoundaryMajorant_sq_le hT
  have hbase : T + 10 ≤ 6 * T := by linarith
  have hp : (T + 10) ^ 12 ≤ (6 * T) ^ 12 := by gcongr
  calc
    scaledJensenBoundaryMajorant T ≤
        scaledJensenBoundaryMajorant T ^ 2 := hselfsq
    _ ≤ jensenQuotientSqConstant * (T + 10) ^ 12 / T := hsq
    _ ≤ jensenQuotientSqConstant * (6 * T) ^ 12 / T := by
      exact div_le_div_of_nonneg_right
        (mul_le_mul_of_nonneg_left hp jensenQuotientSqConstant_pos.le) hT0.le
    _ = jensenQuotientSqConstant * 6 ^ 12 * T ^ 11 := by
      field_simp [hT0.ne']
    _ ≤ jensenQuotientSqConstant * 6 ^ 12 * T ^ 12 := by
      have hpow : T ^ 11 ≤ T ^ 12 := by
        nlinarith [mul_nonneg (pow_nonneg hT0.le 11) (sub_nonneg.mpr (by linarith : 1 ≤ T))]
      exact mul_le_mul_of_nonneg_left hpow
        (mul_nonneg jensenQuotientSqConstant_pos.le (pow_nonneg (by norm_num) 12))
    _ = jensenQuotientPolynomialConstant * T ^ 12 := by
      rfl

theorem log_scaledJensenBoundaryMajorant_le {T : ℝ} (hT : 2 ≤ T) :
    Real.log (scaledJensenBoundaryMajorant T) ≤
      Real.log jensenQuotientPolynomialConstant + 12 * Real.log T := by
  have hspos : 0 < scaledJensenBoundaryMajorant T :=
    lt_of_lt_of_le zero_lt_one (one_le_scaledJensenBoundaryMajorant hT)
  have hTpos : 0 < T := by linarith
  have hrhspos : 0 < jensenQuotientPolynomialConstant * T ^ 12 :=
    mul_pos jensenQuotientPolynomialConstant_pos (pow_pos hTpos 12)
  have hlog := (Real.log_le_log_iff hspos hrhspos).2
    (scaledJensenBoundaryMajorant_le_polynomial hT)
  rw [Real.log_mul jensenQuotientPolynomialConstant_pos.ne'
      (pow_ne_zero 12 hTpos.ne'), Real.log_pow] at hlog
  norm_num at hlog ⊢
  exact hlog

/-- Explicit local zero-counting increment.  This is the checked
`O(log T)` Jensen estimate, with constants left visible. -/
theorem riemannXiEntire_local_zero_count_le_log
    {T : ℝ} (hT : 2 ≤ T) :
    ∑ᶠ u, divisor riemannXiEntire
        (Metric.closedBall (riemannXiJensenCenter T) 3) u ≤
      (Real.log jensenQuotientPolynomialConstant + 12 * Real.log T) /
        Real.log (4 / 3) := by
  have hj := riemannXiEntire_local_jensen_bound_scaled hT
  have hden : 0 < Real.log (4 / 3) := Real.log_pos (by norm_num)
  exact hj.trans (div_le_div_of_nonneg_right
    (log_scaledJensenBoundaryMajorant_le hT) hden.le)

/-- The radius-seven-halves form needed to cover the complete contour segment
from `re = -1` to the Perron line while retaining the radius-four Jensen
boundary.  In particular, `sqrt (3^2 + 1^2) < 7/2`, removing the radius-three
corner gap in the first admissible-height construction. -/
theorem riemannXiEntire_local_jensen_bound_scaled_seven_halves
    {T : ℝ} (hT : 2 ≤ T) :
    ∑ᶠ u, divisor riemannXiEntire
        (Metric.closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ)) u ≤
      Real.log (scaledJensenBoundaryMajorant T) / Real.log (8 / 7) := by
  have hana : AnalyticOnNhd ℂ (centerScaledXi T)
      (Metric.closedBall (riemannXiJensenCenter T) 4) :=
    fun z _ ↦ analyticAt_centerScaledXi T z
  have h := AnalyticOnNhd.sum_divisor_le
    (f := centerScaledXi T) (c := riemannXiJensenCenter T)
    (r := (7 / 2 : ℝ)) (R := 4) (M := scaledJensenBoundaryMajorant T)
    (by norm_num) (by norm_num) (one_le_scaledJensenBoundaryMajorant hT)
    (by simpa using hana) (by simp) (fun z hz ↦ norm_centerScaledXi_le_scaledMajorant
      (by simpa using hz))
  have habs : |(7 / 2 : ℝ)| = 7 / 2 := abs_of_nonneg (by norm_num)
  rw [habs, divisor_centerScaledXi_eq T (7 / 2 : ℝ) (by norm_num)] at h
  norm_num at h
  simpa [show (4 : ℝ) / (7 / 2) = 8 / 7 by norm_num] using h

/-- Explicit `O(log T)` local zero count on the enlarged inner disk. -/
theorem riemannXiEntire_local_zero_count_seven_halves_le_log
    {T : ℝ} (hT : 2 ≤ T) :
    ∑ᶠ u, divisor riemannXiEntire
        (Metric.closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ)) u ≤
      (Real.log jensenQuotientPolynomialConstant + 12 * Real.log T) /
        Real.log (8 / 7) := by
  have hj := riemannXiEntire_local_jensen_bound_scaled_seven_halves hT
  have hden : 0 < Real.log (8 / 7) := Real.log_pos (by norm_num)
  exact hj.trans (div_le_div_of_nonneg_right
    (log_scaledJensenBoundaryMajorant_le hT) hden.le)

end RiemannLab
