import RiemannLab.Tasks.SharpJensenZeroCount
import Mathlib.Data.Fintype.Pigeonhole

namespace RiemannLab

open Set MeromorphicOn

/-!
A finite, quantitative avoidance lemma used to turn the local Jensen count
into admissible contour heights.  The proof is a discrete pigeonhole
argument on an equally spaced grid, so it introduces no measure theory.
-/

/-- Among `card E + 1` equally spaced test heights in an interval, one stays
at least half a mesh away from every member of `E`. -/
theorem exists_height_separated_from_finset
    (E : Finset ℝ) {a b : ℝ} (hab : a < b) :
    ∃ T ∈ Icc a b, ∀ y ∈ E,
      (b - a) / (2 * (E.card + 2)) ≤ |T - y| := by
  let d : ℝ := (b - a) / (E.card + 2)
  let grid : Fin (E.card + 1) → ℝ := fun i ↦
    a + ((i.1 + 1 : ℕ) : ℝ) * d
  have hd : 0 < d := by
    dsimp [d]
    positivity
  have hgrid (i : Fin (E.card + 1)) : grid i ∈ Icc a b := by
    constructor
    · have hprod : 0 ≤ ((i.1 + 1 : ℕ) : ℝ) * d := by positivity
      dsimp [grid]
      linarith
    · have hi : (i.1 + 1 : ℝ) ≤ E.card + 1 := by
        exact_mod_cast i.2
      have hden : (0 : ℝ) < E.card + 2 := by positivity
      have hquot : ((i.1 + 1 : ℕ) : ℝ) * d ≤ b - a := by
        dsimp [d]
        calc
          ((i.1 + 1 : ℕ) : ℝ) * ((b - a) / (E.card + 2)) =
              (((i.1 + 1 : ℕ) : ℝ) * (b - a)) / (E.card + 2) := by ring
          _ ≤ b - a := by
            apply (div_le_iff₀ hden).2
            have hcoef : ((i.1 + 1 : ℕ) : ℝ) ≤ E.card + 2 := by
              norm_num only [Nat.cast_add, Nat.cast_one] at hi ⊢
              linarith
            nlinarith [mul_le_mul_of_nonneg_right hcoef (sub_nonneg.mpr hab.le)]
      dsimp [grid]
      linarith
  by_contra h
  push_neg at h
  have hnear : ∀ i : Fin (E.card + 1),
      ∃ y ∈ E, |grid i - y| < d / 2 := by
    intro i
    obtain ⟨y, hyE, hy⟩ := h (grid i) (hgrid i)
    refine ⟨y, hyE, ?_⟩
    have heq : (b - a) / (2 * (E.card + 2)) = d / 2 := by
      dsimp [d]
      field_simp
      <;> ring
    rw [← heq]
    exact hy
  let near : Fin (E.card + 1) → {y // y ∈ E} := fun i ↦
    ⟨Classical.choose (hnear i), (Classical.choose_spec (hnear i)).1⟩
  have hnear' (i : Fin (E.card + 1)) :
      |grid i - (near i : ℝ)| < d / 2 :=
    (Classical.choose_spec (hnear i)).2
  have hcard : Fintype.card {y // y ∈ E} <
      Fintype.card (Fin (E.card + 1)) := by
    simp
  obtain ⟨i, j, hij, hsame⟩ :=
    Fintype.exists_ne_map_eq_of_card_lt near hcard
  have hsum : |grid i - (near i : ℝ)| +
      |grid j - (near j : ℝ)| < d := by
    linarith [hnear' i, hnear' j]
  have hclose : |grid i - grid j| < d := by
    calc
      |grid i - grid j| =
          |(grid i - (near i : ℝ)) - (grid j - (near j : ℝ))| := by
        rw [hsame]
        congr 1
        ring
      _ ≤ |grid i - (near i : ℝ)| +
          |grid j - (near j : ℝ)| := abs_sub _ _
      _ < d := hsum
  have hvals : i.1 < j.1 ∨ j.1 < i.1 := by
    apply Nat.lt_or_gt_of_ne
    intro heq
    exact hij (Fin.ext heq)
  rcases hvals with hijv | hjiv
  · have hcast : ((i.1 : ℕ) : ℝ) + 1 ≤ (j.1 : ℕ) := by
      exact_mod_cast hijv
    have hcoef : ((i.1 + 1 : ℕ) : ℝ) + 1 ≤ (j.1 + 1 : ℕ) := by
      push_cast
      linarith
    have hmul := mul_le_mul_of_nonneg_right hcoef hd.le
    have hsep : d ≤ |grid i - grid j| := by
      have hsign : grid i - grid j ≤ 0 := by
        dsimp [grid]
        nlinarith
      rw [abs_of_nonpos hsign]
      dsimp [grid]
      nlinarith
    linarith
  · have hcast : ((j.1 : ℕ) : ℝ) + 1 ≤ (i.1 : ℕ) := by
      exact_mod_cast hjiv
    have hcoef : ((j.1 + 1 : ℕ) : ℝ) + 1 ≤ (i.1 + 1 : ℕ) := by
      push_cast
      linarith
    have hmul := mul_le_mul_of_nonneg_right hcoef hd.le
    have hsep : d ≤ |grid i - grid j| := by
      have hsign : 0 ≤ grid i - grid j := by
        dsimp [grid]
        nlinarith
      rw [abs_of_nonneg hsign]
      dsimp [grid]
      nlinarith
    linarith

/-- The finite support of the xi divisor in the radius-seven-halves Jensen
disk.  This enlarged packet covers the full displaced-left contour corners. -/
noncomputable def xiJensenDivisorSupport (T : ℝ) : Finset ℂ :=
  ((divisor riemannXiEntire
    (Metric.closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ))).finiteSupport
      (isCompact_closedBall _ _)).toFinset

@[simp] theorem mem_xiJensenDivisorSupport {T : ℝ} {z : ℂ} :
    z ∈ xiJensenDivisorSupport T ↔
      divisor riemannXiEntire
        (Metric.closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ)) z ≠ 0 := by
  simp [xiJensenDivisorSupport, Function.mem_support]

