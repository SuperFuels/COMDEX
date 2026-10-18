import RiemannLab.Tasks.LiToeplitzAmplifier
import RiemannLab.Tasks.CompactZetaDivisor

namespace RiemannLab

open ComplexConjugate

/-!
# Exact finite spectral isolation

This file replaces approximate suppression of a finite dominant cluster by
an exact interpolation filter.  It also proves a four-channel quadrature
lemma: after real-coefficient localization, an unknown complex phase cannot
hide a nonzero transverse defect from every channel.
-/

/-- A normalized product filter which equals one at `target` and zero at
every listed competitor.  It is a polynomial in `z` multiplied by a nonzero
constant. -/
noncomputable def finiteModeIsolator
    (target : ℂ) (competitors : Finset ℂ) (z : ℂ) : ℂ :=
  ∏ w ∈ competitors, (z - w) / (target - w)

/-- Exact normalization at the selected mode. -/
theorem finiteModeIsolator_at_target
    {target : ℂ} {competitors : Finset ℂ}
    (htarget : target ∉ competitors) :
    finiteModeIsolator target competitors target = 1 := by
  unfold finiteModeIsolator
  apply Finset.prod_eq_one
  intro w hw
  rw [div_self]
  exact sub_ne_zero.mpr (Ne.symm (ne_of_mem_of_not_mem hw htarget))

/-- Every member of the finite competing cluster is annihilated exactly. -/
theorem finiteModeIsolator_at_competitor
    {target z : ℂ} {competitors : Finset ℂ}
    (hz : z ∈ competitors) :
    finiteModeIsolator target competitors z = 0 := by
  unfold finiteModeIsolator
  apply Finset.prod_eq_zero hz
  simp

/-- Multiplying an arbitrary seed by the isolator preserves its selected
value. -/
theorem mul_finiteModeIsolator_at_target
    (seed : ℂ → ℂ) {target : ℂ} {competitors : Finset ℂ}
    (htarget : target ∉ competitors) :
    seed target * finiteModeIsolator target competitors target = seed target := by
  rw [finiteModeIsolator_at_target htarget, mul_one]

/-- The same multiplication kills every competing mode. -/
theorem mul_finiteModeIsolator_at_competitor
    (seed : ℂ → ℂ) {target z : ℂ} {competitors : Finset ℂ}
    (hz : z ∈ competitors) :
    seed z * finiteModeIsolator target competitors z = 0 := by
  rw [finiteModeIsolator_at_competitor hz, mul_zero]

/-! ## Instantiation on the actual compact zeta divisor -/

/-- All compact zeta-divisor modes except the selected target. -/
noncomputable def compactZetaModeCompetitors
    (K : Set ℂ) (hK : IsCompact K) (target : ℂ) : Finset ℂ :=
  (compactZetaDivisorSupport K hK).erase target

/-- The exact isolator attached to a selected point of the actual compact
zeta divisor. -/
noncomputable def compactZetaModeIsolator
    (K : Set ℂ) (hK : IsCompact K) (target z : ℂ) : ℂ :=
  finiteModeIsolator target (compactZetaModeCompetitors K hK target) z

/-- The compact-divisor isolator is normalized to one at its target. -/
theorem compactZetaModeIsolator_at_target
    (K : Set ℂ) (hK : IsCompact K) (target : ℂ) :
    compactZetaModeIsolator K hK target target = 1 := by
  apply finiteModeIsolator_at_target
  simp [compactZetaModeCompetitors]

/-- Every other zero in the actual compact zeta divisor is killed exactly,
independently of its multiplicity. -/
theorem compactZetaModeIsolator_at_other_zero
    (K : Set ℂ) (hK : IsCompact K) {target z : ℂ}
    (hz : z ∈ compactZetaDivisorSupport K hK) (hne : z ≠ target) :
    compactZetaModeIsolator K hK target z = 0 := by
  apply finiteModeIsolator_at_competitor
  simp [compactZetaModeCompetitors, hz, hne]

/-! ## Real-coordinate annihilation for critical-line competitors -/

/-- A real-coefficient polynomial which vanishes at every listed real
`u=q+q⁻¹` coordinate. -/
noncomputable def finiteRealModeAnnihilator
    (competitors : Finset ℝ) (u : ℂ) : ℂ :=
  ∏ c ∈ competitors, (u - (c : ℂ))

