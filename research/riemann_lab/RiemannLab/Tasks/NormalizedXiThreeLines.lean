import RiemannLab.Tasks.ComplexGammaVertical

namespace RiemannLab

open Complex Set Filter Topology
open scoped LSeries.notation

/-!
Polynomial normalization and functional symmetry for the xi-type function.
The fourth power is chosen so that the exponentially weighted boundary values
obtained from `ComplexGammaVertical` are bounded, while its only denominator
zero, `-4`, remains strictly outside the working strip `-3 ≤ Re(s) ≤ 4`.
-/

/-- Functional symmetry of the entire xi-type function. -/
theorem riemannXiEntire_one_sub (s : ℂ) :
    riemannXiEntire (1 - s) = riemannXiEntire s := by
  unfold riemannXiEntire
  rw [completedRiemannZeta₀_one_sub]
  ring

/-- Fourth-power polynomial normalization used for the three-lines step. -/
noncomputable def normalizedRiemannXi (s : ℂ) : ℂ :=
  riemannXiEntire s / (s + 4) ^ 4

/-- The closed vertical strip containing the critical strip and the two
integer boundary lines used by the Gamma identities. -/
def xiVerticalClosedStrip : Set ℂ :=
  Complex.re ⁻¹' Set.Icc (-3 : ℝ) 4

def xiVerticalStrip : Set ℂ :=
  Complex.HadamardThreeLines.verticalStrip (-3 : ℝ) 4

theorem isClosed_xiVerticalClosedStrip : IsClosed xiVerticalClosedStrip := by
  exact isClosed_Icc.preimage continuous_re

theorem closure_xiVerticalStrip_subset :
    closure xiVerticalStrip ⊆ xiVerticalClosedStrip := by
  apply closure_minimal
  · intro s hs
    exact ⟨hs.1.le, hs.2.le⟩
  · exact isClosed_xiVerticalClosedStrip

theorem add_four_ne_zero_of_mem_xiVerticalClosedStrip
    {s : ℂ} (hs : s ∈ xiVerticalClosedStrip) : s + 4 ≠ 0 := by
  intro h
  have hre := congrArg Complex.re h
  have := hs.1
  simp at hre
  linarith

theorem differentiableOn_normalizedRiemannXi_closure :
    DifferentiableOn ℂ normalizedRiemannXi (closure xiVerticalStrip) := by
  intro s hs
  apply DifferentiableAt.differentiableWithinAt
  unfold normalizedRiemannXi
  exact differentiable_riemannXiEntire.differentiableAt.div
    ((differentiable_id.add_const 4).pow 4).differentiableAt
    (pow_ne_zero 4 (add_four_ne_zero_of_mem_xiVerticalClosedStrip
      (closure_xiVerticalStrip_subset hs)))

theorem diffContOnCl_normalizedRiemannXi :
    DiffContOnCl ℂ normalizedRiemannXi xiVerticalStrip :=
  differentiableOn_normalizedRiemannXi_closure.diffContOnCl

/-- The polynomial normalization is uniformly bounded on the complete closed
strip using the qualitative completed-zeta strip majorant. -/
theorem norm_normalizedRiemannXi_le_of_mem
    {s : ℂ} (hs : s ∈ xiVerticalClosedStrip) :
    ‖normalizedRiemannXi s‖ ≤
      30 * completedRiemannZeta₀StripMajorant (-3) 4 + 1 := by
  let r := ‖s + 4‖
  let C := completedRiemannZeta₀StripMajorant (-3) 4
  have hC : 0 ≤ C := completedRiemannZeta₀StripMajorant_nonneg _ _
  have hre : 1 ≤ (s + 4).re := by
    change -3 ≤ s.re ∧ s.re ≤ 4 at hs
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
  have hxi : ‖riemannXiEntire s‖ ≤ 30 * C * r ^ 2 + 1 := by
    refine (norm_riemannXiEntire_le_stripMajorant s hs.1 hs.2).trans ?_
    dsimp [C]
    calc
      ‖s‖ * ‖s - 1‖ * C + 1 ≤ (5 * r) * (6 * r) * C + 1 := by gcongr
      _ = 30 * C * r ^ 2 + 1 := by ring
  have hxi' : ‖riemannXiEntire s‖ ≤ (30 * C + 1) * r ^ 2 := by
    calc
      ‖riemannXiEntire s‖ ≤ 30 * C * r ^ 2 + 1 := hxi
      _ ≤ (30 * C + 1) * r ^ 2 := by
        nlinarith [sq_nonneg r]
  have hr0 : 0 < r := zero_lt_one.trans_le hr
  unfold normalizedRiemannXi
  rw [norm_div, norm_pow]
  apply (div_le_iff₀ (pow_pos hr0 4)).2
  calc
    ‖riemannXiEntire s‖ ≤ (30 * C + 1) * r ^ 2 := hxi'
    _ ≤ (30 * C + 1) * r ^ 4 := by
      have hK : 0 ≤ 30 * C + 1 := by positivity
      gcongr
      nlinarith [sq_nonneg r]
    _ = (30 * completedRiemannZeta₀StripMajorant (-3) 4 + 1) *
        ‖s + 4‖ ^ 4 := by rfl

theorem bddAbove_normalizedRiemannXi_closedStrip :
    BddAbove ((norm ∘ normalizedRiemannXi) '' xiVerticalClosedStrip) := by
  refine ⟨30 * completedRiemannZeta₀StripMajorant (-3) 4 + 1, ?_⟩
  rintro _ ⟨s, hs, rfl⟩
  exact norm_normalizedRiemannXi_le_of_mem hs

