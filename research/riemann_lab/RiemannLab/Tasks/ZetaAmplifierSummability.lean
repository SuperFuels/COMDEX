import RiemannLab.Tasks.ZetaTwoSidedDampedSummability
import RiemannLab.Tasks.LiToeplitzAmplifier

namespace RiemannLab

open ComplexConjugate

/-!
# The actual finite amplifier is dominated by the zeta shell envelope

At height at least two, the Li coordinate `q = 1-ρ⁻¹` and its reciprocal
both have norm at most `3/2`.  Consequently every fixed finite annihilator
is uniformly bounded, while the damping factor `(1-q)^4 = ρ⁻⁴` supplies the
summable fourth power.
-/

/-- The Li coordinate attached to a zero. -/
noncomputable def zetaLiCoordinate (ρ : ℂ) : ℂ := 1 - ρ⁻¹

/-- A fixed finite-cluster annihilator multiplied by the fourth-power damped
Toeplitz amplifier. -/
noncomputable def localizedZetaAmplifier
    (competitors : Finset ℂ) (a : ℂ) (mode : ℕ) (ρ : ℂ) : ℂ :=
  let q := zetaLiCoordinate ρ
  liToeplitzAmplifier a 2 mode q *
    finiteConjugatePairAnnihilator competitors (q + q⁻¹)

/-- Explicit height-independent bound for the fixed polynomial factors. -/
noncomputable def localizedZetaAmplifierConstant
    (competitors : Finset ℂ) (a : ℂ) (mode : ℕ) : ℝ :=
  (((3 / 2 : ℝ) ^ 2 + ‖a‖ * (3 / 2 : ℝ) + 1) *
      (1 + (3 / 2 : ℝ) ^ (2 * mode))) *
    ∏ v ∈ competitors, (3 + ‖v‖) ^ 2

theorem localizedZetaAmplifierConstant_nonneg
    (competitors : Finset ℂ) (a : ℂ) (mode : ℕ) :
    0 ≤ localizedZetaAmplifierConstant competitors a mode := by
  unfold localizedZetaAmplifierConstant
  positivity

/-- A point of ordinate at least two has norm at least two. -/
theorem two_le_norm_of_two_le_abs_im {ρ : ℂ} (him : 2 ≤ |ρ.im|) :
    2 ≤ ‖ρ‖ := by
  exact him.trans (Complex.abs_im_le_norm ρ)

/-- High zeros have uniformly bounded Li coordinate. -/
theorem norm_zetaLiCoordinate_le_three_halves
    {ρ : ℂ} (him : 2 ≤ |ρ.im|) :
    ‖zetaLiCoordinate ρ‖ ≤ 3 / 2 := by
  have hnorm : 2 ≤ ‖ρ‖ := two_le_norm_of_two_le_abs_im him
  have hinv : ‖ρ⁻¹‖ ≤ 1 / 2 := by
    rw [norm_inv]
    calc
      ‖ρ‖⁻¹ ≤ (2 : ℝ)⁻¹ :=
        (inv_le_inv₀ (by linarith) (by norm_num)).mpr hnorm
      _ = 1 / 2 := by norm_num
  unfold zetaLiCoordinate
  calc
    ‖1 - ρ⁻¹‖ ≤ ‖(1 : ℂ)‖ + ‖ρ⁻¹‖ := norm_sub_le _ _
    _ ≤ 3 / 2 := by norm_num at *; linarith

