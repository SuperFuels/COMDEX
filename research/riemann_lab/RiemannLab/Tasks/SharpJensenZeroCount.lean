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

end RiemannLab