/-- Upper-height exponential weight.  Its norm is `exp(pi*Im(s)/4)`,
cancelling the Gamma decay on positive ordinates. -/
noncomputable def upperWeightedNormalizedXi (s : ℂ) : ℂ :=
  Complex.exp ((-I * (Real.pi : ℂ) / 4) * s) * normalizedRiemannXi s

theorem differentiableOn_upperWeightedNormalizedXi_closure :
    DifferentiableOn ℂ upperWeightedNormalizedXi (closure xiVerticalStrip) := by
  intro s hs
  apply DifferentiableAt.differentiableWithinAt
  unfold upperWeightedNormalizedXi
  have hnormAt : DifferentiableAt ℂ normalizedRiemannXi s := by
    unfold normalizedRiemannXi
    exact differentiable_riemannXiEntire.differentiableAt.div
      ((differentiable_id.add_const 4).pow 4).differentiableAt
      (pow_ne_zero 4 (add_four_ne_zero_of_mem_xiVerticalClosedStrip
        (closure_xiVerticalStrip_subset hs)))
  exact (Complex.differentiable_exp.differentiableAt.comp s
    (((differentiable_const (-I * (Real.pi : ℂ) / 4)).mul
      differentiable_id).differentiableAt)).mul
    hnormAt

theorem diffContOnCl_upperWeightedNormalizedXi :
    DiffContOnCl ℂ upperWeightedNormalizedXi xiVerticalStrip :=
  differentiableOn_upperWeightedNormalizedXi_closure.diffContOnCl

theorem norm_upperWeight (s : ℂ) :
    ‖Complex.exp ((-I * (Real.pi : ℂ) / 4) * s)‖ =
      Real.exp (Real.pi * s.im / 4) := by
  rw [Complex.norm_exp]
  congr 2
  simp [Complex.mul_re, Complex.div_re, Complex.normSq_ofReal]
  ring

/-- Absolute Dirichlet-series majorant for zeta on `Re(s)=4`. -/
noncomputable def riemannZetaFourMajorant : ℝ :=
  ∑' n : ℕ, ‖LSeries.term (fun _ : ℕ ↦ (1 : ℂ)) (4 : ℂ) n‖

theorem summable_riemannZetaFourMajorant :
    Summable (fun n : ℕ ↦
      ‖LSeries.term (fun _ : ℕ ↦ (1 : ℂ)) (4 : ℂ) n‖) := by
  exact (LSeriesSummable_one_iff.mpr (by norm_num : 1 < (4 : ℂ).re)).norm

theorem riemannZetaFourMajorant_nonneg : 0 ≤ riemannZetaFourMajorant := by
  exact tsum_nonneg fun _ ↦ norm_nonneg _

/-- Uniform zeta bound in the half-plane `Re(s)≥4`. -/
theorem norm_riemannZeta_le_fourMajorant {s : ℂ} (hs : 4 ≤ s.re) :
    ‖riemannZeta s‖ ≤ riemannZetaFourMajorant := by
  have hs1 : 1 < s.re := lt_of_lt_of_le (by norm_num) hs
  have hsumS : Summable (fun n : ℕ ↦
      ‖LSeries.term (fun _ : ℕ ↦ (1 : ℂ)) s n‖) :=
    (LSeriesSummable_one_iff.mpr hs1).norm
  have hterm : ∀ n : ℕ,
      ‖LSeries.term (fun _ : ℕ ↦ (1 : ℂ)) s n‖ ≤
        ‖LSeries.term (fun _ : ℕ ↦ (1 : ℂ)) (4 : ℂ) n‖ := by
    intro n
    exact LSeries.norm_term_le_of_re_le_re _ (by simpa using hs) n
  rw [← LSeries_one_eq_riemannZeta hs1]
  unfold LSeries riemannZetaFourMajorant
  exact (norm_tsum_le_tsum_norm hsumS).trans
    (hsumS.tsum_mono summable_riemannZetaFourMajorant hterm)

/-- Factorization of the entire xi-type function into its elementary,
Gamma, and zeta factors away from `0` and `1`. -/
theorem riemannXiEntire_eq_mul_GammaR_riemannZeta
    {s : ℂ} (hs0 : s ≠ 0) (hs1 : s ≠ 1) (hre : 0 < s.re) :
    riemannXiEntire s = s * (s - 1) * Gammaℝ s * riemannZeta s := by
  rw [riemannXiEntire_eq_mul_completedRiemannZeta hs0 hs1]
  rw [riemannZeta_def_of_ne_zero hs0]
  field_simp [Gammaℝ_ne_zero_of_re_pos hre]

theorem norm_riemannXiEntire_conj_of_re_pos
    {s : ℂ} (hre : 0 < s.re) (hs0 : s ≠ 0) (hs1 : s ≠ 1) :
    ‖riemannXiEntire (starRingEnd ℂ s)‖ = ‖riemannXiEntire s‖ := by
  have hconj0 : starRingEnd ℂ s ≠ 0 := (map_ne_zero (starRingEnd ℂ)).mpr hs0
  have hconj1 : starRingEnd ℂ s ≠ 1 := by
    intro h
    apply hs1
    have := congrArg (starRingEnd ℂ) h
    simpa using this
  rw [riemannXiEntire_eq_mul_GammaR_riemannZeta hconj0 hconj1 (by simpa using hre),
    riemannXiEntire_eq_mul_GammaR_riemannZeta hs0 hs1 hre]
  have hsub : starRingEnd ℂ s - 1 = starRingEnd ℂ (s - 1) := by simp
  simp only [norm_mul]
  rw [norm_conj, hsub, norm_conj, norm_GammaR_conj, riemannZeta_conj, norm_conj]