/-- The reciprocal Li coordinate is bounded by the same constant at high
nontrivial zeros. -/
theorem norm_zetaLiCoordinate_inv_le_three_halves
    {ρ : ℂ} (hρ : IsNontrivialZetaZero ρ) (him : 2 ≤ |ρ.im|) :
    ‖(zetaLiCoordinate ρ)⁻¹‖ ≤ 3 / 2 := by
  have hρnorm : 2 ≤ ‖ρ‖ := two_le_norm_of_two_le_abs_im him
  have hsub : 2 ≤ ‖ρ - 1‖ := by
    calc
      2 ≤ |(ρ - 1).im| := by simpa using him
      _ ≤ ‖ρ - 1‖ := Complex.abs_im_le_norm _
  have hρ0 : ρ ≠ 0 := norm_ne_zero_iff.mp (by linarith)
  have hρ1 : ρ - 1 ≠ 0 := norm_ne_zero_iff.mp (by linarith)
  have hratio : (zetaLiCoordinate ρ)⁻¹ = ρ / (ρ - 1) := by
    unfold zetaLiCoordinate
    field_simp [hρ0, hρ1]
  rw [hratio, norm_div]
  have htri : ‖ρ‖ ≤ ‖ρ - 1‖ + 1 := by
    calc
      ‖ρ‖ = ‖(ρ - 1) + 1‖ := by ring_nf
      _ ≤ ‖ρ - 1‖ + ‖(1 : ℂ)‖ := norm_add_le _ _
      _ = ‖ρ - 1‖ + 1 := by norm_num
  have hpos : 0 < ‖ρ - 1‖ := by linarith
  apply (div_le_iff₀ hpos).2
  nlinarith

/-- The reciprocal coordinate `q+q⁻¹` stays in the disk of radius three. -/
theorem norm_zeta_reciprocal_coordinate_le_three
    {ρ : ℂ} (hρ : IsNontrivialZetaZero ρ) (him : 2 ≤ |ρ.im|) :
    ‖zetaLiCoordinate ρ + (zetaLiCoordinate ρ)⁻¹‖ ≤ 3 := by
  calc
    _ ≤ ‖zetaLiCoordinate ρ‖ + ‖(zetaLiCoordinate ρ)⁻¹‖ := norm_add_le _ _
    _ ≤ 3 := by
      linarith [norm_zetaLiCoordinate_le_three_halves him,
        norm_zetaLiCoordinate_inv_le_three_halves hρ him]

/-- Uniform bound for an arbitrary fixed finite conjugate-pair annihilator. -/
theorem norm_finiteConjugatePairAnnihilator_le
    (competitors : Finset ℂ) {u : ℂ} (hu : ‖u‖ ≤ 3) :
    ‖finiteConjugatePairAnnihilator competitors u‖ ≤
      ∏ v ∈ competitors, (3 + ‖v‖) ^ 2 := by
  unfold finiteConjugatePairAnnihilator
  rw [norm_prod]
  apply Finset.prod_le_prod
  · intro v hv
    positivity
  · intro v hv
    rw [norm_mul]
    have h₁ : ‖u - v‖ ≤ 3 + ‖v‖ := by
      linarith [norm_sub_le u v]
    have h₂ : ‖u - conj v‖ ≤ 3 + ‖v‖ := by
      calc
        ‖u - conj v‖ ≤ ‖u‖ + ‖conj v‖ := norm_sub_le _ _
        _ = ‖u‖ + ‖v‖ := by simp
        _ ≤ 3 + ‖v‖ := by linarith
    rw [pow_two]
    exact mul_le_mul h₁ h₂ (norm_nonneg _) (by positivity)

/-- Uniform bound for the seed polynomial on the high-zero Li disk. -/
theorem norm_liToeplitz_seed_le
    {q a : ℂ} (hq : ‖q‖ ≤ 3 / 2) :
    ‖q ^ 2 - a * q + 1‖ ≤
      (3 / 2 : ℝ) ^ 2 + ‖a‖ * (3 / 2 : ℝ) + 1 := by
  calc
    ‖q ^ 2 - a * q + 1‖ ≤ ‖q ^ 2 - a * q‖ + 1 := by
      simpa using norm_add_le (q ^ 2 - a * q) (1 : ℂ)
    _ ≤ (‖q ^ 2‖ + ‖a * q‖) + 1 := by
      gcongr
      exact norm_sub_le _ _
    _ = ‖q‖ ^ 2 + ‖a‖ * ‖q‖ + 1 := by rw [norm_pow, norm_mul]
    _ ≤ (3 / 2 : ℝ) ^ 2 + ‖a‖ * (3 / 2 : ℝ) + 1 := by
      gcongr