/-- The real-coordinate annihilator kills every listed critical coordinate. -/
theorem finiteRealModeAnnihilator_at_competitor
    {competitors : Finset ℝ} {c : ℝ} (hc : c ∈ competitors) :
    finiteRealModeAnnihilator competitors (c : ℂ) = 0 := by
  unfold finiteRealModeAnnihilator
  apply Finset.prod_eq_zero hc
  simp

/-- Its coefficients are real, so conjugation is preserved. -/
theorem finiteRealModeAnnihilator_conj
    (competitors : Finset ℝ) (u : ℂ) :
    finiteRealModeAnnihilator competitors (conj u) =
      conj (finiteRealModeAnnihilator competitors u) := by
  simp [finiteRealModeAnnihilator]

/-- A genuinely transverse point `a+ib` cannot be one of the real
competitors, so its localized amplitude is nonzero. -/
theorem finiteRealModeAnnihilator_target_ne_zero
    (competitors : Finset ℝ) {a b : ℝ} (hb : b ≠ 0) :
    finiteRealModeAnnihilator competitors
        ((a : ℂ) + (b : ℂ) * Complex.I) ≠ 0 := by
  unfold finiteRealModeAnnihilator
  apply Finset.prod_ne_zero_iff.mpr
  intro c hc
  intro h
  have him := congrArg Complex.im h
  simp at him
  exact hb him

/-- Pull the real annihilator back to the reciprocal Toeplitz coordinate
`u=z+z⁻¹`. -/
noncomputable def reciprocalRealModeFilter
    (competitors : Finset ℝ) (z : ℂ) : ℂ :=
  finiteRealModeAnnihilator competitors (z + z⁻¹)

/-- The pulled-back filter is exactly reciprocal symmetric. -/
theorem reciprocalRealModeFilter_inv
    (competitors : Finset ℝ) (z : ℂ) :
    reciprocalRealModeFilter competitors z⁻¹ =
      reciprocalRealModeFilter competitors z := by
  simp [reciprocalRealModeFilter, add_comm]

/-- It also preserves conjugation, because all annihilator coordinates are
real. -/
theorem reciprocalRealModeFilter_conj
    (competitors : Finset ℝ) (z : ℂ) :
    reciprocalRealModeFilter competitors (conj z) =
      conj (reciprocalRealModeFilter competitors z) := by
  unfold reciprocalRealModeFilter
  rw [show conj z + (conj z)⁻¹ = conj (z + z⁻¹) by simp]
  exact finiteRealModeAnnihilator_conj competitors (z + z⁻¹)

/-- A Toeplitz mode whose reciprocal coordinate is listed is killed exactly. -/
theorem reciprocalRealModeFilter_eq_zero
    {competitors : Finset ℝ} {z : ℂ} {c : ℝ}
    (hc : c ∈ competitors) (hu : z + z⁻¹ = (c : ℂ)) :
    reciprocalRealModeFilter competitors z = 0 := by
  rw [reciprocalRealModeFilter, hu]
  exact finiteRealModeAnnihilator_at_competitor hc

/-- Reciprocal pairing squares the same localized amplitude; no uncontrolled
second value is introduced. -/
theorem reciprocalRealModeFilter_mul_inv
    (competitors : Finset ℝ) (z : ℂ) :
    reciprocalRealModeFilter competitors z *
        reciprocalRealModeFilter competitors z⁻¹ =
      reciprocalRealModeFilter competitors z ^ 2 := by
  rw [reciprocalRealModeFilter_inv]
  ring

/-! ## Conjugate-pair annihilation for arbitrary off-line competitors -/

/-- A real-coefficient annihilator for an arbitrary finite complex cluster.
Each listed coordinate and its conjugate are both roots. -/
noncomputable def finiteConjugatePairAnnihilator
    (competitors : Finset ℂ) (u : ℂ) : ℂ :=
  ∏ v ∈ competitors, (u - v) * (u - conj v)

/-- Every listed complex coordinate is killed exactly. -/
theorem finiteConjugatePairAnnihilator_at_competitor
    {competitors : Finset ℂ} {v : ℂ} (hv : v ∈ competitors) :
    finiteConjugatePairAnnihilator competitors v = 0 := by
  unfold finiteConjugatePairAnnihilator
  apply Finset.prod_eq_zero hv
  simp

/-- The conjugate of every listed coordinate is killed as well. -/
theorem finiteConjugatePairAnnihilator_at_conj_competitor
    {competitors : Finset ℂ} {v : ℂ} (hv : v ∈ competitors) :
    finiteConjugatePairAnnihilator competitors (conj v) = 0 := by
  unfold finiteConjugatePairAnnihilator
  apply Finset.prod_eq_zero hv
  simp

