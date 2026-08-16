import RiemannLab.Tasks.ZetaMultiplicityExpandedDivisor

namespace RiemannLab

open Filter Set

/-!
# Uniform genus-one products on compact disks

The global quadratic-exponential factor estimate and inverse-square divisor
summability are combined here through Mathlib's uniform infinite-product
theorem.
-/

/-- A generic genus-one product is uniformly multipliable on every closed
disk when its nonzero divisor is inverse-square summable and bounded away
from the origin. -/
theorem multipliableUniformlyOn_zetaGenusOneFactor_closedBall
    {ι : Type*} (ρ : ι → ℂ)
    (hρ0 : ∀ i, ρ i ≠ 0)
    (hρnorm : ∀ i, 1 ≤ ‖ρ i‖)
    (hsum : Summable (fun i ↦ 1 / ‖ρ i‖ ^ 2))
    {R : ℝ} (hR : 0 ≤ R) :
    MultipliableUniformlyOn
      (fun i z ↦ zetaGenusOneFactor (ρ i) z)
      (Metric.closedBall (0 : ℂ) R) := by
  let C : ℝ := 2 * R ^ 2 * Real.exp R
  have hC : 0 ≤ C := by positivity
  have hsumC : Summable (fun i ↦ C * (1 / ‖ρ i‖ ^ 2)) :=
    hsum.mul_left C
  have hmajorant : ∀ i, ∀ z ∈ Metric.closedBall (0 : ℂ) R,
      ‖zetaGenusOneFactor (ρ i) z - 1‖ ≤
        C * (1 / ‖ρ i‖ ^ 2) := by
    intro i z hz
    have hzR : ‖z‖ ≤ R := by
      simpa [Metric.mem_closedBall] using hz
    have hq : 0 < ‖ρ i‖ := norm_pos_iff.mpr (hρ0 i)
    have hwdiv : ‖z / ρ i‖ ≤ R / ‖ρ i‖ := by
      rw [norm_div]
      exact div_le_div_of_nonneg_right hzR hq.le
    have hRdiv : R / ‖ρ i‖ ≤ R := by
      exact div_le_self hR (hρnorm i)
    have hwR : ‖z / ρ i‖ ≤ R := hwdiv.trans hRdiv
    have hsquare : ‖z / ρ i‖ ^ 2 ≤ (R / ‖ρ i‖) ^ 2 :=
      pow_le_pow_left₀ (norm_nonneg _) hwdiv 2
    have hexp : Real.exp ‖z / ρ i‖ ≤ Real.exp R :=
      Real.exp_le_exp.mpr hwR
    calc
      ‖zetaGenusOneFactor (ρ i) z - 1‖ ≤
          2 * ‖z / ρ i‖ ^ 2 * Real.exp ‖z / ρ i‖ :=
        norm_zetaGenusOneFactor_sub_one_le_global
      _ ≤ 2 * (R / ‖ρ i‖) ^ 2 * Real.exp R := by
        gcongr
      _ = C * (1 / ‖ρ i‖ ^ 2) := by
        unfold C
        field_simp
  have hprod := Summable.multipliableUniformlyOn_one_add
    (f := fun i z ↦ zetaGenusOneFactor (ρ i) z - 1)
    (u := fun i ↦ C * (1 / ‖ρ i‖ ^ 2))
    (isCompact_closedBall (0 : ℂ) R) hsumC
    (Filter.Eventually.of_forall hmajorant)
    (fun i ↦ (continuous_iff_continuousAt.mpr fun z ↦
      (zetaGenusOneFactor_analytic (ρ i) z).continuousAt).continuousOn.sub
        continuousOn_const)
  have heq : (fun i z ↦ 1 + (zetaGenusOneFactor (ρ i) z - 1)) =
      (fun i z ↦ zetaGenusOneFactor (ρ i) z) := by
    funext i z
    ring
  rw [← heq]
  exact hprod

