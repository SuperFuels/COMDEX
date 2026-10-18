import RiemannLab.Tasks.QuantitativeJensen

namespace RiemannLab

open Complex Set Filter Topology

/-! Boundary data for extending the sharp xi estimate far enough to contain
the complete radius-four Jensen circle centred at `2+iT`. -/

noncomputable def extendedWeightedXi (s : ℂ) : ℂ :=
  Complex.exp ((-I * (Real.pi : ℂ) / 4) * s) *
    (riemannXiEntire s / (s + 4) ^ 6)

def xiRightExtensionClosedStrip : Set ℂ :=
  Complex.re ⁻¹' Set.Icc (4 : ℝ) 6

def xiRightExtensionStrip : Set ℂ :=
  Complex.HadamardThreeLines.verticalStrip (4 : ℝ) 6

theorem closure_xiRightExtensionStrip_subset :
    closure xiRightExtensionStrip ⊆ xiRightExtensionClosedStrip := by
  apply closure_minimal
  · intro s hs
    exact ⟨hs.1.le, hs.2.le⟩
  · exact isClosed_Icc.preimage continuous_re

theorem add_four_ne_zero_of_mem_xiRightExtensionClosedStrip
    {s : ℂ} (hs : s ∈ xiRightExtensionClosedStrip) : s + 4 ≠ 0 := by
  intro h
  have hre := congrArg Complex.re h
  have := hs.1
  simp at hre
  linarith

noncomputable def extendedNormalizedXi (s : ℂ) : ℂ :=
  riemannXiEntire s / (s + 4) ^ 6

noncomputable def extendedXiStripBound : ℝ :=
  30 * completedRiemannZeta₀StripMajorant 4 6 + 1

theorem extendedXiStripBound_nonneg : 0 ≤ extendedXiStripBound := by
  unfold extendedXiStripBound
  have := completedRiemannZeta₀StripMajorant_nonneg 4 6
  linarith

theorem norm_extendedNormalizedXi_le_of_mem
    {s : ℂ} (hs : s ∈ xiRightExtensionClosedStrip) :
    ‖extendedNormalizedXi s‖ ≤ extendedXiStripBound := by
  let r := ‖s + 4‖
  let C := completedRiemannZeta₀StripMajorant 4 6
  have hC : 0 ≤ C := completedRiemannZeta₀StripMajorant_nonneg _ _
  have hre : 1 ≤ (s + 4).re := by
    change 4 ≤ s.re ∧ s.re ≤ 6 at hs
    norm_num
    linarith [hs.1]
  have hr : 1 ≤ r := by
    calc
      1 ≤ |(s + 4).re| := by rw [abs_of_nonneg (by linarith)] at *; exact hre
      _ ≤ ‖s + 4‖ := Complex.abs_re_le_norm _
  have hsNorm : ‖s‖ ≤ 5 * r := by
    calc
      ‖s‖ = ‖(s + 4) - 4‖ := by congr 1 <;> ring
      _ ≤ ‖s + 4‖ + ‖(4 : ℂ)‖ := norm_sub_le _ _
      _ = r + 4 := by simp [r]
      _ ≤ 5 * r := by linarith
  have hs1Norm : ‖s - 1‖ ≤ 6 * r := by
    calc
      ‖s - 1‖ = ‖(s + 4) - 5‖ := by congr 1 <;> ring
      _ ≤ ‖s + 4‖ + ‖(5 : ℂ)‖ := norm_sub_le _ _
      _ = r + 5 := by simp [r]
      _ ≤ 6 * r := by linarith
  have hxi : ‖riemannXiEntire s‖ ≤ (30 * C + 1) * r ^ 2 := by
    calc
      ‖riemannXiEntire s‖ ≤ ‖s‖ * ‖s - 1‖ * C + 1 :=
        norm_riemannXiEntire_le_stripMajorant s hs.1 hs.2
      _ ≤ (5 * r) * (6 * r) * C + 1 := by gcongr
      _ ≤ (30 * C + 1) * r ^ 2 := by
        nlinarith [sq_nonneg r]
  have hr0 : 0 < r := zero_lt_one.trans_le hr
  unfold extendedNormalizedXi extendedXiStripBound
  rw [norm_div, norm_pow]
  apply (div_le_iff₀ (pow_pos hr0 6)).2
  calc
    ‖riemannXiEntire s‖ ≤ (30 * C + 1) * r ^ 2 := hxi
    _ ≤ (30 * C + 1) * r ^ 6 := by
      have hK : 0 ≤ 30 * C + 1 := by positivity
      gcongr
      nlinarith [sq_nonneg r, sq_nonneg (r ^ 2 - 1)]
    _ = (30 * completedRiemannZeta₀StripMajorant 4 6 + 1) *
        ‖s + 4‖ ^ 6 := by rfl