/-- Pairing every root with its conjugate makes the annihilator commute with
conjugation even when the original finite cluster is off the critical line. -/
theorem finiteConjugatePairAnnihilator_conj
    (competitors : Finset ℂ) (u : ℂ) :
    finiteConjugatePairAnnihilator competitors (conj u) =
      conj (finiteConjugatePairAnnihilator competitors u) := by
  unfold finiteConjugatePairAnnihilator
  rw [map_prod]
  apply Finset.prod_congr rfl
  intro v hv
  simp
  ring

/-- A target separated from every competitor and its conjugate has nonzero
localized amplitude. -/
theorem finiteConjugatePairAnnihilator_target_ne_zero
    {competitors : Finset ℂ} {target : ℂ}
    (hsep : ∀ v ∈ competitors, target ≠ v ∧ target ≠ conj v) :
    finiteConjugatePairAnnihilator competitors target ≠ 0 := by
  unfold finiteConjugatePairAnnihilator
  apply Finset.prod_ne_zero_iff.mpr
  intro v hv
  exact mul_ne_zero (sub_ne_zero.mpr (hsep v hv).1)
    (sub_ne_zero.mpr (hsep v hv).2)

/-! ## Four-channel phase removal -/

/-- Pure real algebra behind the channel bank.  If the squared localized
amplitude has coordinates `(x,y)` and the transverse displacement `b` is
nonzero, at least one of four real channels has strictly positive real part.
The corresponding quartet defect, multiplied by `-4b²`, is strictly
negative. -/
theorem four_channel_real_part_positive
    {x y b : ℝ} (hb : b ≠ 0) (hxy : x ≠ 0 ∨ y ≠ 0) :
    0 < x ∨
      0 < -(b ^ 2) * x ∨
      0 < (1 - b ^ 2) * x - 2 * b * y ∨
      0 < (1 - b ^ 2) * x + 2 * b * y := by
  rcases lt_trichotomy x 0 with hx | hx | hx
  · exact Or.inr (Or.inl (mul_pos_of_neg_of_neg (neg_lt_zero.mpr
      (sq_pos_of_ne_zero hb)) hx))
  · right
    right
    have hy : y ≠ 0 := by
      intro hy
      rcases hxy with hxne | hyne
      · exact hxne hx
      · exact hyne hy
    have hby : b * y ≠ 0 := mul_ne_zero hb hy
    rcases lt_or_gt_of_ne hby with hby | hby
    · left
      rw [hx]
      simp
      linarith
    · right
      rw [hx]
      simp
      linarith
  · exact Or.inl hx

/-- Complex form of the four-channel lemma.  The channels are `w`, `ibw`,
`(1+ib)w`, and `(-1+ib)w`.  No phase of a nonzero localized amplitude can
make all four squared real parts nonpositive. -/
theorem four_channel_complex_square_re_positive
    {w : ℂ} {b : ℝ} (hw : w ≠ 0) (hb : b ≠ 0) :
    0 < (w ^ 2).re ∨
      0 < (((Complex.I * (b : ℂ)) * w) ^ 2).re ∨
      0 < ((((1 : ℂ) + Complex.I * (b : ℂ)) * w) ^ 2).re ∨
      0 < ((((-1 : ℂ) + Complex.I * (b : ℂ)) * w) ^ 2).re := by
  have hw2 : w ^ 2 ≠ 0 := pow_ne_zero 2 hw
  have hcoords : (w ^ 2).re ≠ 0 ∨ (w ^ 2).im ≠ 0 := by
    by_contra h
    simp only [not_or, not_ne_iff] at h
    apply hw2
    apply Complex.ext <;> simp [h.1, h.2]
  have h := four_channel_real_part_positive hb hcoords
  have hi : (((Complex.I * (b : ℂ)) * w) ^ 2).re =
      -(b ^ 2) * (w ^ 2).re := by
    simp [pow_two, Complex.mul_re, Complex.mul_im]
    ring
  have hplus : ((((1 : ℂ) + Complex.I * (b : ℂ)) * w) ^ 2).re =
      (1 - b ^ 2) * (w ^ 2).re - 2 * b * (w ^ 2).im := by
    simp [pow_two, Complex.mul_re, Complex.mul_im]
    ring
  have hminus : ((((-1 : ℂ) + Complex.I * (b : ℂ)) * w) ^ 2).re =
      (1 - b ^ 2) * (w ^ 2).re + 2 * b * (w ^ 2).im := by
    simp [pow_two, Complex.mul_re, Complex.mul_im]
    ring
  rw [hi, hplus, hminus]
  exact h