/-- Uniform bound for the sparse oscillatory factor. -/
theorem norm_one_add_even_pow_le
    {q : ℂ} (mode : ℕ) (hq : ‖q‖ ≤ 3 / 2) :
    ‖1 + q ^ (2 * mode)‖ ≤ 1 + (3 / 2 : ℝ) ^ (2 * mode) := by
  calc
    ‖1 + q ^ (2 * mode)‖ ≤ 1 + ‖q ^ (2 * mode)‖ := by
      simpa using norm_add_le (1 : ℂ) (q ^ (2 * mode))
    _ = 1 + ‖q‖ ^ (2 * mode) := by rw [norm_pow]
    _ ≤ _ := by
      gcongr

/-- The complete localized amplifier is bounded by a fixed constant times
`‖ρ‖⁻⁴`. -/
theorem norm_localizedZetaAmplifier_le
    (competitors : Finset ℂ) (a : ℂ) (mode : ℕ)
    {ρ : ℂ} (hρ : IsNontrivialZetaZero ρ) (him : 2 ≤ |ρ.im|) :
    ‖localizedZetaAmplifier competitors a mode ρ‖ ≤
      localizedZetaAmplifierConstant competitors a mode / ‖ρ‖ ^ 4 := by
  let q := zetaLiCoordinate ρ
  have hq : ‖q‖ ≤ 3 / 2 := norm_zetaLiCoordinate_le_three_halves him
  have hu : ‖q + q⁻¹‖ ≤ 3 := norm_zeta_reciprocal_coordinate_le_three hρ him
  have hρnorm : 0 < ‖ρ‖ := by linarith [two_le_norm_of_two_le_abs_im him]
  have hdamp : ‖(1 - q) ^ (2 * 2)‖ = 1 / ‖ρ‖ ^ 4 := by
    have hρ0 : ρ ≠ 0 := norm_ne_zero_iff.mp hρnorm.ne'
    change ‖(1 - (1 - ρ⁻¹)) ^ 4‖ = _
    rw [show 1 - (1 - ρ⁻¹) = ρ⁻¹ by ring, norm_pow, norm_inv]
    field_simp
  unfold localizedZetaAmplifier liToeplitzAmplifier
  dsimp only
  rw [norm_mul, norm_mul, norm_mul, hdamp]
  have hseed := norm_liToeplitz_seed_le (a := a) hq
  have hosc := norm_one_add_even_pow_le mode hq
  have hann := norm_finiteConjugatePairAnnihilator_le competitors hu
  unfold localizedZetaAmplifierConstant
  have hden : 0 ≤ 1 / ‖ρ‖ ^ 4 := by positivity
  calc
    ‖q ^ 2 - a * q + 1‖ * (1 / ‖ρ‖ ^ 4) *
          ‖1 + q ^ (2 * mode)‖ *
          ‖finiteConjugatePairAnnihilator competitors (q + q⁻¹)‖
        ≤ (((3 / 2 : ℝ) ^ 2 + ‖a‖ * (3 / 2 : ℝ) + 1) *
            (1 / ‖ρ‖ ^ 4) *
            (1 + (3 / 2 : ℝ) ^ (2 * mode))) *
            (∏ v ∈ competitors, (3 + ‖v‖) ^ 2) := by
          gcongr
    _ = ((((3 / 2 : ℝ) ^ 2 + ‖a‖ * (3 / 2 : ℝ) + 1) *
            (1 + (3 / 2 : ℝ) ^ (2 * mode))) *
            ∏ v ∈ competitors, (3 + ‖v‖) ^ 2) / ‖ρ‖ ^ 4 := by ring

/-! ## Summability of the actual localized divisor -/

/-- Multiplicity-weighted localized amplitude on the positive shell model. -/
noncomputable def positiveLocalizedZetaAmplifierWeight
    (competitors : Finset ℂ) (a : ℂ) (mode : ℕ)
    (i : PositiveHighZetaShellIndex) : ℝ :=
  analyticOrderNatAt riemannXiEntire i.2.1 *
    ‖localizedZetaAmplifier competitors a mode i.2.1‖