private theorem normSq_four_add_two_mul_I (t : ℝ) :
    ‖(4 : ℂ) + ((2 * t : ℝ) : ℂ) * I‖ ^ 2 = 16 + 4 * t ^ 2 := by
  rw [Complex.sq_norm]
  simp [Complex.normSq_apply]
  ring

private theorem normSq_three_add_two_mul_I (t : ℝ) :
    ‖(3 : ℂ) + ((2 * t : ℝ) : ℂ) * I‖ ^ 2 = 9 + 4 * t ^ 2 := by
  rw [Complex.sq_norm]
  simp [Complex.normSq_apply]
  ring

private theorem normSq_eight_add_two_mul_I (t : ℝ) :
    ‖(8 : ℂ) + ((2 * t : ℝ) : ℂ) * I‖ ^ 2 = 64 + 4 * t ^ 2 := by
  rw [Complex.sq_norm]
  simp [Complex.normSq_apply]
  ring

/-- Exact norm ledger for the exponentially weighted, normalized xi function
on the right boundary `Re(s)=4`. -/
theorem norm_upperWeightedNormalizedXi_four_sq {t : ℝ} (ht : 0 < t) :
    ‖upperWeightedNormalizedXi
        (4 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2 =
      Real.exp (Real.pi * t) *
        ((16 + 4 * t ^ 2) * (9 + 4 * t ^ 2) *
          ((Real.pi ^ (-2 : ℝ)) ^ 2 *
            ((1 + t ^ 2) *
              (Real.pi * t / Real.sinh (Real.pi * t)))) *
          ‖riemannZeta (4 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2) /
        (64 + 4 * t ^ 2) ^ 4 := by
  let s : ℂ := 4 + ((2 * t : ℝ) : ℂ) * I
  have hsre : s.re = 4 := by simp [s]
  have hsim : s.im = 2 * t := by simp [s]
  have hs0 : s ≠ 0 := by
    exact ne_zero_of_re_pos (by rw [hsre]; norm_num)
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
  have hnorms : ‖s‖ ^ 2 = 16 + 4 * t ^ 2 := by
    simpa [s] using normSq_four_add_two_mul_I t
  have hnorms1 : ‖(3 : ℂ) + ((2 * t : ℝ) : ℂ) * I‖ ^ 2 =
      9 + 4 * t ^ 2 := normSq_three_add_two_mul_I t
  have hnorms4 : ‖(8 : ℂ) + ((2 * t : ℝ) : ℂ) * I‖ ^ 2 =
      64 + 4 * t ^ 2 := normSq_eight_add_two_mul_I t
  have hden : (‖(8 : ℂ) + ((2 * t : ℝ) : ℂ) * I‖ ^ 4) ^ 2 =
      (64 + 4 * t ^ 2) ^ 4 := by
    calc
      (‖(8 : ℂ) + ((2 * t : ℝ) : ℂ) * I‖ ^ 4) ^ 2 =
          (‖(8 : ℂ) + ((2 * t : ℝ) : ℂ) * I‖ ^ 2) ^ 4 := by ring
      _ = (64 + 4 * t ^ 2) ^ 4 := by rw [hnorms4]
  have hgamma : ‖Gammaℝ s‖ ^ 2 =
      (Real.pi ^ (-2 : ℝ)) ^ 2 *
        ((1 + t ^ 2) * (Real.pi * t / Real.sinh (Real.pi * t))) := by
    simpa [s] using norm_GammaR_four_add_two_mul_I_sq ht
  rw [show 4 + ((2 * t : ℝ) : ℂ) * I = s by rfl]
  unfold upperWeightedNormalizedXi normalizedRiemannXi
  rw [norm_mul, norm_div, norm_pow, mul_pow, div_pow]
  rw [norm_upperWeight]
  rw [riemannXiEntire_eq_mul_GammaR_riemannZeta hs0 hs1
    (by rw [hsre]; norm_num)]
  simp only [norm_mul]
  rw [show s - 1 = 3 + ((2 * t : ℝ) : ℂ) * I by simp [s]; ring]
  rw [show s + 4 = 8 + ((2 * t : ℝ) : ℂ) * I by simp [s]; ring]
  rw [hsim]
  simp only [mul_pow]
  rw [hexp, hnorms, hnorms1, hden, hgamma]
  ring

/-- A height-independent bound for the squared norm on the positive-ordinate
part of the right boundary.  Constants are intentionally coarse. -/
theorem norm_upperWeightedNormalizedXi_four_sq_le {t : ℝ} (ht : 1 ≤ t) :
    ‖upperWeightedNormalizedXi
        (4 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2 ≤
      2080 * (Real.pi ^ (-2 : ℝ)) ^ 2 * Real.pi *
        riemannZetaFourMajorant ^ 2 := by
  rw [norm_upperWeightedNormalizedXi_four_sq (zero_lt_one.trans_le ht)]
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
    (s := 4 + ((2 * t : ℝ) : ℂ) * I) (by simp)
  have hzetaSq : ‖riemannZeta
      (4 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2 ≤
      riemannZetaFourMajorant ^ 2 := by
    nlinarith [norm_nonneg (riemannZeta
      (4 + ((2 * t : ℝ) : ℂ) * I)), riemannZetaFourMajorant_nonneg]
  have h16 : 16 + 4 * t ^ 2 ≤ 20 * t ^ 2 := by nlinarith [sq_nonneg t]
  have h9 : 9 + 4 * t ^ 2 ≤ 13 * t ^ 2 := by nlinarith [sq_nonneg t]
  have h1 : 1 + t ^ 2 ≤ 2 * t ^ 2 := by nlinarith [sq_nonneg t]
  have hdenpos : 0 < (64 + 4 * t ^ 2) ^ 4 := by positivity
  have hden : t ^ 8 ≤ (64 + 4 * t ^ 2) ^ 4 := by
    have ht2 : t ^ 2 ≤ 64 + 4 * t ^ 2 := by nlinarith [sq_nonneg t]
    calc
      t ^ 8 = (t ^ 2) ^ 4 := by ring
      _ ≤ (64 + 4 * t ^ 2) ^ 4 := by gcongr
  have ht7 : t ^ 7 ≤ t ^ 8 := by
    calc
      t ^ 7 = t ^ 7 * 1 := by ring
      _ ≤ t ^ 7 * t := by gcongr
      _ = t ^ 8 := by ring
  have hpiPow : 0 ≤ (Real.pi ^ (-2 : ℝ)) ^ 2 := sq_nonneg _
  have hM : 0 ≤ riemannZetaFourMajorant ^ 2 := sq_nonneg _
  apply (div_le_iff₀ hdenpos).2
  calc
    Real.exp (Real.pi * t) *
          ((16 + 4 * t ^ 2) * (9 + 4 * t ^ 2) *
              ((Real.pi ^ (-2 : ℝ)) ^ 2 *
                ((1 + t ^ 2) *
                  (Real.pi * t / Real.sinh (Real.pi * t)))) *
            ‖riemannZeta (4 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2) ≤
        (20 * t ^ 2) * (13 * t ^ 2) *
          (Real.pi ^ (-2 : ℝ)) ^ 2 * (2 * t ^ 2) *
          (4 * Real.pi * t) * riemannZetaFourMajorant ^ 2 := by
      calc
        _ = (16 + 4 * t ^ 2) * (9 + 4 * t ^ 2) *
            (Real.pi ^ (-2 : ℝ)) ^ 2 * (1 + t ^ 2) *
            (Real.exp (Real.pi * t) *
              (Real.pi * t / Real.sinh (Real.pi * t))) *
            ‖riemannZeta (4 + ((2 * t : ℝ) : ℂ) * I)‖ ^ 2 := by ring
        _ ≤ _ := by gcongr
    _ ≤ (2080 * (Real.pi ^ (-2 : ℝ)) ^ 2 * Real.pi *
          riemannZetaFourMajorant ^ 2) *
        (64 + 4 * t ^ 2) ^ 4 := by
      calc
        _ = 2080 * (Real.pi ^ (-2 : ℝ)) ^ 2 * Real.pi *
            riemannZetaFourMajorant ^ 2 * t ^ 7 := by ring
        _ ≤ 2080 * (Real.pi ^ (-2 : ℝ)) ^ 2 * Real.pi *
            riemannZetaFourMajorant ^ 2 * t ^ 8 := by gcongr
        _ ≤ _ := by gcongr

noncomputable def normalizedXiStripBound : ℝ :=
  30 * completedRiemannZeta₀StripMajorant (-3) 4 + 1

noncomputable def upperWeightedXiRightSqBound : ℝ :=
  2080 * (Real.pi ^ (-2 : ℝ)) ^ 2 * Real.pi *
    riemannZetaFourMajorant ^ 2

noncomputable def upperWeightedXiRightBound : ℝ :=
  Real.exp (Real.pi / 2) * normalizedXiStripBound +
    upperWeightedXiRightSqBound + 1

theorem normalizedXiStripBound_nonneg : 0 ≤ normalizedXiStripBound := by
  unfold normalizedXiStripBound
  have := completedRiemannZeta₀StripMajorant_nonneg (-3) 4
  linarith

theorem upperWeightedXiRightSqBound_nonneg :
    0 ≤ upperWeightedXiRightSqBound := by
  unfold upperWeightedXiRightSqBound
  exact mul_nonneg (mul_nonneg (mul_nonneg (by norm_num) (sq_nonneg _)) Real.pi_pos.le)
    (sq_nonneg _)

/-- Uniform bound on the entire right boundary, including both ordinate
directions and the compact transition range. -/
theorem norm_upperWeightedNormalizedXi_right_le (T : ℝ) :
    ‖upperWeightedNormalizedXi (4 + (T : ℂ) * I)‖ ≤
      upperWeightedXiRightBound := by
  by_cases hT : T ≤ 2
  · have hs : (4 + (T : ℂ) * I : ℂ) ∈ xiVerticalClosedStrip := by
      change -3 ≤ (4 + (T : ℂ) * I : ℂ).re ∧
        (4 + (T : ℂ) * I : ℂ).re ≤ 4
      norm_num
    have hnorm := norm_normalizedRiemannXi_le_of_mem hs
    have hexp : Real.exp (Real.pi * T / 4) ≤ Real.exp (Real.pi / 2) := by
      apply Real.exp_le_exp.mpr
      nlinarith [Real.pi_pos]
    unfold upperWeightedNormalizedXi
    rw [norm_mul, norm_upperWeight]
    calc
      Real.exp (Real.pi * (4 + (T : ℂ) * I).im / 4) *
          ‖normalizedRiemannXi (4 + (T : ℂ) * I)‖ ≤
          Real.exp (Real.pi / 2) * normalizedXiStripBound := by
        rw [show (4 + (T : ℂ) * I : ℂ).im = T by simp]
        change ‖normalizedRiemannXi (4 + (T : ℂ) * I)‖ ≤
          normalizedXiStripBound at hnorm
        exact mul_le_mul hexp hnorm (norm_nonneg _) (Real.exp_nonneg _)
      _ ≤ upperWeightedXiRightBound := by
        unfold upperWeightedXiRightBound
        linarith [upperWeightedXiRightSqBound_nonneg]
  · have hT2 : 2 < T := lt_of_not_ge hT
    let t := T / 2
    have ht : 1 ≤ t := by dsimp [t]; linarith
    have hsq := norm_upperWeightedNormalizedXi_four_sq_le ht
    have harg : 4 + (((2 * t : ℝ) : ℂ) * I) =
        4 + (T : ℂ) * I := by
      have htEq : ((2 * t : ℝ) : ℂ) = (T : ℂ) := by
        norm_cast
        dsimp [t]
        ring
      rw [htEq]
    rw [harg] at hsq
    calc
      ‖upperWeightedNormalizedXi (4 + (T : ℂ) * I)‖ ≤
          ‖upperWeightedNormalizedXi (4 + (T : ℂ) * I)‖ ^ 2 + 1 := by
        nlinarith [norm_nonneg (upperWeightedNormalizedXi
          (4 + (T : ℂ) * I))]
      _ ≤ upperWeightedXiRightSqBound + 1 := by
        unfold upperWeightedXiRightSqBound
        linarith
      _ ≤ upperWeightedXiRightBound := by
        unfold upperWeightedXiRightBound
        have hnonneg : 0 ≤ Real.exp (Real.pi / 2) * normalizedXiStripBound :=
          mul_nonneg (Real.exp_nonneg _) normalizedXiStripBound_nonneg
        linarith

theorem norm_riemannXiEntire_four_sub_im_eq_four_add_im (T : ℝ) :
    ‖riemannXiEntire (4 - (T : ℂ) * I)‖ =
      ‖riemannXiEntire (4 + (T : ℂ) * I)‖ := by
  let s : ℂ := 4 + (T : ℂ) * I
  have hsre : s.re = 4 := by simp [s]
  have hs0 : s ≠ 0 := ne_zero_of_re_pos (by rw [hsre]; norm_num)
  have hs1 : s ≠ 1 := by
    intro h
    have := congrArg Complex.re h
    rw [hsre] at this
    norm_num at this
  have hconj : starRingEnd ℂ s = 4 - (T : ℂ) * I := by
    apply Complex.ext <;> simp [s]
  rw [← hconj]
  exact norm_riemannXiEntire_conj_of_re_pos (by rw [hsre]; norm_num) hs0 hs1

theorem norm_riemannXiEntire_neg_three_add_im_eq_four_add_im (T : ℝ) :
    ‖riemannXiEntire (-3 + (T : ℂ) * I)‖ =
      ‖riemannXiEntire (4 + (T : ℂ) * I)‖ := by
  have hsym := riemannXiEntire_one_sub (4 - (T : ℂ) * I)
  have hone : 1 - (4 - (T : ℂ) * I) = -3 + (T : ℂ) * I := by ring
  rw [hone] at hsym
  rw [hsym, norm_riemannXiEntire_four_sub_im_eq_four_add_im]

noncomputable def upperWeightedXiLeftBound : ℝ :=
  normalizedXiStripBound + 4096 * upperWeightedXiRightBound

/-- Uniform bound on the left boundary, transferred from the right boundary
by xi functional symmetry and conjugation. -/
theorem norm_upperWeightedNormalizedXi_left_le (T : ℝ) :
    ‖upperWeightedNormalizedXi (-3 + (T : ℂ) * I)‖ ≤
      upperWeightedXiLeftBound := by
  by_cases hT : T ≤ 0
  · have hs : (-3 + (T : ℂ) * I : ℂ) ∈ xiVerticalClosedStrip := by
      change -3 ≤ (-3 + (T : ℂ) * I : ℂ).re ∧
        (-3 + (T : ℂ) * I : ℂ).re ≤ 4
      norm_num
    have hnorm := norm_normalizedRiemannXi_le_of_mem hs
    have hweight : Real.exp (Real.pi * T / 4) ≤ 1 := by
      rw [← Real.exp_zero]
      apply Real.exp_le_exp.mpr
      have := Real.pi_pos
      nlinarith
    unfold upperWeightedNormalizedXi
    rw [norm_mul, norm_upperWeight]
    rw [show (-3 + (T : ℂ) * I : ℂ).im = T by simp]
    calc
      Real.exp (Real.pi * T / 4) *
          ‖normalizedRiemannXi (-3 + (T : ℂ) * I)‖ ≤
          normalizedXiStripBound := by
        change ‖normalizedRiemannXi (-3 + (T : ℂ) * I)‖ ≤
          normalizedXiStripBound at hnorm
        nlinarith [norm_nonneg (normalizedRiemannXi
          (-3 + (T : ℂ) * I)), normalizedXiStripBound_nonneg,
          Real.exp_nonneg (Real.pi * T / 4)]
      _ ≤ upperWeightedXiLeftBound := by
        unfold upperWeightedXiLeftBound
        have : 0 ≤ upperWeightedXiRightBound := by
          unfold upperWeightedXiRightBound
          have hprod : 0 ≤ Real.exp (Real.pi / 2) * normalizedXiStripBound :=
            mul_nonneg (Real.exp_nonneg _) normalizedXiStripBound_nonneg
          linarith [upperWeightedXiRightSqBound_nonneg]
        linarith
  · have hT0 : 0 < T := lt_of_not_ge hT
    let zR : ℂ := 4 + (T : ℂ) * I
    let zL : ℂ := -3 + (T : ℂ) * I
    have hdenR : 0 < ‖zR + 4‖ := by
      apply norm_pos_iff.mpr
      intro h
      have := congrArg Complex.re h
      norm_num [zR] at this
    have hdenL : 0 < ‖zL + 4‖ := by
      apply norm_pos_iff.mpr
      intro h
      have := congrArg Complex.re h
      norm_num [zL] at this
    have hXi : ‖riemannXiEntire zL‖ = ‖riemannXiEntire zR‖ := by
      simpa [zL, zR] using
        norm_riemannXiEntire_neg_three_add_im_eq_four_add_im T
    have hdenRatio : ‖zR + 4‖ ^ 4 / ‖zL + 4‖ ^ 4 ≤ 4096 := by
      apply (div_le_iff₀ (pow_pos hdenL 4)).2
      have hR2 : ‖zR + 4‖ ^ 2 = 64 + T ^ 2 := by
        rw [Complex.sq_norm]
        simp [zR, Complex.normSq_apply]
        ring
      have hL2 : ‖zL + 4‖ ^ 2 = 1 + T ^ 2 := by
        rw [Complex.sq_norm]
        simp [zL, Complex.normSq_apply]
        ring
      calc
        ‖zR + 4‖ ^ 4 = (64 + T ^ 2) ^ 2 := by rw [show ‖zR + 4‖ ^ 4 =
          (‖zR + 4‖ ^ 2) ^ 2 by ring, hR2]
        _ ≤ 4096 * (1 + T ^ 2) ^ 2 := by nlinarith [sq_nonneg T]
        _ = 4096 * ‖zL + 4‖ ^ 4 := by
          rw [show ‖zL + 4‖ ^ 4 = (‖zL + 4‖ ^ 2) ^ 2 by ring, hL2]
    have hright := norm_upperWeightedNormalizedXi_right_le T
    change ‖upperWeightedNormalizedXi zR‖ ≤ upperWeightedXiRightBound at hright
    have hRightNonneg : 0 ≤ upperWeightedXiRightBound :=
      (norm_nonneg (upperWeightedNormalizedXi zR)).trans hright
    have hrel : ‖upperWeightedNormalizedXi zL‖ =
        ‖upperWeightedNormalizedXi zR‖ *
          (‖zR + 4‖ ^ 4 / ‖zL + 4‖ ^ 4) := by
      unfold upperWeightedNormalizedXi normalizedRiemannXi
      simp only [norm_mul, norm_div, norm_pow, norm_upperWeight]
      have himL : zL.im = T := by simp [zL]
      have himR : zR.im = T := by simp [zR]
      rw [himL, himR, hXi]
      field_simp
    rw [hrel]
    calc
      ‖upperWeightedNormalizedXi zR‖ *
          (‖zR + 4‖ ^ 4 / ‖zL + 4‖ ^ 4) ≤
          upperWeightedXiRightBound * 4096 := by
        exact mul_le_mul hright hdenRatio (div_nonneg (by positivity) (by positivity))
          hRightNonneg
      _ ≤ upperWeightedXiLeftBound := by
        unfold upperWeightedXiLeftBound
        linarith [normalizedXiStripBound_nonneg]

/-- Gaussian regularization used to apply the bounded version of Hadamard's
three-lines theorem. -/
noncomputable def gaussianRegularizedUpperXi (ε : ℝ) (s : ℂ) : ℂ :=
  Complex.exp ((ε : ℂ) * s ^ 2) * upperWeightedNormalizedXi s

theorem norm_gaussianFactor (ε : ℝ) (s : ℂ) :
    ‖Complex.exp ((ε : ℂ) * s ^ 2)‖ =
      Real.exp (ε * (s.re ^ 2 - s.im ^ 2)) := by
  rw [Complex.norm_exp]
  congr 1
  simp [pow_two, Complex.mul_re]

theorem differentiableOn_gaussianRegularizedUpperXi_closure (ε : ℝ) :
    DifferentiableOn ℂ (gaussianRegularizedUpperXi ε)
      (closure xiVerticalStrip) := by
  intro s hs
  apply DifferentiableAt.differentiableWithinAt
  unfold gaussianRegularizedUpperXi
  have hupper : DifferentiableAt ℂ upperWeightedNormalizedXi s := by
    unfold upperWeightedNormalizedXi normalizedRiemannXi
    have hden : s + 4 ≠ 0 :=
      add_four_ne_zero_of_mem_xiVerticalClosedStrip
        (closure_xiVerticalStrip_subset hs)
    exact (Complex.differentiable_exp.differentiableAt.comp s
      (((differentiable_const (-I * (Real.pi : ℂ) / 4)).mul
        differentiable_id).differentiableAt)).mul
      (differentiable_riemannXiEntire.differentiableAt.div
        ((differentiable_id.add_const 4).pow 4).differentiableAt
        (pow_ne_zero 4 hden))
  exact (Complex.differentiable_exp.differentiableAt.comp s
    (((differentiable_const (ε : ℂ)).mul
      (differentiable_id.pow 2)).differentiableAt)).mul hupper

theorem diffContOnCl_gaussianRegularizedUpperXi (ε : ℝ) :
    DiffContOnCl ℂ (gaussianRegularizedUpperXi ε) xiVerticalStrip :=
  (differentiableOn_gaussianRegularizedUpperXi_closure ε).diffContOnCl

noncomputable def gaussianRegularizedXiBound (ε : ℝ) : ℝ :=
  Real.exp (16 * ε + (Real.pi / 4) ^ 2 / (4 * ε)) *
    normalizedXiStripBound

theorem norm_gaussianRegularizedUpperXi_le
    {ε : ℝ} (hε : 0 < ε) {s : ℂ} (hs : s ∈ xiVerticalClosedStrip) :
    ‖gaussianRegularizedUpperXi ε s‖ ≤ gaussianRegularizedXiBound ε := by
  have hnorm := norm_normalizedRiemannXi_le_of_mem hs
  change ‖normalizedRiemannXi s‖ ≤ normalizedXiStripBound at hnorm
  have hreSq : s.re ^ 2 ≤ 16 := by
    change -3 ≤ s.re ∧ s.re ≤ 4 at hs
    nlinarith [sq_nonneg (s.re + 3), sq_nonneg (4 - s.re)]
  have hquad : -ε * s.im ^ 2 + (Real.pi / 4) * s.im ≤
      (Real.pi / 4) ^ 2 / (4 * ε) := by
    have hsq := sq_nonneg (2 * ε * s.im - Real.pi / 4)
    apply (le_div_iff₀ (by positivity : 0 < 4 * ε)).2
    nlinarith
  have hexpArg : ε * (s.re ^ 2 - s.im ^ 2) +
      Real.pi * s.im / 4 ≤
      16 * ε + (Real.pi / 4) ^ 2 / (4 * ε) := by
    nlinarith
  unfold gaussianRegularizedUpperXi
  rw [norm_mul, norm_gaussianFactor]
  unfold upperWeightedNormalizedXi
  rw [norm_mul, norm_upperWeight]
  unfold gaussianRegularizedXiBound
  calc
    Real.exp (ε * (s.re ^ 2 - s.im ^ 2)) *
        (Real.exp (Real.pi * s.im / 4) * ‖normalizedRiemannXi s‖) =
        Real.exp (ε * (s.re ^ 2 - s.im ^ 2) + Real.pi * s.im / 4) *
          ‖normalizedRiemannXi s‖ := by rw [Real.exp_add]; ring
    _ ≤ Real.exp (16 * ε + (Real.pi / 4) ^ 2 / (4 * ε)) *
        normalizedXiStripBound :=
      mul_le_mul (Real.exp_le_exp.mpr hexpArg) hnorm
        (norm_nonneg _) (Real.exp_nonneg _)

theorem bddAbove_gaussianRegularizedUpperXi_closedStrip
    {ε : ℝ} (hε : 0 < ε) :
    BddAbove ((norm ∘ gaussianRegularizedUpperXi ε) ''
      xiVerticalClosedStrip) := by
  refine ⟨gaussianRegularizedXiBound ε, ?_⟩
  rintro _ ⟨s, hs, rfl⟩
  exact norm_gaussianRegularizedUpperXi_le hε hs

noncomputable def weightedXiBoundaryBound : ℝ :=
  max upperWeightedXiLeftBound upperWeightedXiRightBound

noncomputable def regularizedWeightedXiBoundaryBound (ε : ℝ) : ℝ :=
  Real.exp (16 * ε) * weightedXiBoundaryBound

theorem weightedXiBoundaryBound_nonneg : 0 ≤ weightedXiBoundaryBound := by
  unfold weightedXiBoundaryBound
  have hright : 0 ≤ upperWeightedXiRightBound := by
    unfold upperWeightedXiRightBound
    have hprod : 0 ≤ Real.exp (Real.pi / 2) * normalizedXiStripBound :=
      mul_nonneg (Real.exp_nonneg _) normalizedXiStripBound_nonneg
    linarith [upperWeightedXiRightSqBound_nonneg]
  exact le_max_of_le_left (by
    unfold upperWeightedXiLeftBound
    exact add_nonneg normalizedXiStripBound_nonneg
      (mul_nonneg (by norm_num) hright))

theorem norm_gaussianRegularizedUpperXi_boundary_le
    {ε : ℝ} (hε : 0 < ε) {s : ℂ}
    (hs : s.re = -3 ∨ s.re = 4) :
    ‖gaussianRegularizedUpperXi ε s‖ ≤
      regularizedWeightedXiBoundaryBound ε := by
  have hgauss : ‖Complex.exp ((ε : ℂ) * s ^ 2)‖ ≤
      Real.exp (16 * ε) := by
    rw [norm_gaussianFactor]
    apply Real.exp_le_exp.mpr
    rcases hs with hs | hs <;> rw [hs] <;>
      nlinarith [sq_nonneg s.im]
  have hweighted : ‖upperWeightedNormalizedXi s‖ ≤
      weightedXiBoundaryBound := by
    rcases hs with hs | hs
    · have hz : s = -3 + (s.im : ℂ) * I := by
        apply Complex.ext <;> simp [hs]
      rw [hz]
      exact (norm_upperWeightedNormalizedXi_left_le s.im).trans
        (le_max_left _ _)
    · have hz : s = 4 + (s.im : ℂ) * I := by
        apply Complex.ext <;> simp [hs]
      rw [hz]
      exact (norm_upperWeightedNormalizedXi_right_le s.im).trans
        (le_max_right _ _)
  unfold gaussianRegularizedUpperXi regularizedWeightedXiBoundaryBound
  rw [norm_mul]
  exact mul_le_mul hgauss hweighted (norm_nonneg _) (Real.exp_nonneg _)

/-- Gaussian-regularized Hadamard three-lines propagation across the complete
closed strip. -/
theorem norm_gaussianRegularizedUpperXi_le_threeLines
    {ε : ℝ} (hε : 0 < ε) {s : ℂ}
    (hs : s ∈ xiVerticalClosedStrip) :
    ‖gaussianRegularizedUpperXi ε s‖ ≤
      (regularizedWeightedXiBoundaryBound ε) ^
          (1 - (s.re - (-3)) / (4 - (-3))) *
        (regularizedWeightedXiBoundaryBound ε) ^
          ((s.re - (-3)) / (4 - (-3))) := by
  apply Complex.HadamardThreeLines.norm_le_interp_of_mem_verticalClosedStrip'
    (l := -3) (u := 4) (a := regularizedWeightedXiBoundaryBound ε)
    (b := regularizedWeightedXiBoundaryBound ε)
  · norm_num
  · exact hs
  · exact diffContOnCl_gaussianRegularizedUpperXi ε
  · exact bddAbove_gaussianRegularizedUpperXi_closedStrip hε
  · intro z hz
    exact norm_gaussianRegularizedUpperXi_boundary_le hε (Or.inl hz)
  · intro z hz
    exact norm_gaussianRegularizedUpperXi_boundary_le hε (Or.inr hz)

theorem weightedXiBoundaryBound_pos : 0 < weightedXiBoundaryBound := by
  unfold weightedXiBoundaryBound
  apply lt_of_lt_of_le _ (le_max_right _ _)
  unfold upperWeightedXiRightBound
  have hprod : 0 ≤ Real.exp (Real.pi / 2) * normalizedXiStripBound :=
    mul_nonneg (Real.exp_nonneg _) normalizedXiStripBound_nonneg
  linarith [upperWeightedXiRightSqBound_nonneg]

theorem regularizedWeightedXiBoundaryBound_pos (ε : ℝ) :
    0 < regularizedWeightedXiBoundaryBound ε := by
  unfold regularizedWeightedXiBoundaryBound
  exact mul_pos (Real.exp_pos _) weightedXiBoundaryBound_pos

theorem norm_gaussianRegularizedUpperXi_le_boundaryBound
    {ε : ℝ} (hε : 0 < ε) {s : ℂ}
    (hs : s ∈ xiVerticalClosedStrip) :
    ‖gaussianRegularizedUpperXi ε s‖ ≤
      regularizedWeightedXiBoundaryBound ε := by
  have h := norm_gaussianRegularizedUpperXi_le_threeLines hε hs
  rw [← Real.rpow_add (regularizedWeightedXiBoundaryBound_pos ε)] at h
  have hsum : 1 - (s.re - (-3)) / (4 - (-3)) +
      (s.re - (-3)) / (4 - (-3)) = 1 := by ring
  rw [hsum, Real.rpow_one] at h
  exact h

/-- Sharp unregularized strip bound, obtained by sending the Gaussian
parameter to zero through positive values. -/
theorem norm_upperWeightedNormalizedXi_le_boundaryBound
    {s : ℂ} (hs : s ∈ xiVerticalClosedStrip) :
    ‖upperWeightedNormalizedXi s‖ ≤ weightedXiBoundaryBound := by
  let l : Filter ℝ := 𝓝[Set.Ioi 0] 0
  letI : NeBot l := by dsimp [l]; infer_instance
  have hl_le : l ≤ 𝓝 0 := by
    dsimp [l]
    exact inf_le_left
  have hleft : Tendsto
      (fun ε : ℝ ↦ ‖gaussianRegularizedUpperXi ε s‖) l
      (𝓝 ‖upperWeightedNormalizedXi s‖) := by
    have hc : ContinuousAt
        (fun ε : ℝ ↦ ‖gaussianRegularizedUpperXi ε s‖) 0 := by
      unfold gaussianRegularizedUpperXi
      fun_prop
    have ht := hc.tendsto.mono_left hl_le
    simpa [l, gaussianRegularizedUpperXi] using ht
  have hright : Tendsto
      (fun ε : ℝ ↦ regularizedWeightedXiBoundaryBound ε) l
      (𝓝 weightedXiBoundaryBound) := by
    have hc : ContinuousAt
        (fun ε : ℝ ↦ regularizedWeightedXiBoundaryBound ε) 0 := by
      unfold regularizedWeightedXiBoundaryBound
      fun_prop
    have ht := hc.tendsto.mono_left hl_le
    simpa [l, regularizedWeightedXiBoundaryBound] using ht
  apply le_of_tendsto_of_tendsto hleft hright
  filter_upwards [self_mem_nhdsWithin] with ε hε
  exact norm_gaussianRegularizedUpperXi_le_boundaryBound hε hs

/-- Sharp polynomial-times-exponential xi growth bound throughout the strip.
This is the unregularized output needed by the Jensen step. -/
theorem norm_riemannXiEntire_le_sharpStripBound
    {s : ℂ} (hs : s ∈ xiVerticalClosedStrip) :
    ‖riemannXiEntire s‖ ≤
      weightedXiBoundaryBound * ‖s + 4‖ ^ 4 *
        Real.exp (-(Real.pi * s.im / 4)) := by
  have h := norm_upperWeightedNormalizedXi_le_boundaryBound hs
  unfold upperWeightedNormalizedXi normalizedRiemannXi at h
  rw [norm_mul, norm_upperWeight, norm_div, norm_pow] at h
  have hnorm : 0 < ‖s + 4‖ :=
    norm_pos_iff.mpr (add_four_ne_zero_of_mem_xiVerticalClosedStrip hs)
  have hden : 0 < ‖s + 4‖ ^ 4 := by
    exact pow_pos hnorm _
  have hexp : 0 < Real.exp (Real.pi * s.im / 4) := Real.exp_pos _
  calc
    ‖riemannXiEntire s‖ =
        (Real.exp (Real.pi * s.im / 4) *
          (‖riemannXiEntire s‖ / ‖s + 4‖ ^ 4)) *
          ‖s + 4‖ ^ 4 * Real.exp (-(Real.pi * s.im / 4)) := by
        rw [Real.exp_neg]
        field_simp [ne_of_gt hnorm, ne_of_gt hexp]
    _ ≤ weightedXiBoundaryBound * ‖s + 4‖ ^ 4 *
        Real.exp (-(Real.pi * s.im / 4)) := by gcongr

end RiemannLab