/-- Pointwise absolute control of the factor defects.  This is the
nonvanishing input that rules out phantom zeros in the infinite product. -/
theorem summable_norm_zetaGenusOneFactor_sub_one
    {ι : Type*} (ρ : ι → ℂ)
    (hρ0 : ∀ i, ρ i ≠ 0)
    (hρnorm : ∀ i, 1 ≤ ‖ρ i‖)
    (hsum : Summable (fun i ↦ 1 / ‖ρ i‖ ^ 2))
    (z : ℂ) :
    Summable (fun i ↦ ‖zetaGenusOneFactor (ρ i) z - 1‖) := by
  let R : ℝ := ‖z‖
  let C : ℝ := 2 * R ^ 2 * Real.exp R
  have hsumC : Summable (fun i ↦ C * (1 / ‖ρ i‖ ^ 2)) :=
    hsum.mul_left C
  apply hsumC.of_nonneg_of_le
  · intro i
    positivity
  · intro i
    have hq : 0 < ‖ρ i‖ := norm_pos_iff.mpr (hρ0 i)
    have hwdiv : ‖z / ρ i‖ ≤ R / ‖ρ i‖ := by
      rw [norm_div]
    have hRdiv : R / ‖ρ i‖ ≤ R := by
      exact div_le_self (norm_nonneg z) (hρnorm i)
    have hwR : ‖z / ρ i‖ ≤ R := hwdiv.trans hRdiv
    have hsquare : ‖z / ρ i‖ ^ 2 ≤ (R / ‖ρ i‖) ^ 2 :=
      pow_le_pow_left₀ (norm_nonneg _) hwdiv 2
    have hexp : Real.exp ‖z / ρ i‖ ≤ Real.exp R :=
      Real.exp_le_exp.mpr hwR
    calc
      ‖zetaGenusOneFactor (ρ i) z - 1‖ ≤
          2 * ‖z / ρ i‖ ^ 2 * Real.exp ‖z / ρ i‖ :=
        norm_zetaGenusOneFactor_sub_one_le_global
      _ ≤ 2 * (R / ‖ρ i‖) ^ 2 * Real.exp R := by
        gcongr
      _ = C * (1 / ‖ρ i‖ ^ 2) := by
        unfold C
        field_simp