/-- On each positive shell, the actual amplifier weight is bounded by the
verified fourth-power envelope times one fixed constant. -/
theorem positiveLocalizedZetaAmplifierWeight_le
    (competitors : Finset ℂ) (a : ℂ) (mode : ℕ)
    (i : PositiveHighZetaShellIndex) :
    positiveLocalizedZetaAmplifierWeight competitors a mode i ≤
      localizedZetaAmplifierConstant competitors a mode *
        positiveHighZetaDampedMass i := by
  have hmem := mem_positiveUnitZetaShellFinset.mp i.2.property
  have hzero : IsNontrivialZetaZero i.2.1 := hmem.1
  have him0 : 0 ≤ i.2.1.im := by
    have : (2 : ℝ) ≤ i.2.1.im := by
      have hn : (0 : ℝ) ≤ i.1 := Nat.cast_nonneg _
      linarith [hmem.2.1]
    linarith
  have him : 2 ≤ |i.2.1.im| := by
    rw [abs_of_nonneg him0]
    have : (2 : ℝ) ≤ i.2.1.im := by
      have hn : (0 : ℝ) ≤ i.1 := Nat.cast_nonneg _
      linarith [hmem.2.1]
    exact this
  have hshellNorm : (((i.1 + 1 : ℕ) : ℝ)) ≤ ‖i.2.1‖ := by
    calc
      (((i.1 + 1 : ℕ) : ℝ)) ≤ (i.1 : ℝ) + 2 := by push_cast; linarith
      _ ≤ i.2.1.im := by exact_mod_cast hmem.2.1
      _ = |i.2.1.im| := (abs_of_nonneg him0).symm
      _ ≤ ‖i.2.1‖ := Complex.abs_im_le_norm _
  have hamp := norm_localizedZetaAmplifier_le competitors a mode hzero him
  have hC := localizedZetaAmplifierConstant_nonneg competitors a mode
  have hdenSmall : 0 < (((i.1 + 1 : ℕ) : ℝ) ^ 4) := by positivity
  have hpow : (((i.1 + 1 : ℕ) : ℝ) ^ 4) ≤ ‖i.2.1‖ ^ 4 :=
    pow_le_pow_left₀ (by positivity) hshellNorm 4
  have hdiv : localizedZetaAmplifierConstant competitors a mode / ‖i.2.1‖ ^ 4 ≤
      localizedZetaAmplifierConstant competitors a mode /
        (((i.1 + 1 : ℕ) : ℝ) ^ 4) :=
    div_le_div_of_nonneg_left hC hdenSmall hpow
  unfold positiveLocalizedZetaAmplifierWeight positiveHighZetaDampedMass
  calc
    (analyticOrderNatAt riemannXiEntire i.2.1 : ℝ) *
          ‖localizedZetaAmplifier competitors a mode i.2.1‖
      ≤ (analyticOrderNatAt riemannXiEntire i.2.1 : ℝ) *
          (localizedZetaAmplifierConstant competitors a mode /
            (((i.1 + 1 : ℕ) : ℝ) ^ 4)) := by
        gcongr
        exact hamp.trans hdiv
    _ = localizedZetaAmplifierConstant competitors a mode *
          ((analyticOrderNatAt riemannXiEntire i.2.1 : ℝ) /
            (((i.1 + 1 : ℕ) : ℝ) ^ 4)) := by ring

/-- Every fixed finite spectral amplifier is summable over the complete
positive-height multiplicity divisor. -/
theorem summable_positiveLocalizedZetaAmplifierWeight
    (competitors : Finset ℂ) (a : ℂ) (mode : ℕ) :
    Summable (positiveLocalizedZetaAmplifierWeight competitors a mode) := by
  apply (summable_positiveHighZetaDampedMass.mul_left
    (localizedZetaAmplifierConstant competitors a mode)).of_nonneg_of_le
  · intro i
    exact mul_nonneg (Nat.cast_nonneg _) (norm_nonneg _)
  · exact positiveLocalizedZetaAmplifierWeight_le competitors a mode

/-- Multiplicity-weighted localized amplitude on the reflected negative
shell model. -/
noncomputable def negativeLocalizedZetaAmplifierWeight
    (competitors : Finset ℂ) (a : ℂ) (mode : ℕ)
    (i : NegativeHighZetaShellIndex) : ℝ :=
  analyticOrderNatAt riemannZeta (1 - i.2.1) *
    ‖localizedZetaAmplifier competitors a mode (1 - i.2.1)‖