theorem riemannXiEntire_eq_zero_iff_mem_xiJensenDivisorSupport
    {T : ℝ} {z : ℂ}
    (hz : z ∈ Metric.closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ)) :
    riemannXiEntire z = 0 ↔ z ∈ xiJensenDivisorSupport T := by
  let U := Metric.closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ)
  have hana : AnalyticOnNhd ℂ riemannXiEntire U :=
    fun w _ ↦ analyticAt_riemannXiEntire w
  have hc : riemannXiJensenCenter T ∈ U := by
    simp [U]
    norm_num
  have hcenterOrder : meromorphicOrderAt riemannXiEntire
      (riemannXiJensenCenter T) ≠ ⊤ := by
    rw [(analyticAt_riemannXiEntire _).meromorphicOrderAt_eq,
      (analyticAt_riemannXiEntire _).analyticOrderAt_eq_zero.2
        (riemannXiEntire_ne_zero_jensenCenter T)]
    simp
  have horder : ∀ w : U, meromorphicOrderAt riemannXiEntire w ≠ ⊤ := by
    intro w
    exact hana.meromorphicOn.meromorphicOrderAt_ne_top_of_isPreconnected
      Metric.isPreconnected_closedBall hc w.2 hcenterOrder
  have hzero := hana.meromorphicNFOn.zero_set_eq_divisor_support horder
  have hzU : z ∈ U := hz
  have hziff : riemannXiEntire z = 0 ↔
      z ∈ Function.support (divisor riemannXiEntire U) := by
    have := Set.ext_iff.mp hzero z
    simpa [hzU] using this
  rw [hziff]
  simp [xiJensenDivisorSupport, U, Function.mem_support]