/-- An inverse-square controlled genus-one product has no zeros beyond its
literal factor zeros. -/
theorem tprod_zetaGenusOneFactor_eq_zero_iff
    {ι : Type*} (ρ : ι → ℂ)
    (hρ0 : ∀ i, ρ i ≠ 0)
    (hρnorm : ∀ i, 1 ≤ ‖ρ i‖)
    (hsum : Summable (fun i ↦ 1 / ‖ρ i‖ ^ 2))
    (z : ℂ) :
    (∏' i, zetaGenusOneFactor (ρ i) z) = 0 ↔ ∃ i, ρ i = z := by
  constructor
  · intro hzero
    by_contra hnone
    push_neg at hnone
    have hfactor : ∀ i, zetaGenusOneFactor (ρ i) z ≠ 0 := by
      intro i
      exact (zetaGenusOneFactor_eq_zero_iff (hρ0 i)).not.mpr (Ne.symm (hnone i))
    have hsumNorm := summable_norm_zetaGenusOneFactor_sub_one
      ρ hρ0 hρnorm hsum z
    have htprod : (∏' i, zetaGenusOneFactor (ρ i) z) ≠ 0 := by
      have h := tprod_one_add_ne_zero_of_summable
        (f := fun i ↦ zetaGenusOneFactor (ρ i) z - 1)
        (fun i ↦ by
          intro h
          apply hfactor i
          calc
            zetaGenusOneFactor (ρ i) z =
                1 + (zetaGenusOneFactor (ρ i) z - 1) := by ring
            _ = 0 := h)
        hsumNorm
      have heq : (fun i ↦ 1 + (zetaGenusOneFactor (ρ i) z - 1)) =
          (fun i ↦ zetaGenusOneFactor (ρ i) z) := by
        funext i
        ring
      simpa only [heq] using h
    exact htprod hzero
  · rintro ⟨i, hi⟩
    apply tprod_of_exists_eq_zero
    refine ⟨i, ?_⟩
    exact (zetaGenusOneFactor_eq_zero_iff (hρ0 i)).2 hi.symm

/-- The complete multiplicity-expanded positive zeta tail defines a uniform
canonical product on every closed disk. -/
theorem multipliableUniformlyOn_positiveZetaGenusOneTail
    {R : ℝ} (hR : 0 ≤ R) :
    MultipliableUniformlyOn
      (fun j z ↦ zetaGenusOneFactor (positiveHighZetaFactorPoint j) z)
      (Metric.closedBall (0 : ℂ) R) := by
  apply multipliableUniformlyOn_zetaGenusOneFactor_closedBall
    positiveHighZetaFactorPoint positiveHighZetaFactorPoint_ne_zero
  · intro j
    exact le_trans (by norm_num) (positiveHighZetaFactor_shell_le_norm j)
  · exact summable_positiveHighZetaFactor_inverseSquare
  · exact hR

/-- The reflected multiplicity-expanded negative zeta tail likewise defines
a uniform canonical product on every closed disk. -/
theorem multipliableUniformlyOn_negativeZetaGenusOneTail
    {R : ℝ} (hR : 0 ≤ R) :
    MultipliableUniformlyOn
      (fun j z ↦ zetaGenusOneFactor (negativeHighZetaFactorPoint j) z)
      (Metric.closedBall (0 : ℂ) R) := by
  apply multipliableUniformlyOn_zetaGenusOneFactor_closedBall
    negativeHighZetaFactorPoint negativeHighZetaFactorPoint_ne_zero
  · intro j
    exact le_trans (by norm_num) (negativeHighZetaFactor_shell_le_norm j)
  · exact summable_negativeHighZetaFactor_inverseSquare
  · exact hR

/-! ## Global locally uniform tail products -/

/-- The actual infinite product over the positive multiplicity-expanded
tail. -/
noncomputable def positiveZetaGenusOneTailProduct (z : ℂ) : ℂ :=
  ∏' j : PositiveHighZetaFactorIndex,
    zetaGenusOneFactor (positiveHighZetaFactorPoint j) z

/-- The positive infinite product has no phantom zeros. -/
theorem positiveZetaGenusOneTailProduct_eq_zero_iff (z : ℂ) :
    positiveZetaGenusOneTailProduct z = 0 ↔
      ∃ j : PositiveHighZetaFactorIndex,
        positiveHighZetaFactorPoint j = z := by
  unfold positiveZetaGenusOneTailProduct
  exact tprod_zetaGenusOneFactor_eq_zero_iff
    positiveHighZetaFactorPoint positiveHighZetaFactorPoint_ne_zero
    (fun j ↦ le_trans (by norm_num) (positiveHighZetaFactor_shell_le_norm j))
    summable_positiveHighZetaFactor_inverseSquare z

/-- The positive canonical tail converges locally uniformly on the entire
complex plane. -/
theorem hasProdLocallyUniformlyOn_positiveZetaGenusOneTail :
    HasProdLocallyUniformlyOn
      (fun j z ↦ zetaGenusOneFactor (positiveHighZetaFactorPoint j) z)
      positiveZetaGenusOneTailProduct Set.univ := by
  apply hasProdLocallyUniformlyOn_of_forall_compact isOpen_univ
  intro K _ hK
  obtain ⟨R, hR, hKR⟩ := hK.isBounded.subset_closedBall_lt 0 (0 : ℝ)
  have hball := (multipliableUniformlyOn_positiveZetaGenusOneTail hR.le).hasProdUniformlyOn
  exact hball.mono hKR

/-- The actual infinite product over the reflected negative
multiplicity-expanded tail. -/
noncomputable def negativeZetaGenusOneTailProduct (z : ℂ) : ℂ :=
  ∏' j : NegativeHighZetaFactorIndex,
    zetaGenusOneFactor (negativeHighZetaFactorPoint j) z

/-- The reflected negative infinite product has no phantom zeros. -/
theorem negativeZetaGenusOneTailProduct_eq_zero_iff (z : ℂ) :
    negativeZetaGenusOneTailProduct z = 0 ↔
      ∃ j : NegativeHighZetaFactorIndex,
        negativeHighZetaFactorPoint j = z := by
  unfold negativeZetaGenusOneTailProduct
  exact tprod_zetaGenusOneFactor_eq_zero_iff
    negativeHighZetaFactorPoint negativeHighZetaFactorPoint_ne_zero
    (fun j ↦ le_trans (by norm_num) (negativeHighZetaFactor_shell_le_norm j))
    summable_negativeHighZetaFactor_inverseSquare z

/-- The reflected negative canonical tail converges locally uniformly on the
entire complex plane. -/
theorem hasProdLocallyUniformlyOn_negativeZetaGenusOneTail :
    HasProdLocallyUniformlyOn
      (fun j z ↦ zetaGenusOneFactor (negativeHighZetaFactorPoint j) z)
      negativeZetaGenusOneTailProduct Set.univ := by
  apply hasProdLocallyUniformlyOn_of_forall_compact isOpen_univ
  intro K _ hK
  obtain ⟨R, hR, hKR⟩ := hK.isBounded.subset_closedBall_lt 0 (0 : ℝ)
  have hball := (multipliableUniformlyOn_negativeZetaGenusOneTail hR.le).hasProdUniformlyOn
  exact hball.mono hKR

/-- The locally uniform positive tail product is entire. -/
theorem differentiable_positiveZetaGenusOneTailProduct :
    Differentiable ℂ positiveZetaGenusOneTailProduct := by
  have hdiff : DifferentiableOn ℂ positiveZetaGenusOneTailProduct Set.univ := by
    apply hasProdLocallyUniformlyOn_positiveZetaGenusOneTail.differentiableOn
    · exact Filter.Eventually.of_forall fun s ↦ by
        apply DifferentiableOn.fun_finsetProd
        intro i _
        exact fun z _ ↦
          (zetaGenusOneFactor_analytic (positiveHighZetaFactorPoint i) z).differentiableAt
            |>.differentiableWithinAt
    · exact isOpen_univ
  intro z
  exact (hdiff z (Set.mem_univ z)).differentiableAt univ_mem

/-- The locally uniform reflected negative tail product is entire. -/
theorem differentiable_negativeZetaGenusOneTailProduct :
    Differentiable ℂ negativeZetaGenusOneTailProduct := by
  have hdiff : DifferentiableOn ℂ negativeZetaGenusOneTailProduct Set.univ := by
    apply hasProdLocallyUniformlyOn_negativeZetaGenusOneTail.differentiableOn
    · exact Filter.Eventually.of_forall fun s ↦ by
        apply DifferentiableOn.fun_finsetProd
        intro i _
        exact fun z _ ↦
          (zetaGenusOneFactor_analytic (negativeHighZetaFactorPoint i) z).differentiableAt
            |>.differentiableWithinAt
    · exact isOpen_univ
  intro z
  exact (hdiff z (Set.mem_univ z)).differentiableAt univ_mem

/-! ## Finite centre and assembled canonical product -/

/-- The finite canonical product over the central zero block, with one factor
per unit of analytic multiplicity. -/
noncomputable def lowHeightZetaGenusOneProduct (z : ℂ) : ℂ :=
  ∏ j : LowHeightZetaFactorIndex,
    zetaGenusOneFactor (lowHeightZetaFactorPoint j) z

/-- The finite central product vanishes exactly at one of its literal factor
points. -/
theorem lowHeightZetaGenusOneProduct_eq_zero_iff (z : ℂ) :
    lowHeightZetaGenusOneProduct z = 0 ↔
      ∃ j : LowHeightZetaFactorIndex, lowHeightZetaFactorPoint j = z := by
  classical
  unfold lowHeightZetaGenusOneProduct
  rw [Finset.prod_eq_zero_iff]
  simp only [Finset.mem_univ, true_and]
  apply exists_congr
  intro j
  simpa only [eq_comm] using
    (zetaGenusOneFactor_eq_zero_iff (lowHeightZetaFactorPoint_ne_zero j) (z := z))

theorem differentiable_lowHeightZetaGenusOneProduct :
    Differentiable ℂ lowHeightZetaGenusOneProduct := by
  unfold lowHeightZetaGenusOneProduct
  apply Differentiable.fun_finsetProd
  intro i _ z
  exact (zetaGenusOneFactor_analytic (lowHeightZetaFactorPoint i) z).differentiableAt

/-- The complete genus-one canonical product assembled from the positive
tail, reflected negative tail, and finite central block. -/
noncomputable def completedZetaGenusOneProduct (z : ℂ) : ℂ :=
  positiveZetaGenusOneTailProduct z *
    negativeZetaGenusOneTailProduct z *
      lowHeightZetaGenusOneProduct z

/-- The assembled multiplicity-aware zeta canonical product is entire. -/
theorem differentiable_completedZetaGenusOneProduct :
    Differentiable ℂ completedZetaGenusOneProduct := by
  unfold completedZetaGenusOneProduct
  exact (differentiable_positiveZetaGenusOneTailProduct.mul
    differentiable_negativeZetaGenusOneTailProduct).mul
      differentiable_lowHeightZetaGenusOneProduct

/-- Exact zero-set ledger for the assembled product.  Multiplicity order is
the next theorem; this result already rules out every extraneous zero. -/
theorem completedZetaGenusOneProduct_eq_zero_iff (z : ℂ) :
    completedZetaGenusOneProduct z = 0 ↔
      (∃ j : PositiveHighZetaFactorIndex,
          positiveHighZetaFactorPoint j = z) ∨
      (∃ j : NegativeHighZetaFactorIndex,
          negativeHighZetaFactorPoint j = z) ∨
      (∃ j : LowHeightZetaFactorIndex,
          lowHeightZetaFactorPoint j = z) := by
  unfold completedZetaGenusOneProduct
  rw [mul_eq_zero, mul_eq_zero,
    positiveZetaGenusOneTailProduct_eq_zero_iff,
    negativeZetaGenusOneTailProduct_eq_zero_iff,
    lowHeightZetaGenusOneProduct_eq_zero_iff]
  tauto

/-- Every nontrivial zeta zero has strictly positive natural analytic
multiplicity. -/
theorem IsNontrivialZetaZero.zetaMultiplicity_pos {z : ℂ}
    (hz : IsNontrivialZetaZero z) :
    0 < analyticOrderNatAt riemannZeta z := by
  unfold analyticOrderNatAt
  apply ENat.toNat_pos
  · exact hz.analyticAt.analyticOrderAt_ne_zero.mpr hz.1
  · exact zetaZeroOrder_ne_top (by
      intro h
      subst z
      have hlt := hz.re_lt_one
      norm_num at hlt)

/-- A positive-height nontrivial zero occurs in the literal positive factor
index, including a certified multiplicity copy. -/
theorem exists_positiveHighZetaFactorPoint_eq
    {z : ℂ} (hz : IsNontrivialZetaZero z) (him : 2 ≤ z.im) :
    ∃ j : PositiveHighZetaFactorIndex, positiveHighZetaFactorPoint j = z := by
  obtain ⟨n, hn⟩ := exists_mem_positiveUnitZetaShellFinset hz him
  have hpos : 0 < analyticOrderNatAt riemannXiEntire z := by
    rw [hz.xiMultiplicity_eq_zetaMultiplicity]
    exact hz.zetaMultiplicity_pos
  exact ⟨⟨⟨n, ⟨z, hn⟩⟩, ⟨0, hpos⟩⟩, rfl⟩

/-- A negative-height nontrivial zero occurs in the literal reflected factor
index. -/
theorem exists_negativeHighZetaFactorPoint_eq
    {z : ℂ} (hz : IsNontrivialZetaZero z) (him : z.im ≤ -2) :
    ∃ j : NegativeHighZetaFactorIndex, negativeHighZetaFactorPoint j = z := by
  obtain ⟨n, hn⟩ := exists_mem_reflected_negativeZetaShell hz him
  have hpos : 0 < analyticOrderNatAt riemannZeta (1 - (1 - z)) := by
    simpa only [sub_sub_cancel] using hz.zetaMultiplicity_pos
  exact ⟨⟨⟨n, ⟨1 - z, hn⟩⟩, ⟨0, hpos⟩⟩, by
    simp [negativeHighZetaFactorPoint]⟩

/-- A central nontrivial zero occurs in the finite multiplicity-expanded
factor index. -/
theorem exists_lowHeightZetaFactorPoint_eq
    {z : ℂ} (hz : IsNontrivialZetaZero z) (him : |z.im| < 2) :
    ∃ j : LowHeightZetaFactorIndex, lowHeightZetaFactorPoint j = z := by
  have hpos : 0 < zetaZeroMultiplicity ⟨z, hz⟩ := by
    exact hz.zetaMultiplicity_pos
  exact ⟨⟨⟨⟨z, hz⟩, him⟩, ⟨0, hpos⟩⟩, rfl⟩

/-- The assembled canonical product has exactly the nontrivial zeta zero set.
This closes zero-set identification; equality of analytic orders is the
remaining divisor theorem. -/
theorem completedZetaGenusOneProduct_zero_iff_nontrivialZetaZero (z : ℂ) :
    completedZetaGenusOneProduct z = 0 ↔ IsNontrivialZetaZero z := by
  rw [completedZetaGenusOneProduct_eq_zero_iff]
  constructor
  · rintro (hpos | hneg | hlow)
    · obtain ⟨j, rfl⟩ := hpos
      exact (mem_positiveUnitZetaShellFinset.mp j.1.2.property).1
    · obtain ⟨j, rfl⟩ := hneg
      exact ((mem_positiveUnitZetaShellFinset.mp j.1.2.property).1).one_sub
    · obtain ⟨j, rfl⟩ := hlow
      exact j.1.1.property
  · intro hz
    by_cases hpos : 2 ≤ z.im
    · exact Or.inl (exists_positiveHighZetaFactorPoint_eq hz hpos)
    by_cases hneg : z.im ≤ -2
    · exact Or.inr (Or.inl (exists_negativeHighZetaFactorPoint_eq hz hneg))
    · have him : |z.im| < 2 := abs_lt.mpr ⟨by linarith, by linarith⟩
      exact Or.inr (Or.inr (exists_lowHeightZetaFactorPoint_eq hz him))

@[simp] theorem positiveZetaGenusOneTailProduct_zero :
    positiveZetaGenusOneTailProduct 0 = 1 := by
  unfold positiveZetaGenusOneTailProduct
  simp

@[simp] theorem negativeZetaGenusOneTailProduct_zero :
    negativeZetaGenusOneTailProduct 0 = 1 := by
  unfold negativeZetaGenusOneTailProduct
  simp

@[simp] theorem lowHeightZetaGenusOneProduct_zero :
    lowHeightZetaGenusOneProduct 0 = 1 := by
  unfold lowHeightZetaGenusOneProduct
  simp

@[simp] theorem completedZetaGenusOneProduct_zero :
    completedZetaGenusOneProduct 0 = 1 := by
  simp [completedZetaGenusOneProduct]

end RiemannLab