/-- Every fixed finite spectral amplifier is summable over the complete
negative-height multiplicity divisor as well. -/
theorem summable_negativeLocalizedZetaAmplifierWeight
    (competitors : Finset ℂ) (a : ℂ) (mode : ℕ) :
    Summable (negativeLocalizedZetaAmplifierWeight competitors a mode) := by
  have hpoint : ∀ i,
      negativeLocalizedZetaAmplifierWeight competitors a mode i ≤
        localizedZetaAmplifierConstant competitors a mode *
          negativeHighZetaDampedMass i := by
    intro i
    have hmem := mem_positiveUnitZetaShellFinset.mp i.2.property
    have hposzero : IsNontrivialZetaZero i.2.1 := hmem.1
    have hnegzero : IsNontrivialZetaZero (1 - i.2.1) := hposzero.one_sub
    have himpos : 2 ≤ i.2.1.im := by
      have hn : (0 : ℝ) ≤ i.1 := Nat.cast_nonneg _
      linarith [hmem.2.1]
    have him : 2 ≤ |(1 - i.2.1).im| := by
      simp
      rw [abs_of_nonneg (by linarith : 0 ≤ i.2.1.im)]
      exact himpos
    have hshellNorm : (((i.1 + 1 : ℕ) : ℝ)) ≤ ‖1 - i.2.1‖ := by
      calc
        (((i.1 + 1 : ℕ) : ℝ)) ≤ (i.1 : ℝ) + 2 := by push_cast; linarith
        _ ≤ i.2.1.im := by exact_mod_cast hmem.2.1
        _ = |(1 - i.2.1).im| := by simp [abs_of_nonneg (by linarith : 0 ≤ i.2.1.im)]
        _ ≤ ‖1 - i.2.1‖ := Complex.abs_im_le_norm _
    have hamp := norm_localizedZetaAmplifier_le competitors a mode hnegzero him
    have hC := localizedZetaAmplifierConstant_nonneg competitors a mode
    have hdenSmall : 0 < (((i.1 + 1 : ℕ) : ℝ) ^ 4) := by positivity
    have hpow : (((i.1 + 1 : ℕ) : ℝ) ^ 4) ≤ ‖1 - i.2.1‖ ^ 4 :=
      pow_le_pow_left₀ (by positivity) hshellNorm 4
    have hdiv := div_le_div_of_nonneg_left hC hdenSmall hpow
    unfold negativeLocalizedZetaAmplifierWeight negativeHighZetaDampedMass
    calc
      (analyticOrderNatAt riemannZeta (1 - i.2.1) : ℝ) *
            ‖localizedZetaAmplifier competitors a mode (1 - i.2.1)‖
        ≤ (analyticOrderNatAt riemannZeta (1 - i.2.1) : ℝ) *
            (localizedZetaAmplifierConstant competitors a mode /
              (((i.1 + 1 : ℕ) : ℝ) ^ 4)) := by
          gcongr
          exact hamp.trans hdiv
      _ = localizedZetaAmplifierConstant competitors a mode *
            ((analyticOrderNatAt riemannZeta (1 - i.2.1) : ℝ) /
              (((i.1 + 1 : ℕ) : ℝ) ^ 4)) := by ring
  apply (summable_negativeHighZetaDampedMass.mul_left
    (localizedZetaAmplifierConstant competitors a mode)).of_nonneg_of_le
  · intro i
    exact mul_nonneg (Nat.cast_nonneg _) (norm_nonneg _)
  · exact hpoint

/-! ## Reindexing onto the actual zero subtype -/

