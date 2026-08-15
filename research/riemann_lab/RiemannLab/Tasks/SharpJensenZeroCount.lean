import RiemannLab.Tasks.ExtendedXiStrip

namespace RiemannLab

open Complex Set Filter Topology MeromorphicOn

noncomputable def sharpJensenBoundaryMajorant (T : ℝ) : ℝ :=
  max 1 (extendedXiBoundaryBound * (|T| + 10) ^ 6 *
    Real.exp (-(Real.pi * (T - 4) / 4)))

theorem one_le_sharpJensenBoundaryMajorant (T : ℝ) :
    1 ≤ sharpJensenBoundaryMajorant T := le_max_left _ _

/-- The sharp xi estimates now cover the complete Jensen circle, including
the portion between real parts four and six. -/
theorem norm_riemannXiEntire_le_sharpJensenBoundaryMajorant
    {T : ℝ} {z : ℂ}
    (hz : z ∈ Metric.sphere (riemannXiJensenCenter T) 4) :
    ‖riemannXiEntire z‖ ≤ sharpJensenBoundaryMajorant T := by
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
  apply le_trans _ (le_max_right 1 _)
  have hK : 0 ≤ extendedXiBoundaryBound := extendedXiBoundaryBound_pos.le
  have hp : ‖z + 4‖ ^ 6 ≤ (|T| + 10) ^ 6 := by gcongr
  calc
    extendedXiBoundaryBound * ‖z + 4‖ ^ 6 *
        Real.exp (-(Real.pi * z.im / 4)) ≤
        extendedXiBoundaryBound * (|T| + 10) ^ 6 *
          Real.exp (-(Real.pi * z.im / 4)) := by gcongr
    _ ≤ extendedXiBoundaryBound * (|T| + 10) ^ 6 *
        Real.exp (-(Real.pi * (T - 4) / 4)) := by gcongr

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

end RiemannLab