/-- Each point in the support contributes at least one to the analytic xi
divisor, so its cardinality is bounded by the multiplicity-aware Jensen sum. -/
theorem xiJensenDivisorSupport_card_le_finsum (T : ℝ) :
    (xiJensenDivisorSupport T).card ≤
      ∑ᶠ u, divisor riemannXiEntire
        (Metric.closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ)) u := by
  let D := divisor riemannXiEntire
    (Metric.closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ))
  have hana : AnalyticOnNhd ℂ riemannXiEntire
      (Metric.closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ)) :=
    fun z _ ↦ analyticAt_riemannXiEntire z
  rw [finsum_eq_sum_of_support_subset (s := xiJensenDivisorSupport T)]
  · change ((xiJensenDivisorSupport T).card : ℤ) ≤
        ∑ u ∈ xiJensenDivisorSupport T, D u
    rw [Finset.card_eq_sum_ones]
    push_cast
    apply Finset.sum_le_sum
    intro z hz
    have hzD : D z ≠ 0 := by
      simpa [xiJensenDivisorSupport, D, Function.mem_support] using hz
    have hz0 : 0 ≤ D z := hana.divisor_nonneg z
    omega
  · intro z hz
    simpa [xiJensenDivisorSupport, D, Function.mem_support] using hz

theorem xiJensenDivisorSupport_card_le_log
    {T : ℝ} (hT : 2 ≤ T) :
    ((xiJensenDivisorSupport T).card : ℝ) ≤
      (Real.log jensenQuotientPolynomialConstant + 12 * Real.log T) /
        Real.log (8 / 7) := by
  have hcard := xiJensenDivisorSupport_card_le_finsum T
  have hcardR : ((xiJensenDivisorSupport T).card : ℝ) ≤
      ((∑ᶠ u, divisor riemannXiEntire
        (Metric.closedBall (riemannXiJensenCenter T) (7 / 2 : ℝ)) u : ℤ) : ℝ) := by
    exact_mod_cast hcard
  exact hcardR.trans (riemannXiEntire_local_zero_count_seven_halves_le_log hT)

noncomputable def xiJensenZeroOrdinates (T : ℝ) : Finset ℝ :=
  (xiJensenDivisorSupport T).image Complex.im

noncomputable def jensenLocalLogBound (T : ℝ) : ℝ :=
  (Real.log jensenQuotientPolynomialConstant + 12 * Real.log T) /
    Real.log (8 / 7)

/-- Quantitative height selection for the actual finite xi divisor support.
The following cardinal estimate turns this denominator into `O(log T)`. -/
theorem exists_height_separated_from_xiJensenZeros
    (T : ℝ) {a b : ℝ} (hab : a < b) :
    ∃ H ∈ Icc a b, ∀ z ∈ xiJensenDivisorSupport T,
      (b - a) / (2 * ((xiJensenZeroOrdinates T).card + 2)) ≤
        |H - z.im| := by
  obtain ⟨H, hHab, hH⟩ :=
    exists_height_separated_from_finset (xiJensenZeroOrdinates T) hab
  refine ⟨H, hHab, ?_⟩
  intro z hz
  exact hH z.im (Finset.mem_image.mpr ⟨z, hz, rfl⟩)

/-- The selected height has the explicit reciprocal-logarithmic separation
which is needed in the logarithmic-derivative estimate. -/
theorem exists_height_with_logarithmic_xi_separation
    {T : ℝ} (hT : 2 ≤ T) {a b : ℝ} (hab : a < b) :
    ∃ H ∈ Icc a b, ∀ z ∈ xiJensenDivisorSupport T,
      (b - a) / (2 * (jensenLocalLogBound T + 2)) ≤ |H - z.im| := by
  obtain ⟨H, hHI, hH⟩ := exists_height_separated_from_xiJensenZeros T hab
  refine ⟨H, hHI, ?_⟩
  have hsupp : ((xiJensenDivisorSupport T).card : ℝ) ≤
      jensenLocalLogBound T := by
    simpa [jensenLocalLogBound] using xiJensenDivisorSupport_card_le_log hT
  have himage : ((xiJensenZeroOrdinates T).card : ℝ) ≤
      (xiJensenDivisorSupport T).card := by
    exact_mod_cast Finset.card_image_le
  have hbound : ((xiJensenZeroOrdinates T).card : ℝ) ≤
      jensenLocalLogBound T := himage.trans hsupp
  have hsmallpos : 0 < 2 * ((xiJensenZeroOrdinates T).card + 2 : ℝ) := by
    positivity
  have hden : 2 * ((xiJensenZeroOrdinates T).card + 2 : ℝ) ≤
      2 * (jensenLocalLogBound T + 2) := by
    nlinarith
  intro z hz
  exact (div_le_div_of_nonneg_left (sub_nonneg.mpr hab.le) hsmallpos hden).trans
    (hH z hz)