theorem differentiableOn_extendedWeightedXi_closure :
    DifferentiableOn ℂ extendedWeightedXi (closure xiRightExtensionStrip) := by
  intro s hs
  apply DifferentiableAt.differentiableWithinAt
  unfold extendedWeightedXi
  have hden : s + 4 ≠ 0 :=
    add_four_ne_zero_of_mem_xiRightExtensionClosedStrip
      (closure_xiRightExtensionStrip_subset hs)
  exact (Complex.differentiable_exp.differentiableAt.comp s
    (((differentiable_const (-I * (Real.pi : ℂ) / 4)).mul
      differentiable_id).differentiableAt)).mul
    (differentiable_riemannXiEntire.differentiableAt.div
      ((differentiable_id.add_const 4).pow 6).differentiableAt
      (pow_ne_zero 6 hden))

theorem diffContOnCl_extendedWeightedXi :
    DiffContOnCl ℂ extendedWeightedXi xiRightExtensionStrip :=
  differentiableOn_extendedWeightedXi_closure.diffContOnCl

theorem norm_extendedWeightedXi_six_sq {t : ℝ} (ht : 0 < t) :
    ‖extendedWeightedXi (6 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2 =
      Real.exp (Real.pi * t) *
        ((36 + 4 * t ^ 2) * (25 + 4 * t ^ 2) *
          ((Real.pi ^ (-3 : ℝ)) ^ 2 *
            ((4 + t ^ 2) * (1 + t ^ 2) *
              (Real.pi * t / Real.sinh (Real.pi * t)))) *
          ‖riemannZeta (6 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2) /
        (100 + 4 * t ^ 2) ^ 6 := by
  let s : ℂ := 6 + ((2 * t : ℝ) : ℂ) * I
  have hsre : s.re = 6 := by simp [s]
  have hsim : s.im = 2 * t := by simp [s]
  have hs0 : s ≠ 0 := ne_zero_of_re_pos (by rw [hsre]; norm_num)
  have hs1 : s ≠ 1 := by
    intro h
    have := congrArg Complex.re h
    rw [hsre] at this
    norm_num at this
  have hexp : Real.exp (Real.pi * (2 * t) / 4) ^ 2 =
      Real.exp (Real.pi * t) := by
    rw [← Real.exp_nat_mul]
    congr 1
    norm_num
    ring
  have hnorms : ‖s‖ ^ 2 = 36 + 4 * t ^ 2 := by
    rw [Complex.sq_norm]
    simp [s, Complex.normSq_apply]
    ring
  have hnorms1 : ‖s - 1‖ ^ 2 = 25 + 4 * t ^ 2 := by
    rw [Complex.sq_norm]
    simp [s, Complex.normSq_apply]
    ring
  have hnorms4 : ‖s + 4‖ ^ 2 = 100 + 4 * t ^ 2 := by
    rw [Complex.sq_norm]
    simp [s, Complex.normSq_apply]
    ring
  have hden : (‖s + 4‖ ^ 6) ^ 2 = (100 + 4 * t ^ 2) ^ 6 := by
    calc
      (‖s + 4‖ ^ 6) ^ 2 = (‖s + 4‖ ^ 2) ^ 6 := by ring
      _ = (100 + 4 * t ^ 2) ^ 6 := by rw [hnorms4]
  have hgamma := norm_GammaR_six_add_two_mul_I_sq ht
  change ‖Gammaℝ s‖ ^ 2 = _ at hgamma
  unfold extendedWeightedXi
  rw [norm_mul, norm_div, norm_pow, mul_pow, div_pow, norm_upperWeight]
  rw [riemannXiEntire_eq_mul_GammaR_riemannZeta hs0 hs1
    (by rw [hsre]; norm_num)]
  simp only [norm_mul, mul_pow]
  rw [hsim, hexp, hnorms, hnorms1, hden, hgamma]
  ring

/-- Height-independent squared-norm bound on the positive high part of the
actual Jensen right boundary. -/
theorem norm_extendedWeightedXi_six_sq_le {t : ℝ} (ht : 1 ≤ t) :
    ‖extendedWeightedXi (6 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2 ≤
      46400 * (Real.pi ^ (-3 : ℝ)) ^ 2 * Real.pi *
        riemannZetaFourMajorant ^ 2 := by
  rw [norm_extendedWeightedXi_six_sq (zero_lt_one.trans_le ht)]
  have hsinh : Real.exp (Real.pi * t) / 4 ≤
      Real.sinh (Real.pi * t) := by
    apply exp_div_four_le_sinh
    nlinarith [Real.two_le_pi]
  have hsinhpos : 0 < Real.sinh (Real.pi * t) := by positivity
  have hcancel : Real.exp (Real.pi * t) *
      (Real.pi * t / Real.sinh (Real.pi * t)) ≤ 4 * Real.pi * t := by
    have hratio : Real.exp (Real.pi * t) /
        Real.sinh (Real.pi * t) ≤ 4 := by
      apply (div_le_iff₀ hsinhpos).2
      linarith
    calc
      Real.exp (Real.pi * t) *
          (Real.pi * t / Real.sinh (Real.pi * t)) =
          (Real.pi * t) *
            (Real.exp (Real.pi * t) / Real.sinh (Real.pi * t)) := by ring
      _ ≤ (Real.pi * t) * 4 := by gcongr
      _ = 4 * Real.pi * t := by ring
  have hzeta := norm_riemannZeta_le_fourMajorant
    (s := 6 + ((2 * t : ℝ) : ℂ) * I) (by norm_num)
  have hzetaSq : ‖riemannZeta
      (6 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2 ≤
      riemannZetaFourMajorant ^ 2 := by
    nlinarith [norm_nonneg (riemannZeta
      (6 + ((2 * t : ℝ) : ℂ) * I)), riemannZetaFourMajorant_nonneg]
  have h36 : 36 + 4 * t ^ 2 ≤ 40 * t ^ 2 := by nlinarith [sq_nonneg t]
  have h25 : 25 + 4 * t ^ 2 ≤ 29 * t ^ 2 := by nlinarith [sq_nonneg t]
  have h4 : 4 + t ^ 2 ≤ 5 * t ^ 2 := by nlinarith [sq_nonneg t]
  have h1 : 1 + t ^ 2 ≤ 2 * t ^ 2 := by nlinarith [sq_nonneg t]
  have hdenpos : 0 < (100 + 4 * t ^ 2) ^ 6 := by positivity
  have hden : t ^ 12 ≤ (100 + 4 * t ^ 2) ^ 6 := by
    have ht2 : t ^ 2 ≤ 100 + 4 * t ^ 2 := by nlinarith [sq_nonneg t]
    calc
      t ^ 12 = (t ^ 2) ^ 6 := by ring
      _ ≤ (100 + 4 * t ^ 2) ^ 6 := by gcongr
  have ht9 : t ^ 9 ≤ t ^ 12 := by
    have ht0 : 0 ≤ t := le_trans zero_le_one ht
    have ht3 : 1 ≤ t ^ 3 := by
      nlinarith [sq_nonneg t, mul_nonneg (sq_nonneg t) ht0]
    calc
      t ^ 9 = t ^ 9 * 1 := by ring
      _ ≤ t ^ 9 * t ^ 3 := by
        exact mul_le_mul_of_nonneg_left ht3 (by positivity)
      _ = t ^ 12 := by ring
  apply (div_le_iff₀ hdenpos).2
  calc
    Real.exp (Real.pi * t) *
        ((36 + 4 * t ^ 2) * (25 + 4 * t ^ 2) *
          ((Real.pi ^ (-3 : ℝ)) ^ 2 *
            ((4 + t ^ 2) * (1 + t ^ 2) *
              (Real.pi * t / Real.sinh (Real.pi * t)))) *
          ‖riemannZeta (6 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2) ≤
      (40 * t ^ 2) * (29 * t ^ 2) *
        (Real.pi ^ (-3 : ℝ)) ^ 2 * (5 * t ^ 2) * (2 * t ^ 2) *
        (4 * Real.pi * t) * riemannZetaFourMajorant ^ 2 := by
      calc
        _ = (36 + 4 * t ^ 2) * (25 + 4 * t ^ 2) *
            (Real.pi ^ (-3 : ℝ)) ^ 2 * (4 + t ^ 2) * (1 + t ^ 2) *
            (Real.exp (Real.pi * t) *
              (Real.pi * t / Real.sinh (Real.pi * t))) *
            ‖riemannZeta (6 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2 := by ring
        _ ≤ _ := by gcongr
    _ = 46400 * (Real.pi ^ (-3 : ℝ)) ^ 2 * Real.pi *
        riemannZetaFourMajorant ^ 2 * t ^ 9 := by ring
    _ ≤ 46400 * (Real.pi ^ (-3 : ℝ)) ^ 2 * Real.pi *
        riemannZetaFourMajorant ^ 2 * t ^ 12 := by gcongr
    _ ≤ (46400 * (Real.pi ^ (-3 : ℝ)) ^ 2 * Real.pi *
        riemannZetaFourMajorant ^ 2) * (100 + 4 * t ^ 2) ^ 6 := by gcongr

noncomputable def extendedXiRightSqBound : ℝ :=
  46400 * (Real.pi ^ (-3 : ℝ)) ^ 2 * Real.pi *
    riemannZetaFourMajorant ^ 2

noncomputable def extendedXiRightBound : ℝ :=
  Real.exp (Real.pi / 2) * extendedXiStripBound +
    extendedXiRightSqBound + 1

theorem extendedXiRightSqBound_nonneg : 0 ≤ extendedXiRightSqBound := by
  unfold extendedXiRightSqBound
  positivity

theorem norm_extendedWeightedXi_six_le (T : ℝ) :
    ‖extendedWeightedXi (6 + (T : ℂ) * I)‖ ≤ extendedXiRightBound := by
  by_cases hT : T ≤ 2
  · have hs : (6 + (T : ℂ) * I : ℂ) ∈ xiRightExtensionClosedStrip := by
      change 4 ≤ (6 + (T : ℂ) * I : ℂ).re ∧
        (6 + (T : ℂ) * I : ℂ).re ≤ 6
      norm_num
    have hnorm := norm_extendedNormalizedXi_le_of_mem hs
    have hexp : Real.exp (Real.pi * T / 4) ≤ Real.exp (Real.pi / 2) := by
      apply Real.exp_le_exp.mpr
      nlinarith [Real.pi_pos]
    unfold extendedWeightedXi
    rw [norm_mul, norm_upperWeight]
    change ‖extendedNormalizedXi (6 + (T : ℂ) * I)‖ ≤
      extendedXiStripBound at hnorm
    calc
      Real.exp (Real.pi * (6 + (T : ℂ) * I).im / 4) *
          ‖riemannXiEntire (6 + (T : ℂ) * I) /
            (6 + (T : ℂ) * I + 4) ^ 6‖ ≤
          Real.exp (Real.pi / 2) * extendedXiStripBound := by
        rw [show (6 + (T : ℂ) * I : ℂ).im = T by simp]
        change ‖extendedNormalizedXi (6 + (T : ℂ) * I)‖ ≤
          extendedXiStripBound at hnorm
        exact mul_le_mul hexp hnorm (norm_nonneg _) (Real.exp_nonneg _)
      _ ≤ extendedXiRightBound := by
        unfold extendedXiRightBound
        linarith [extendedXiRightSqBound_nonneg]
  · have hT2 : 2 < T := lt_of_not_ge hT
    let t := T / 2
    have ht : 1 ≤ t := by dsimp [t]; linarith
    have hsq := norm_extendedWeightedXi_six_sq_le ht
    have harg : 6 + (((2 * t : ℝ) : ℂ) * I) =
        6 + (T : ℂ) * I := by
      congr 2
      norm_cast
      dsimp [t]
      ring
    rw [harg] at hsq
    calc
      ‖extendedWeightedXi (6 + (T : ℂ) * I)‖ ≤
          ‖extendedWeightedXi (6 + (T : ℂ) * I)‖ ^ 2 + 1 := by
        nlinarith [norm_nonneg (extendedWeightedXi (6 + (T : ℂ) * I))]
      _ ≤ extendedXiRightSqBound + 1 := by
        unfold extendedXiRightSqBound
        linarith
      _ ≤ extendedXiRightBound := by
        unfold extendedXiRightBound
        have hnonneg : 0 ≤ Real.exp (Real.pi / 2) * extendedXiStripBound :=
          mul_nonneg (Real.exp_nonneg _) extendedXiStripBound_nonneg
        linarith

/-- The old `Re(s)=4` boundary estimate controls the sixth-power extension
normalization as well. -/
theorem norm_extendedWeightedXi_four_le (T : ℝ) :
    ‖extendedWeightedXi (4 + (T : ℂ) * I)‖ ≤
      upperWeightedXiRightBound := by
  let s : ℂ := 4 + (T : ℂ) * I
  have hd : 1 ≤ ‖s + 4‖ := by
    calc
      1 ≤ |(s + 4).re| := by norm_num [s]
      _ ≤ ‖s + 4‖ := Complex.abs_re_le_norm _
  have hd0 : 0 < ‖s + 4‖ := zero_lt_one.trans_le hd
  have hold := norm_upperWeightedNormalizedXi_right_le T
  change ‖upperWeightedNormalizedXi s‖ ≤ upperWeightedXiRightBound at hold
  have hrel : ‖extendedWeightedXi s‖ =
      ‖upperWeightedNormalizedXi s‖ / ‖s + 4‖ ^ 2 := by
    unfold extendedWeightedXi upperWeightedNormalizedXi normalizedRiemannXi
    simp only [norm_mul, norm_div, norm_pow]
    field_simp [ne_of_gt hd0]
  rw [hrel]
  exact (div_le_self (norm_nonneg _) (by nlinarith [sq_nonneg ‖s + 4‖])).trans hold

noncomputable def extendedGaussianXi (ε : ℝ) (s : ℂ) : ℂ :=
  Complex.exp ((ε : ℂ) * s ^ 2) * extendedWeightedXi s

theorem differentiableOn_extendedGaussianXi_closure (ε : ℝ) :
    DifferentiableOn ℂ (extendedGaussianXi ε)
      (closure xiRightExtensionStrip) := by
  intro s hs
  unfold extendedGaussianXi
  exact (Complex.differentiable_exp.differentiableAt.comp s
    (((differentiable_const (ε : ℂ)).mul
      (differentiable_id.pow 2)).differentiableAt)).differentiableWithinAt.mul
    (differentiableOn_extendedWeightedXi_closure s hs)

theorem diffContOnCl_extendedGaussianXi (ε : ℝ) :
    DiffContOnCl ℂ (extendedGaussianXi ε) xiRightExtensionStrip :=
  (differentiableOn_extendedGaussianXi_closure ε).diffContOnCl

noncomputable def extendedGaussianGlobalBound (ε : ℝ) : ℝ :=
  Real.exp (36 * ε + (Real.pi / 4) ^ 2 / (4 * ε)) *
    extendedXiStripBound

theorem norm_extendedGaussianXi_le
    {ε : ℝ} (hε : 0 < ε) {s : ℂ}
    (hs : s ∈ xiRightExtensionClosedStrip) :
    ‖extendedGaussianXi ε s‖ ≤ extendedGaussianGlobalBound ε := by
  have hnorm := norm_extendedNormalizedXi_le_of_mem hs
  have hreSq : s.re ^ 2 ≤ 36 := by
    change 4 ≤ s.re ∧ s.re ≤ 6 at hs
    nlinarith [sq_nonneg (s.re - 4), sq_nonneg (6 - s.re)]
  have hquad : -ε * s.im ^ 2 + (Real.pi / 4) * s.im ≤
      (Real.pi / 4) ^ 2 / (4 * ε) := by
    have hsq := sq_nonneg (2 * ε * s.im - Real.pi / 4)
    apply (le_div_iff₀ (by positivity : 0 < 4 * ε)).2
    nlinarith
  have hexpArg : ε * (s.re ^ 2 - s.im ^ 2) +
      Real.pi * s.im / 4 ≤
      36 * ε + (Real.pi / 4) ^ 2 / (4 * ε) := by
    nlinarith
  unfold extendedGaussianXi extendedWeightedXi
  rw [norm_mul, norm_gaussianFactor, norm_mul, norm_upperWeight]
  unfold extendedGaussianGlobalBound
  change ‖extendedNormalizedXi s‖ ≤ extendedXiStripBound at hnorm
  calc
    Real.exp (ε * (s.re ^ 2 - s.im ^ 2)) *
        (Real.exp (Real.pi * s.im / 4) * ‖extendedNormalizedXi s‖) =
        Real.exp (ε * (s.re ^ 2 - s.im ^ 2) + Real.pi * s.im / 4) *
          ‖extendedNormalizedXi s‖ := by rw [Real.exp_add]; ring
    _ ≤ Real.exp (36 * ε + (Real.pi / 4) ^ 2 / (4 * ε)) *
        extendedXiStripBound :=
      mul_le_mul (Real.exp_le_exp.mpr hexpArg) hnorm
        (norm_nonneg _) (Real.exp_nonneg _)

theorem bddAbove_extendedGaussianXi_closedStrip
    {ε : ℝ} (hε : 0 < ε) :
    BddAbove ((norm ∘ extendedGaussianXi ε) ''
      xiRightExtensionClosedStrip) := by
  refine ⟨extendedGaussianGlobalBound ε, ?_⟩
  rintro _ ⟨s, hs, rfl⟩
  exact norm_extendedGaussianXi_le hε hs

noncomputable def extendedXiBoundaryBound : ℝ :=
  max weightedXiBoundaryBound extendedXiRightBound

noncomputable def extendedRegularizedBoundaryBound (ε : ℝ) : ℝ :=
  Real.exp (36 * ε) * extendedXiBoundaryBound

theorem extendedXiBoundaryBound_pos : 0 < extendedXiBoundaryBound := by
  exact lt_of_lt_of_le weightedXiBoundaryBound_pos (le_max_left _ _)

theorem norm_extendedGaussianXi_boundary_le
    {ε : ℝ} (hε : 0 < ε) {s : ℂ}
    (hs : s.re = 4 ∨ s.re = 6) :
    ‖extendedGaussianXi ε s‖ ≤ extendedRegularizedBoundaryBound ε := by
  have hgauss : ‖Complex.exp ((ε : ℂ) * s ^ 2)‖ ≤
      Real.exp (36 * ε) := by
    rw [norm_gaussianFactor]
    apply Real.exp_le_exp.mpr
    rcases hs with hs | hs <;> rw [hs] <;>
      nlinarith [sq_nonneg s.im]
  have hweighted : ‖extendedWeightedXi s‖ ≤ extendedXiBoundaryBound := by
    rcases hs with hs | hs
    · have hz : s = 4 + (s.im : ℂ) * I := by
        apply Complex.ext <;> simp [hs]
      rw [hz]
      exact (norm_extendedWeightedXi_four_le s.im).trans
        (le_trans (le_max_right _ _) (le_max_left _ _))
    · have hz : s = 6 + (s.im : ℂ) * I := by
        apply Complex.ext <;> simp [hs]
      rw [hz]
      exact (norm_extendedWeightedXi_six_le s.im).trans (le_max_right _ _)
  unfold extendedGaussianXi extendedRegularizedBoundaryBound
  rw [norm_mul]
  exact mul_le_mul hgauss hweighted (norm_nonneg _) (Real.exp_nonneg _)

theorem norm_extendedGaussianXi_le_threeLines
    {ε : ℝ} (hε : 0 < ε) {s : ℂ}
    (hs : s ∈ xiRightExtensionClosedStrip) :
    ‖extendedGaussianXi ε s‖ ≤
      (extendedRegularizedBoundaryBound ε) ^
          (1 - (s.re - 4) / (6 - 4)) *
        (extendedRegularizedBoundaryBound ε) ^
          ((s.re - 4) / (6 - 4)) := by
  apply Complex.HadamardThreeLines.norm_le_interp_of_mem_verticalClosedStrip'
    (l := 4) (u := 6) (a := extendedRegularizedBoundaryBound ε)
    (b := extendedRegularizedBoundaryBound ε)
  · norm_num
  · exact hs
  · exact diffContOnCl_extendedGaussianXi ε
  · exact bddAbove_extendedGaussianXi_closedStrip hε
  · intro z hz
    exact norm_extendedGaussianXi_boundary_le hε (Or.inl hz)
  · intro z hz
    exact norm_extendedGaussianXi_boundary_le hε (Or.inr hz)

theorem norm_extendedGaussianXi_le_boundaryBound
    {ε : ℝ} (hε : 0 < ε) {s : ℂ}
    (hs : s ∈ xiRightExtensionClosedStrip) :
    ‖extendedGaussianXi ε s‖ ≤ extendedRegularizedBoundaryBound ε := by
  have h := norm_extendedGaussianXi_le_threeLines hε hs
  have hpos : 0 < extendedRegularizedBoundaryBound ε :=
    mul_pos (Real.exp_pos _) extendedXiBoundaryBound_pos
  rw [← Real.rpow_add hpos] at h
  have hsum : 1 - (s.re - 4) / (6 - 4) +
      (s.re - 4) / (6 - 4) = 1 := by ring
  rw [hsum, Real.rpow_one] at h
  exact h

theorem norm_extendedWeightedXi_le_boundaryBound
    {s : ℂ} (hs : s ∈ xiRightExtensionClosedStrip) :
    ‖extendedWeightedXi s‖ ≤ extendedXiBoundaryBound := by
  let l : Filter ℝ := 𝓝[Set.Ioi 0] 0
  letI : NeBot l := by dsimp [l]; infer_instance
  have hl_le : l ≤ 𝓝 0 := by dsimp [l]; exact inf_le_left
  have hleft : Tendsto (fun ε : ℝ ↦ ‖extendedGaussianXi ε s‖) l
      (𝓝 ‖extendedWeightedXi s‖) := by
    have hc : ContinuousAt (fun ε : ℝ ↦ ‖extendedGaussianXi ε s‖) 0 := by
      unfold extendedGaussianXi
      fun_prop
    simpa [l, extendedGaussianXi] using hc.tendsto.mono_left hl_le
  have hright : Tendsto (fun ε : ℝ ↦ extendedRegularizedBoundaryBound ε) l
      (𝓝 extendedXiBoundaryBound) := by
    have hc : ContinuousAt (fun ε : ℝ ↦ extendedRegularizedBoundaryBound ε) 0 := by
      unfold extendedRegularizedBoundaryBound
      fun_prop
    simpa [l, extendedRegularizedBoundaryBound] using hc.tendsto.mono_left hl_le
  apply le_of_tendsto_of_tendsto hleft hright
  filter_upwards [self_mem_nhdsWithin] with ε hε
  exact norm_extendedGaussianXi_le_boundaryBound hε hs

theorem norm_riemannXiEntire_le_rightExtensionBound
    {s : ℂ} (hs : s ∈ xiRightExtensionClosedStrip) :
    ‖riemannXiEntire s‖ ≤ extendedXiBoundaryBound * ‖s + 4‖ ^ 6 *
      Real.exp (-(Real.pi * s.im / 4)) := by
  have h := norm_extendedWeightedXi_le_boundaryBound hs
  unfold extendedWeightedXi at h
  rw [norm_mul, norm_upperWeight, norm_div, norm_pow] at h
  have hd : 0 < ‖s + 4‖ :=
    norm_pos_iff.mpr (add_four_ne_zero_of_mem_xiRightExtensionClosedStrip hs)
  have he : 0 < Real.exp (Real.pi * s.im / 4) := Real.exp_pos _
  calc
    ‖riemannXiEntire s‖ =
        (Real.exp (Real.pi * s.im / 4) *
          (‖riemannXiEntire s‖ / ‖s + 4‖ ^ 6)) *
          ‖s + 4‖ ^ 6 * Real.exp (-(Real.pi * s.im / 4)) := by
      rw [Real.exp_neg]
      field_simp [ne_of_gt hd, ne_of_gt he]
    _ ≤ extendedXiBoundaryBound * ‖s + 4‖ ^ 6 *
        Real.exp (-(Real.pi * s.im / 4)) := by gcongr

end RiemannLab