/-- Multiplication by the negative quartet prefactor converts the positive
channel into a strict negative certificate. -/
theorem four_channel_quartet_defect_negative
    {w : ℂ} {b : ℝ} (hw : w ≠ 0) (hb : b ≠ 0) :
    (-4 * b ^ 2 * (w ^ 2).re < 0) ∨
      (-4 * b ^ 2 * (((Complex.I * (b : ℂ)) * w) ^ 2).re < 0) ∨
      (-4 * b ^ 2 * ((((1 : ℂ) + Complex.I * (b : ℂ)) * w) ^ 2).re < 0) ∨
      (-4 * b ^ 2 * ((((-1 : ℂ) + Complex.I * (b : ℂ)) * w) ^ 2).re < 0) := by
  rcases four_channel_complex_square_re_positive hw hb with h | h | h | h
  · exact Or.inl (mul_neg_of_neg_of_pos
      (mul_neg_of_neg_of_pos (by norm_num) (sq_pos_of_ne_zero hb)) h)
  · exact Or.inr (Or.inl (mul_neg_of_neg_of_pos
      (mul_neg_of_neg_of_pos (by norm_num) (sq_pos_of_ne_zero hb)) h))
  · exact Or.inr (Or.inr (Or.inl (mul_neg_of_neg_of_pos
      (mul_neg_of_neg_of_pos (by norm_num) (sq_pos_of_ne_zero hb)) h)))
  · exact Or.inr (Or.inr (Or.inr (mul_neg_of_neg_of_pos
      (mul_neg_of_neg_of_pos (by norm_num) (sq_pos_of_ne_zero hb)) h)))

/-- Exact finite-cluster conclusion: after annihilating an arbitrary finite
set of critical-line coordinates, at least one of four real polynomial
channels retains a strict negative off-critical quartet defect. -/
theorem finite_real_cluster_four_channel_negative
    (competitors : Finset ℝ) {a b : ℝ} (hb : b ≠ 0) :
    let w := finiteRealModeAnnihilator competitors
      ((a : ℂ) + (b : ℂ) * Complex.I)
    (-4 * b ^ 2 * (w ^ 2).re < 0) ∨
      (-4 * b ^ 2 * (((Complex.I * (b : ℂ)) * w) ^ 2).re < 0) ∨
      (-4 * b ^ 2 * ((((1 : ℂ) + Complex.I * (b : ℂ)) * w) ^ 2).re < 0) ∨
      (-4 * b ^ 2 * ((((-1 : ℂ) + Complex.I * (b : ℂ)) * w) ^ 2).re < 0) := by
  dsimp
  exact four_channel_quartet_defect_negative
    (finiteRealModeAnnihilator_target_ne_zero competitors hb) hb

/-- Strong finite-cluster isolation theorem.  An arbitrary finite collection
of critical or off-critical competitor coordinates can be removed together
with all of their conjugates.  For every separated transverse target, one of
four channels still gives a strict negative quartet defect. -/
theorem finite_conjugate_cluster_four_channel_negative
    (competitors : Finset ℂ) {a b : ℝ} (hb : b ≠ 0)
    (hsep : ∀ v ∈ competitors,
      (a : ℂ) + (b : ℂ) * Complex.I ≠ v ∧
      (a : ℂ) + (b : ℂ) * Complex.I ≠ conj v) :
    let w := finiteConjugatePairAnnihilator competitors
      ((a : ℂ) + (b : ℂ) * Complex.I)
    (-4 * b ^ 2 * (w ^ 2).re < 0) ∨
      (-4 * b ^ 2 * (((Complex.I * (b : ℂ)) * w) ^ 2).re < 0) ∨
      (-4 * b ^ 2 * ((((1 : ℂ) + Complex.I * (b : ℂ)) * w) ^ 2).re < 0) ∨
      (-4 * b ^ 2 * ((((-1 : ℂ) + Complex.I * (b : ℂ)) * w) ^ 2).re < 0) := by
  dsimp
  exact four_channel_quartet_defect_negative
    (finiteConjugatePairAnnihilator_target_ne_zero hsep) hb

end RiemannLab