/-- A canonical quantitatively separated height in each unit interval. -/
noncomputable def quantitativeAdmissibleZetaHeight (n : ℕ) : ℝ :=
  Classical.choose (exists_height_separated_from_xiJensenZeros
    ((n : ℝ) + 3) (by linarith : (n : ℝ) + 2 < (n : ℝ) + 3))

theorem quantitativeAdmissibleZetaHeight_spec (n : ℕ) :
    quantitativeAdmissibleZetaHeight n ∈
        Icc ((n : ℝ) + 2) ((n : ℝ) + 3) ∧
      ∀ z ∈ xiJensenDivisorSupport ((n : ℝ) + 3),
        (((n : ℝ) + 3) - ((n : ℝ) + 2)) /
            (2 * ((xiJensenZeroOrdinates ((n : ℝ) + 3)).card + 2)) ≤
          |quantitativeAdmissibleZetaHeight n - z.im| := by
  unfold quantitativeAdmissibleZetaHeight
  exact Classical.choose_spec (exists_height_separated_from_xiJensenZeros
    ((n : ℝ) + 3) (by linarith : (n : ℝ) + 2 < (n : ℝ) + 3))

theorem quantitativeAdmissibleZetaHeight_mem (n : ℕ) :
    quantitativeAdmissibleZetaHeight n ∈
      Icc ((n : ℝ) + 2) ((n : ℝ) + 3) :=
  (quantitativeAdmissibleZetaHeight_spec n).1

theorem quantitativeAdmissibleZetaHeight_lower (n : ℕ) :
    (n : ℝ) + 2 ≤ quantitativeAdmissibleZetaHeight n :=
  (quantitativeAdmissibleZetaHeight_mem n).1

theorem quantitativeAdmissibleZetaHeight_upper (n : ℕ) :
    quantitativeAdmissibleZetaHeight n ≤ (n : ℝ) + 3 :=
  (quantitativeAdmissibleZetaHeight_mem n).2

theorem tendsto_quantitativeAdmissibleZetaHeight_atTop :
    Filter.Tendsto quantitativeAdmissibleZetaHeight Filter.atTop Filter.atTop := by
  refine Filter.tendsto_atTop.2 fun b ↦ ?_
  obtain ⟨N, hN⟩ := exists_nat_ge b
  filter_upwards [Filter.eventually_ge_atTop N] with n hn
  have hNn : (N : ℝ) ≤ n := by exact_mod_cast hn
  exact hN.trans (hNn.trans (by
    linarith [quantitativeAdmissibleZetaHeight_lower n]))

theorem quantitativeAdmissibleZetaHeight_separation (n : ℕ)
    {z : ℂ} (hz : z ∈ xiJensenDivisorSupport ((n : ℝ) + 3)) :
    1 / (2 * ((xiJensenZeroOrdinates ((n : ℝ) + 3)).card + 2)) ≤
      |quantitativeAdmissibleZetaHeight n - z.im| := by
  have h := (quantitativeAdmissibleZetaHeight_spec n).2 z hz
  norm_num at h ⊢
  exact h