def PositiveHighNontrivialZetaZeroPoint :=
  {ρ : NontrivialZetaZeroPoint // 2 ≤ ρ.1.im}

def NegativeHighNontrivialZetaZeroPoint :=
  {ρ : NontrivialZetaZeroPoint // ρ.1.im ≤ -2}

/-- The shell union is exactly the actual positive-height zero subtype. -/
noncomputable def positiveHighZetaShellEquiv :
    PositiveHighZetaShellIndex ≃ PositiveHighNontrivialZetaZeroPoint := by
  let f : PositiveHighZetaShellIndex → PositiveHighNontrivialZetaZeroPoint :=
    fun i ↦ ⟨⟨i.2.1, (mem_positiveUnitZetaShellFinset.mp i.2.property).1⟩, by
      have hmem := (mem_positiveUnitZetaShellFinset.mp i.2.property).2.1
      have hn : (0 : ℝ) ≤ i.1 := Nat.cast_nonneg _
      linarith⟩
  apply Equiv.ofBijective f
  constructor
  · rintro ⟨n, i⟩ ⟨m, j⟩ hij
    have hρ : i.1 = j.1 := congrArg (fun z ↦ z.1.1) hij
    have hindex : n = m := by
      apply positiveUnitZetaShellFinset_index_unique i.property
      simpa [hρ] using j.property
    subst m
    simp_all
  · intro ρ
    obtain ⟨n, hn⟩ := exists_mem_positiveUnitZetaShellFinset ρ.1.2 ρ.2
    refine ⟨⟨n, ⟨ρ.1.1, hn⟩⟩, ?_⟩
    apply Subtype.ext
    rfl

/-- Reflection identifies the transported shell union with the actual
negative-height zero subtype. -/
noncomputable def negativeHighZetaShellEquiv :
    NegativeHighZetaShellIndex ≃ NegativeHighNontrivialZetaZeroPoint := by
  let f : NegativeHighZetaShellIndex → NegativeHighNontrivialZetaZeroPoint :=
    fun i ↦ ⟨⟨1 - i.2.1,
      (mem_positiveUnitZetaShellFinset.mp i.2.property).1.one_sub⟩, by
        have hmem := (mem_positiveUnitZetaShellFinset.mp i.2.property).2.1
        have hn : (0 : ℝ) ≤ i.1 := Nat.cast_nonneg _
        simp
        linarith⟩
  apply Equiv.ofBijective f
  constructor
  · rintro ⟨n, i⟩ ⟨m, j⟩ hij
    have hρ : 1 - i.1 = 1 - j.1 := congrArg (fun z ↦ z.1.1) hij
    have hbase : i.1 = j.1 := sub_right_inj.mp hρ
    have hindex : n = m := by
      apply positiveUnitZetaShellFinset_index_unique i.property
      simpa [hbase] using j.property
    subst m
    simp_all
  · intro ρ
    obtain ⟨n, hn⟩ := exists_mem_reflected_negativeZetaShell ρ.1.2 ρ.2
    refine ⟨⟨n, ⟨1 - ρ.1.1, hn⟩⟩, ?_⟩
    apply Subtype.ext
    apply Subtype.ext
    ring

@[simp]
theorem positiveHighZetaShellEquiv_apply_value
    (i : PositiveHighZetaShellIndex) :
    (positiveHighZetaShellEquiv i).1.1 = i.2.1 := by
  rfl

@[simp]
theorem negativeHighZetaShellEquiv_apply_value
    (i : NegativeHighZetaShellIndex) :
    (negativeHighZetaShellEquiv i).1.1 = 1 - i.2.1 := by
  rfl

/-- The concrete finite amplifier has a globally summable,
multiplicity-weighted norm on the complete actual nontrivial zeta divisor. -/
theorem summable_actual_localizedZetaAmplifier
    (competitors : Finset ℂ) (a : ℂ) (mode : ℕ) :
    Summable (zetaModeWeight
      (fun ρ ↦ localizedZetaAmplifier competitors a mode ρ.1)) := by
  let amplitude : NontrivialZetaZeroPoint → ℂ :=
    fun ρ ↦ localizedZetaAmplifier competitors a mode ρ.1
  have hpos : Summable (fun ρ : PositiveHighNontrivialZetaZeroPoint ↦
      zetaModeWeight amplitude ρ.1) := by
    apply positiveHighZetaShellEquiv.summable_iff.mp
    apply (summable_positiveLocalizedZetaAmplifierWeight competitors a mode).congr
    intro i
    have hzero : IsNontrivialZetaZero i.2.1 :=
      (mem_positiveUnitZetaShellFinset.mp i.2.property).1
    simp only [Function.comp_apply, amplitude, zetaModeWeight,
      zetaZeroMultiplicity, positiveHighZetaShellEquiv_apply_value,
      positiveLocalizedZetaAmplifierWeight]
    rw [← hzero.xiMultiplicity_eq_zetaMultiplicity]
  have hneg : Summable (fun ρ : NegativeHighNontrivialZetaZeroPoint ↦
      zetaModeWeight amplitude ρ.1) := by
    apply negativeHighZetaShellEquiv.summable_iff.mp
    apply (summable_negativeLocalizedZetaAmplifierWeight competitors a mode).congr
    intro i
    simp only [Function.comp_apply, amplitude, zetaModeWeight,
      zetaZeroMultiplicity, negativeHighZetaShellEquiv_apply_value,
      negativeLocalizedZetaAmplifierWeight]
  have hlow : Summable
      (fun ρ : {z : NontrivialZetaZeroPoint | |z.1.im| < 2} ↦
        zetaModeWeight amplitude ρ.1) :=
    summable_on_lowHeightNontrivialZetaZeros amplitude
  let region : Fin 3 → Set NontrivialZetaZeroPoint
    | ⟨0, _⟩ => {ρ | 2 ≤ ρ.1.im}
    | ⟨1, _⟩ => {ρ | ρ.1.im ≤ -2}
    | ⟨2, _⟩ => {ρ | |ρ.1.im| < 2}
  have hpartition : ∀ ρ, ∃! j, ρ ∈ region j := by
    intro ρ
    by_cases hp : 2 ≤ ρ.1.im
    · refine ⟨⟨0, by omega⟩, hp, ?_⟩
      intro j hj
      fin_cases j <;> simp_all [region, abs_lt] <;> linarith
    · by_cases hn : ρ.1.im ≤ -2
      · refine ⟨⟨1, by omega⟩, hn, ?_⟩
        intro j hj
        fin_cases j <;> simp_all [region, abs_lt] <;> linarith
      · have hl : |ρ.1.im| < 2 := by
          rw [abs_lt]
          constructor <;> linarith
        refine ⟨⟨2, by omega⟩, hl, ?_⟩
        intro j hj
        fin_cases j <;> simp_all [region, abs_lt] <;> linarith
  apply (summable_partition (f := zetaModeWeight amplitude)
    (fun ρ ↦ zetaModeWeight_nonneg amplitude ρ) hpartition).2
  constructor
  · intro j
    fin_cases j
    · change Summable (fun ρ : PositiveHighNontrivialZetaZeroPoint ↦
        zetaModeWeight amplitude ρ.1)
      exact hpos
    · change Summable (fun ρ : NegativeHighNontrivialZetaZeroPoint ↦
        zetaModeWeight amplitude ρ.1)
      exact hneg
    · change Summable
        (fun ρ : {z : NontrivialZetaZeroPoint | |z.1.im| < 2} ↦
          zetaModeWeight amplitude ρ.1)
      exact hlow
  · exact Summable.of_finite

/-- Under RH failure, the now-verified concrete finite amplifier satisfies
the complete summability hypothesis required for exponential domination of
the actual infinite zeta tail. -/
theorem not_rh_localizedZetaAmplifier_tail_dominated
    (hRH : ¬RiemannHypothesis) (competitors : Finset ℂ)
    (a : ℂ) (mode : ℕ) :
    ∃ target : NontrivialZetaZeroPoint, ∃ r : ℝ,
      1 < r ∧ r < zetaLiRate target ∧
      {z : ℂ | IsNontrivialZetaZero z ∧ r ≤ ‖1 - z⁻¹‖}.Finite ∧
      ∀ A : ℝ, 0 < A →
        ∀ᶠ n : ℕ in Filter.atTop,
          ∑' ρ : SubdominantZetaZeroPoints r,
              zetaModeWeight
                (fun z ↦ localizedZetaAmplifier competitors a mode z.1) ρ.1 *
                zetaLiRate ρ.1 ^ n <
            A * zetaLiRate target ^ n := by
  obtain ⟨target, r, hr, hrt, hfinite, htail⟩ :=
    not_rh_actual_zeta_tail_reduction hRH
  refine ⟨target, r, hr, hrt, hfinite, ?_⟩
  intro A hA
  exact htail _ A
    (summable_actual_localizedZetaAmplifier competitors a mode) hA

end RiemannLab