theorem quantitativeAdmissibleZetaHeight_log_separation (n : ℕ)
    {z : ℂ} (hz : z ∈ xiJensenDivisorSupport ((n : ℝ) + 3)) :
    1 / (2 * (jensenLocalLogBound ((n : ℝ) + 3) + 2)) ≤
      |quantitativeAdmissibleZetaHeight n - z.im| := by
  have hT : 2 ≤ (n : ℝ) + 3 := by
    have hn : 0 ≤ (n : ℝ) := Nat.cast_nonneg n
    linarith
  have hsupp : ((xiJensenDivisorSupport ((n : ℝ) + 3)).card : ℝ) ≤
      jensenLocalLogBound ((n : ℝ) + 3) := by
    simpa [jensenLocalLogBound] using xiJensenDivisorSupport_card_le_log hT
  have himage : ((xiJensenZeroOrdinates ((n : ℝ) + 3)).card : ℝ) ≤
      (xiJensenDivisorSupport ((n : ℝ) + 3)).card := by
    exact_mod_cast Finset.card_image_le
  have hbound := himage.trans hsupp
  have hsmall : 0 <
      2 * ((xiJensenZeroOrdinates ((n : ℝ) + 3)).card + 2 : ℝ) := by
    positivity
  have hden :
      2 * ((xiJensenZeroOrdinates ((n : ℝ) + 3)).card + 2 : ℝ) ≤
        2 * (jensenLocalLogBound ((n : ℝ) + 3) + 2) := by
    nlinarith
  exact (div_le_div_of_nonneg_left zero_le_one hsmall hden).trans
    (quantitativeAdmissibleZetaHeight_separation n hz)

theorem riemannZeta_ne_zero_on_quantitativeAdmissibleZetaHeight
    (n : ℕ) (σ : ℝ) :
    riemannZeta (σ + quantitativeAdmissibleZetaHeight n * Complex.I) ≠ 0 := by
  intro hzeta
  let ρ : ℂ := σ + quantitativeAdmissibleZetaHeight n * Complex.I
  have hH := quantitativeAdmissibleZetaHeight_mem n
  have hρim : ρ.im = quantitativeAdmissibleZetaHeight n := by simp [ρ]
  have hρ : IsNontrivialZetaZero ρ := by
    refine ⟨hzeta, ?_⟩
    rintro ⟨k, hk⟩
    have him := congrArg Complex.im hk
    simp [ρ] at him
    linarith [hH.1]
  have him : |ρ.im - ((n : ℝ) + 3)| ≤ 1 := by
    rw [hρim, abs_of_nonpos]
    · linarith [hH.1]
    · linarith [hH.2]
  have hball3 := hρ.mem_jensenClosedBall him
  have hball : ρ ∈ Metric.closedBall
      (riemannXiJensenCenter ((n : ℝ) + 3)) (7 / 2 : ℝ) :=
    Metric.closedBall_subset_closedBall (by norm_num) hball3
  have hsupport : ρ ∈ xiJensenDivisorSupport ((n : ℝ) + 3) :=
    (riemannXiEntire_eq_zero_iff_mem_xiJensenDivisorSupport hball).1
      hρ.riemannXiEntire_eq_zero
  have hsep := quantitativeAdmissibleZetaHeight_separation n hsupport
  rw [hρim, sub_self, abs_zero] at hsep
  have hpos : 0 <
      1 / (2 * ((xiJensenZeroOrdinates ((n : ℝ) + 3)).card + 2) : ℝ) := by
    positivity
  linarith

/-- Conjugation transfers quantitative zero-freeness to the reflected lower
horizontal line. -/
theorem riemannZeta_ne_zero_on_neg_quantitativeAdmissibleZetaHeight
    (n : ℕ) (σ : ℝ) :
    riemannZeta (σ - quantitativeAdmissibleZetaHeight n * Complex.I) ≠ 0 := by
  intro hz
  have hzconj := riemannZeta_conj
    ((σ : ℂ) - quantitativeAdmissibleZetaHeight n * Complex.I)
  rw [hz, map_zero] at hzconj
  apply riemannZeta_ne_zero_on_quantitativeAdmissibleZetaHeight n σ
  convert hzconj using 1 <;> push_cast <;> simp

end RiemannLab
