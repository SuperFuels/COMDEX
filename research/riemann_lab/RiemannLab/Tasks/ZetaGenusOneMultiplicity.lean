import RiemannLab.Tasks.ZetaGenusOneUniformProduct
import RiemannLab.Tasks.ZetaAmplifierSummability

namespace RiemannLab

open Filter Set Complex

set_option maxHeartbeats 800000

/-!
# Multiplicity of a locally uniform genus-one product

This file isolates the reusable analytic theorem needed for the remaining
zeta-divisor calculation.  If a finite set contains exactly the factor
copies at a selected divisor point, then the order of the complete infinite
product at that point is the cardinality of that set.
-/

/-- The product over the complement of a finite collection of divisor
copies. -/
noncomputable def zetaGenusOneComplementProduct
    {ι : Type*} (ρ : ι → ℂ) (s : Finset ι) (z : ℂ) : ℂ :=
  ∏' i : ↥((↑s : Set ι)ᶜ), zetaGenusOneFactor (ρ i.1) z

/-- Removing finitely many copies preserves local uniform convergence of the
genus-one product. -/
theorem hasProdLocallyUniformlyOn_zetaGenusOneComplement
    {ι : Type*} (ρ : ι → ℂ) (s : Finset ι)
    (hρ0 : ∀ i, ρ i ≠ 0)
    (hρnorm : ∀ i, 1 ≤ ‖ρ i‖)
    (hsum : Summable (fun i ↦ 1 / ‖ρ i‖ ^ 2)) :
    HasProdLocallyUniformlyOn
      (fun (i : ↥((↑s : Set ι)ᶜ)) z ↦ zetaGenusOneFactor (ρ i.1) z)
      (zetaGenusOneComplementProduct ρ s) Set.univ := by
  apply hasProdLocallyUniformlyOn_of_forall_compact isOpen_univ
  intro K _ hK
  obtain ⟨R, hR, hKR⟩ := hK.isBounded.subset_closedBall_lt 0 (0 : ℝ)
  have hsum' : Summable
      (fun i : ↥((↑s : Set ι)ᶜ) ↦ 1 / ‖ρ i.1‖ ^ 2) :=
    hsum.comp_injective Subtype.coe_injective
  have hball :=
    (multipliableUniformlyOn_zetaGenusOneFactor_closedBall
      (fun i : ↥((↑s : Set ι)ᶜ) ↦ ρ i.1)
      (fun i ↦ hρ0 i.1) (fun i ↦ hρnorm i.1) hsum' hR.le).hasProdUniformlyOn
  exact hball.mono hKR

/-- The complementary product is entire. -/
theorem differentiable_zetaGenusOneComplementProduct
    {ι : Type*} (ρ : ι → ℂ) (s : Finset ι)
    (hρ0 : ∀ i, ρ i ≠ 0)
    (hρnorm : ∀ i, 1 ≤ ‖ρ i‖)
    (hsum : Summable (fun i ↦ 1 / ‖ρ i‖ ^ 2)) :
    Differentiable ℂ (zetaGenusOneComplementProduct ρ s) := by
  have hdiff : DifferentiableOn ℂ
      (zetaGenusOneComplementProduct ρ s) Set.univ := by
    apply (hasProdLocallyUniformlyOn_zetaGenusOneComplement
      ρ s hρ0 hρnorm hsum).differentiableOn
    · exact Filter.Eventually.of_forall fun t ↦ by
        apply DifferentiableOn.fun_finsetProd
        intro i _
        exact fun z _ ↦
          (zetaGenusOneFactor_analytic (ρ i.1) z).differentiableAt
            |>.differentiableWithinAt
    · exact isOpen_univ
  intro z
  exact (hdiff z (Set.mem_univ z)).differentiableAt univ_mem

/-- Pointwise multipliability, exposed as an opaque interface so subsequent
finite/complement decompositions do not elaborate the uniform proof again. -/
theorem multipliable_zetaGenusOneFactor
    {ι : Type*} (ρ : ι → ℂ)
    (hρ0 : ∀ i, ρ i ≠ 0)
    (hρnorm : ∀ i, 1 ≤ ‖ρ i‖)
    (hsum : Summable (fun i ↦ 1 / ‖ρ i‖ ^ 2)) (z : ℂ) :
    Multipliable (fun i ↦ zetaGenusOneFactor (ρ i) z) := by
  have h := multipliable_one_add_of_summable
    (summable_norm_zetaGenusOneFactor_sub_one ρ hρ0 hρnorm hsum z)
  convert h using 1
  funext i
  ring

/-- A deliberately small wrapper around Mathlib's finite/complement product
split.  Keeping the function abstract avoids expensive dependent-type
unification when the theorem is instantiated by analytic factors. -/
theorem multipliable_finset_mul_complement
    {ι : Type*} (f : ι → ℂ) (s : Finset ι)
    (hfc : Multipliable (f ∘ (↑) : ↥((↑s : Set ι)ᶜ) → ℂ)) :
    (∏ i ∈ s, f i) * (∏' i : ↥((↑s : Set ι)ᶜ), f i.1) = ∏' i, f i := by
  classical
  exact ((s.hasProd f).mul_compl hfc.hasProd).tprod_eq.symm

/-- Pointwise factorization in terms of the named complementary entire
function. -/
theorem zetaGenusOneProduct_eq_finset_mul_complement
    {ι : Type*} (ρ : ι → ℂ) (s : Finset ι)
    (hρ0 : ∀ i, ρ i ≠ 0)
    (hρnorm : ∀ i, 1 ≤ ‖ρ i‖)
    (hsum : Summable (fun i ↦ 1 / ‖ρ i‖ ^ 2)) (z : ℂ) :
    (∏' i, zetaGenusOneFactor (ρ i) z) =
      (∏ i ∈ s, zetaGenusOneFactor (ρ i) z) *
        zetaGenusOneComplementProduct ρ s z := by
  let f : ι → ℂ := fun i ↦ zetaGenusOneFactor (ρ i) z
  have hsum' : Summable
      (fun i : ↥((↑s : Set ι)ᶜ) ↦ 1 / ‖ρ i.1‖ ^ 2) :=
    hsum.comp_injective Subtype.coe_injective
  have hfc : Multipliable
      (f ∘ (↑) : ↥((↑s : Set ι)ᶜ) → ℂ) := by
    exact multipliable_zetaGenusOneFactor
      (fun i : ↥((↑s : Set ι)ᶜ) ↦ ρ i.1)
      (fun i ↦ hρ0 i.1) (fun i ↦ hρnorm i.1) hsum' z
  have hsplit := multipliable_finset_mul_complement f s hfc
  change (∏' i, f i) =
    (∏ i ∈ s, f i) * (∏' i : ↥((↑s : Set ι)ᶜ), f i.1)
  exact hsplit.symm

/-- The complement is nonzero at a point after every factor copy at that
point has been placed in the selected finite set. -/
theorem zetaGenusOneComplementProduct_ne_zero
    {ι : Type*} (ρ : ι → ℂ) (s : Finset ι)
    (hρ0 : ∀ i, ρ i ≠ 0)
    (hρnorm : ∀ i, 1 ≤ ‖ρ i‖)
    (hsum : Summable (fun i ↦ 1 / ‖ρ i‖ ^ 2))
    {z : ℂ} (hcopies : ∀ i, ρ i = z → i ∈ s) :
    zetaGenusOneComplementProduct ρ s z ≠ 0 := by
  unfold zetaGenusOneComplementProduct
  have hsum' : Summable
      (fun i : ↥((↑s : Set ι)ᶜ) ↦ 1 / ‖ρ i.1‖ ^ 2) :=
    hsum.comp_injective Subtype.coe_injective
  intro hzero
  have hexists := (tprod_zetaGenusOneFactor_eq_zero_iff
    (fun i : ↥((↑s : Set ι)ᶜ) ↦ ρ i.1)
    (fun i ↦ hρ0 i.1) (fun i ↦ hρnorm i.1) hsum' z).mp hzero
  obtain ⟨i, hi⟩ := hexists
  exact i.2 (hcopies i.1 hi)

/-- A finite product all of whose selected divisor points equal `z` is the
corresponding power of the single primary factor. -/
theorem selected_zetaGenusOneFactors_eq_pow
    {ι : Type*} (ρ : ι → ℂ) (s : Finset ι) {z w : ℂ}
    (hselected : ∀ i ∈ s, ρ i = z) :
    (∏ i ∈ s, zetaGenusOneFactor (ρ i) w) =
      zetaGenusOneFactor z w ^ s.card := by
  apply Finset.prod_eq_pow_card
  intro i hi
  rw [hselected i hi]

/-- Generic multiplicity theorem for an inverse-square controlled genus-one
product.  The selected finite set must contain exactly the copies at `z`. -/
theorem analyticOrderAt_tprod_zetaGenusOneFactor
    {ι : Type*} (ρ : ι → ℂ) (s : Finset ι)
    (hρ0 : ∀ i, ρ i ≠ 0)
    (hρnorm : ∀ i, 1 ≤ ‖ρ i‖)
    (hsum : Summable (fun i ↦ 1 / ‖ρ i‖ ^ 2))
    {z : ℂ} (hz0 : z ≠ 0) (hselected : ∀ i, i ∈ s ↔ ρ i = z) :
    analyticOrderAt (fun w ↦ ∏' i, zetaGenusOneFactor (ρ i) w) z = s.card := by
  have hfactor : (fun w ↦ ∏' i, zetaGenusOneFactor (ρ i) w) =
      (fun w ↦ (zetaGenusOneFactor z w ^ s.card) *
        zetaGenusOneComplementProduct ρ s w) := by
    funext w
    rw [zetaGenusOneProduct_eq_finset_mul_complement ρ s hρ0 hρnorm hsum w]
    rw [selected_zetaGenusOneFactors_eq_pow ρ s
      (fun i hi ↦ (hselected i).mp hi)]
  rw [hfactor]
  have hpowAnalytic : AnalyticAt ℂ (fun w ↦ zetaGenusOneFactor z w ^ s.card) z :=
    (zetaGenusOneFactor_analytic z z).pow s.card
  have hcomplAnalytic : AnalyticAt ℂ (zetaGenusOneComplementProduct ρ s) z :=
    (differentiable_zetaGenusOneComplementProduct ρ s hρ0 hρnorm hsum).analyticAt z
  change analyticOrderAt
    ((fun w ↦ zetaGenusOneFactor z w ^ s.card) *
      zetaGenusOneComplementProduct ρ s) z = s.card
  rw [analyticOrderAt_mul hpowAnalytic hcomplAnalytic]
  have hpowOrder := analyticOrderAt_pow
    (zetaGenusOneFactor_analytic z z) s.card
  change analyticOrderAt (fun w ↦ zetaGenusOneFactor z w ^ s.card) z =
    s.card • analyticOrderAt (zetaGenusOneFactor z) z at hpowOrder
  rw [hpowOrder]
  rw [analyticOrderAt_zetaGenusOneFactor_self hz0]
  have hcompl0 : analyticOrderAt (zetaGenusOneComplementProduct ρ s) z = 0 :=
    analyticOrderAt_eq_zero.mpr (Or.inr
      (zetaGenusOneComplementProduct_ne_zero ρ s hρ0 hρnorm hsum
        (fun i hi ↦ (hselected i).mpr hi)))
  rw [hcompl0]
  simp

/-! ## Positive zeta tail -/

/-- All multiplicity copies above one fixed positive-height shell point. -/
noncomputable def positiveHighZetaFactorFiber
    (i : PositiveHighZetaShellIndex) : Finset PositiveHighZetaFactorIndex :=
  Finset.univ.map
    ⟨(fun k : Fin (analyticOrderNatAt riemannXiEntire i.2.1) ↦ ⟨i, k⟩), by
      intro a b h
      exact Fin.ext (congrArg (fun x : PositiveHighZetaFactorIndex ↦ x.2.1) h)⟩

@[simp] theorem card_positiveHighZetaFactorFiber
    (i : PositiveHighZetaShellIndex) :
    (positiveHighZetaFactorFiber i).card =
      analyticOrderNatAt riemannXiEntire i.2.1 := by
  simp [positiveHighZetaFactorFiber]

/-- Equality of carried positive zero points determines the underlying shell
index; multiplicity is the only remaining freedom. -/
theorem positiveHighZetaFactor_fst_eq_of_point_eq
    (j k : PositiveHighZetaFactorIndex)
    (h : positiveHighZetaFactorPoint j = positiveHighZetaFactorPoint k) :
    j.1 = k.1 := by
  have hpoint0 : j.1.2.1 = k.1.2.1 := by
    exact h
  apply (positiveHighZetaShellEquiv).injective
  apply Subtype.ext
  apply Subtype.ext
  exact hpoint0

@[simp] theorem mem_positiveHighZetaFactorFiber_iff
    (i : PositiveHighZetaShellIndex) (j : PositiveHighZetaFactorIndex) :
    j ∈ positiveHighZetaFactorFiber i ↔ j.1 = i := by
  constructor
  · intro hj
    simp only [positiveHighZetaFactorFiber, Finset.mem_map,
      Finset.mem_univ, true_and] at hj
    obtain ⟨a, ha⟩ := hj
    exact (congrArg Sigma.fst ha).symm
  · intro hj
    subst i
    refine Finset.mem_map.mpr ⟨j.2, Finset.mem_univ _, ?_⟩
    cases j
    rfl

/-- The positive tail product has exactly the xi multiplicity at each of its
zeros. -/
theorem analyticOrderAt_positiveZetaGenusOneTailProduct
    {z : ℂ} (hz : IsNontrivialZetaZero z) (him : 2 ≤ z.im) :
    analyticOrderAt positiveZetaGenusOneTailProduct z =
      analyticOrderNatAt riemannXiEntire z := by
  obtain ⟨j, hj⟩ := exists_positiveHighZetaFactorPoint_eq hz him
  let s := positiveHighZetaFactorFiber j.1
  have hselected : ∀ k : PositiveHighZetaFactorIndex,
      k ∈ s ↔ positiveHighZetaFactorPoint k = z := by
    intro k
    rw [show s = positiveHighZetaFactorFiber j.1 from rfl,
      mem_positiveHighZetaFactorFiber_iff]
    constructor
    · intro hk
      change k.1.2.1 = z
      rw [hk]
      exact hj
    · intro hk
      exact positiveHighZetaFactor_fst_eq_of_point_eq k j (hk.trans hj.symm)
  have horder := analyticOrderAt_tprod_zetaGenusOneFactor
    positiveHighZetaFactorPoint s
    positiveHighZetaFactorPoint_ne_zero
    (fun k ↦ le_trans (by norm_num) (positiveHighZetaFactor_shell_le_norm k))
    summable_positiveHighZetaFactor_inverseSquare
    (by
      intro hz0
      exact positiveHighZetaFactorPoint_ne_zero j (hj.trans hz0))
    hselected
  unfold positiveZetaGenusOneTailProduct
  rw [horder]
  rw [show s = positiveHighZetaFactorFiber j.1 from rfl,
    card_positiveHighZetaFactorFiber]
  congr 1
  simpa [positiveHighZetaFactorPoint] using congrArg
    (analyticOrderNatAt riemannXiEntire) hj

/-! ## Reflected negative zeta tail -/

noncomputable def negativeHighZetaFactorFiber
    (i : NegativeHighZetaShellIndex) : Finset NegativeHighZetaFactorIndex :=
  Finset.univ.map
    ⟨(fun k : Fin (analyticOrderNatAt riemannZeta (1 - i.2.1)) ↦ ⟨i, k⟩), by
      intro a b h
      exact Fin.ext (congrArg (fun x : NegativeHighZetaFactorIndex ↦ x.2.1) h)⟩

@[simp] theorem card_negativeHighZetaFactorFiber
    (i : NegativeHighZetaShellIndex) :
    (negativeHighZetaFactorFiber i).card =
      analyticOrderNatAt riemannZeta (1 - i.2.1) := by
  simp [negativeHighZetaFactorFiber]

theorem negativeHighZetaFactor_fst_eq_of_point_eq
    (j k : NegativeHighZetaFactorIndex)
    (h : negativeHighZetaFactorPoint j = negativeHighZetaFactorPoint k) :
    j.1 = k.1 := by
  have hpoint0 : 1 - j.1.2.1 = 1 - k.1.2.1 := h
  apply (negativeHighZetaShellEquiv).injective
  apply Subtype.ext
  apply Subtype.ext
  exact hpoint0

@[simp] theorem mem_negativeHighZetaFactorFiber_iff
    (i : NegativeHighZetaShellIndex) (j : NegativeHighZetaFactorIndex) :
    j ∈ negativeHighZetaFactorFiber i ↔ j.1 = i := by
  constructor
  · intro hj
    simp only [negativeHighZetaFactorFiber, Finset.mem_map,
      Finset.mem_univ, true_and] at hj
    obtain ⟨a, ha⟩ := hj
    exact (congrArg Sigma.fst ha).symm
  · intro hj
    subst i
    refine Finset.mem_map.mpr ⟨j.2, Finset.mem_univ _, ?_⟩
    cases j
    rfl

/-- The reflected negative tail has the exact xi multiplicity at each of its
zeros. -/
theorem analyticOrderAt_negativeZetaGenusOneTailProduct
    {z : ℂ} (hz : IsNontrivialZetaZero z) (him : z.im ≤ -2) :
    analyticOrderAt negativeZetaGenusOneTailProduct z =
      analyticOrderNatAt riemannXiEntire z := by
  obtain ⟨j, hj⟩ := exists_negativeHighZetaFactorPoint_eq hz him
  let s := negativeHighZetaFactorFiber j.1
  have hselected : ∀ k : NegativeHighZetaFactorIndex,
      k ∈ s ↔ negativeHighZetaFactorPoint k = z := by
    intro k
    rw [show s = negativeHighZetaFactorFiber j.1 from rfl,
      mem_negativeHighZetaFactorFiber_iff]
    constructor
    · intro hk
      change 1 - k.1.2.1 = z
      rw [hk]
      exact hj
    · intro hk
      exact negativeHighZetaFactor_fst_eq_of_point_eq k j (hk.trans hj.symm)
  have horder := analyticOrderAt_tprod_zetaGenusOneFactor
    negativeHighZetaFactorPoint s
    negativeHighZetaFactorPoint_ne_zero
    (fun k ↦ le_trans (by norm_num) (negativeHighZetaFactor_shell_le_norm k))
    summable_negativeHighZetaFactor_inverseSquare
    (by
      intro hz0
      exact negativeHighZetaFactorPoint_ne_zero j (hj.trans hz0))
    hselected
  unfold negativeZetaGenusOneTailProduct
  rw [horder]
  rw [show s = negativeHighZetaFactorFiber j.1 from rfl,
    card_negativeHighZetaFactorFiber]
  congr 1
  have hj' : 1 - j.1.2.1 = z := hj
  have hnat : analyticOrderNatAt riemannZeta (1 - j.1.2.1) =
      analyticOrderNatAt riemannXiEntire z := by
    rw [hj']
    exact hz.xiMultiplicity_eq_zetaMultiplicity.symm
  exact hnat

/-! ## Finite central block -/

/-- Analytic order is additive over a finite product. -/
theorem analyticOrderAt_finsetProduct
    {ι : Type*} (s : Finset ι) (f : ι → ℂ → ℂ) (z : ℂ)
    (hf : ∀ i ∈ s, AnalyticAt ℂ (f i) z) :
    analyticOrderAt (fun w ↦ ∏ i ∈ s, f i w) z =
      ∑ i ∈ s, analyticOrderAt (f i) z := by
  classical
  induction s using Finset.induction_on with
  | empty => simp [analyticOrderAt_eq_zero]
  | @insert a s ha ih =>
      have haAnalytic : AnalyticAt ℂ (f a) z := hf a (Finset.mem_insert_self a s)
      have hsAnalytic : AnalyticAt ℂ (fun w ↦ ∏ i ∈ s, f i w) z :=
        s.analyticAt_fun_prod (fun i hi ↦ hf i (Finset.mem_insert_of_mem hi))
      simp only [Finset.prod_insert ha, Finset.sum_insert ha]
      change analyticOrderAt (f a * fun w ↦ ∏ i ∈ s, f i w) z = _
      rw [analyticOrderAt_mul haAnalytic hsAnalytic, ih]
      intro i hi
      exact hf i (Finset.mem_insert_of_mem hi)

noncomputable def lowHeightZetaFactorFiber
    (ρ : {z : NontrivialZetaZeroPoint | |z.1.im| < 2}) :
    Finset LowHeightZetaFactorIndex :=
  Finset.univ.map
    ⟨(fun k : Fin (zetaZeroMultiplicity ρ.1) ↦ ⟨ρ, k⟩), by
      intro a b h
      exact Fin.ext (congrArg (fun x : LowHeightZetaFactorIndex ↦ x.2.1) h)⟩

@[simp] theorem card_lowHeightZetaFactorFiber
    (ρ : {z : NontrivialZetaZeroPoint | |z.1.im| < 2}) :
    (lowHeightZetaFactorFiber ρ).card = zetaZeroMultiplicity ρ.1 := by
  simp [lowHeightZetaFactorFiber]

@[simp] theorem mem_lowHeightZetaFactorFiber_iff
    (ρ : {z : NontrivialZetaZeroPoint | |z.1.im| < 2})
    (j : LowHeightZetaFactorIndex) :
    j ∈ lowHeightZetaFactorFiber ρ ↔ j.1 = ρ := by
  constructor
  · intro hj
    simp only [lowHeightZetaFactorFiber, Finset.mem_map,
      Finset.mem_univ, true_and] at hj
    obtain ⟨a, ha⟩ := hj
    exact (congrArg Sigma.fst ha).symm
  · intro hj
    subst ρ
    refine Finset.mem_map.mpr ⟨j.2, Finset.mem_univ _, ?_⟩
    cases j
    rfl

theorem lowHeightZetaFactor_fst_eq_of_point_eq
    (j k : LowHeightZetaFactorIndex)
    (h : lowHeightZetaFactorPoint j = lowHeightZetaFactorPoint k) :
    j.1 = k.1 := by
  apply Subtype.ext
  apply Subtype.ext
  exact h

/-- The finite central product also has exactly the xi multiplicity at each
central nontrivial zero. -/
theorem analyticOrderAt_lowHeightZetaGenusOneProduct
    {z : ℂ} (hz : IsNontrivialZetaZero z) (him : |z.im| < 2) :
    analyticOrderAt lowHeightZetaGenusOneProduct z =
      analyticOrderNatAt riemannXiEntire z := by
  classical
  let ρ : {z : NontrivialZetaZeroPoint | |z.1.im| < 2} :=
    ⟨⟨z, hz⟩, him⟩
  let s := lowHeightZetaFactorFiber ρ
  have hselected : ∀ j : LowHeightZetaFactorIndex,
      j ∈ s ↔ lowHeightZetaFactorPoint j = z := by
    intro j
    rw [show s = lowHeightZetaFactorFiber ρ from rfl,
      mem_lowHeightZetaFactorFiber_iff]
    constructor
    · intro hj
      change j.1.1.1 = z
      rw [hj]
    · intro hj
      apply lowHeightZetaFactor_fst_eq_of_point_eq j ⟨ρ, ⟨0, by
        exact hz.zetaMultiplicity_pos⟩⟩
      exact hj
  have hfactorOrder : ∀ j : LowHeightZetaFactorIndex,
      analyticOrderAt (zetaGenusOneFactor (lowHeightZetaFactorPoint j)) z =
        if j ∈ s then 1 else 0 := by
    intro j
    by_cases hj : j ∈ s
    · rw [if_pos hj]
      have hp : lowHeightZetaFactorPoint j = z := (hselected j).mp hj
      rw [← hp]
      exact analyticOrderAt_zetaGenusOneFactor_self
        (lowHeightZetaFactorPoint_ne_zero j)
    · rw [if_neg hj]
      apply analyticOrderAt_eq_zero.mpr
      right
      exact (zetaGenusOneFactor_eq_zero_iff
        (lowHeightZetaFactorPoint_ne_zero j)).not.mpr
          (fun hp ↦ hj ((hselected j).mpr hp.symm))
  unfold lowHeightZetaGenusOneProduct
  rw [analyticOrderAt_finsetProduct]
  · calc
      (∑ j ∈ Finset.univ,
          analyticOrderAt (zetaGenusOneFactor (lowHeightZetaFactorPoint j)) z) =
          ∑ j ∈ Finset.univ, if j ∈ s then 1 else 0 := by
            apply Finset.sum_congr rfl
            intro j _
            exact hfactorOrder j
      _ = (s.card : ENat) := by simp
      _ = (zetaZeroMultiplicity ⟨z, hz⟩ : ENat) := by
        rw [show s = lowHeightZetaFactorFiber ρ from rfl,
          card_lowHeightZetaFactorFiber]
      _ = analyticOrderNatAt riemannXiEntire z := by
        exact congrArg (fun n : ℕ ↦ (n : ENat))
          hz.xiMultiplicity_eq_zetaMultiplicity.symm
  · intro j _
    exact zetaGenusOneFactor_analytic (lowHeightZetaFactorPoint j) z

/-! ## Complete divisor multiplicity -/

theorem positiveHighZetaFactorPoint_im_ge_two
    (j : PositiveHighZetaFactorIndex) :
    2 ≤ (positiveHighZetaFactorPoint j).im := by
  have hmem := (mem_positiveUnitZetaShellFinset.mp j.1.2.property).2.1
  have hn : (0 : ℝ) ≤ j.1.1 := Nat.cast_nonneg _
  norm_num [positiveHighZetaFactorPoint, Nat.cast_add] at hmem ⊢
  linarith

theorem negativeHighZetaFactorPoint_im_le_neg_two
    (j : NegativeHighZetaFactorIndex) :
    (negativeHighZetaFactorPoint j).im ≤ -2 := by
  have hmem := (mem_positiveUnitZetaShellFinset.mp j.1.2.property).2.1
  have hn : (0 : ℝ) ≤ j.1.1 := Nat.cast_nonneg _
  norm_num [negativeHighZetaFactorPoint, Nat.cast_add] at hmem ⊢
  linarith

theorem positiveZetaGenusOneTailProduct_ne_zero_of_im_lt_two
    {z : ℂ} (hz : z.im < 2) :
    positiveZetaGenusOneTailProduct z ≠ 0 := by
  intro hzero
  obtain ⟨j, hj⟩ :=
    (positiveZetaGenusOneTailProduct_eq_zero_iff z).mp hzero
  have := positiveHighZetaFactorPoint_im_ge_two j
  rw [hj] at this
  linarith

theorem negativeZetaGenusOneTailProduct_ne_zero_of_neg_two_lt_im
    {z : ℂ} (hz : -2 < z.im) :
    negativeZetaGenusOneTailProduct z ≠ 0 := by
  intro hzero
  obtain ⟨j, hj⟩ :=
    (negativeZetaGenusOneTailProduct_eq_zero_iff z).mp hzero
  have := negativeHighZetaFactorPoint_im_le_neg_two j
  rw [hj] at this
  linarith

theorem lowHeightZetaGenusOneProduct_ne_zero_of_two_le_abs_im
    {z : ℂ} (hz : 2 ≤ |z.im|) :
    lowHeightZetaGenusOneProduct z ≠ 0 := by
  intro hzero
  obtain ⟨j, hj⟩ :=
    (lowHeightZetaGenusOneProduct_eq_zero_iff z).mp hzero
  have hlow : |(lowHeightZetaFactorPoint j).im| < 2 := j.1.property
  rw [hj] at hlow
  linarith

/-- The assembled canonical product and the completed zeta function now have
the same analytic order at every nontrivial zero.  This completes equality of
their divisors, including multiplicity. -/
theorem analyticOrderAt_completedZetaGenusOneProduct
    {z : ℂ} (hz : IsNontrivialZetaZero z) :
    analyticOrderAt completedZetaGenusOneProduct z =
      analyticOrderAt riemannXiEntire z := by
  have hposA : AnalyticAt ℂ positiveZetaGenusOneTailProduct z :=
    differentiable_positiveZetaGenusOneTailProduct.analyticAt z
  have hnegA : AnalyticAt ℂ negativeZetaGenusOneTailProduct z :=
    differentiable_negativeZetaGenusOneTailProduct.analyticAt z
  have hlowA : AnalyticAt ℂ lowHeightZetaGenusOneProduct z :=
    differentiable_lowHeightZetaGenusOneProduct.analyticAt z
  have hxiFinite : analyticOrderAt riemannXiEntire z ≠ ⊤ := by
    rw [hz.xiOrder_eq_zetaOrder]
    exact zetaZeroOrder_ne_top (by
      intro h
      subst z
      have := hz.re_lt_one
      norm_num at this)
  have hxiNat : (analyticOrderNatAt riemannXiEntire z : ENat) =
      analyticOrderAt riemannXiEntire z :=
    Nat.cast_analyticOrderNatAt hxiFinite
  unfold completedZetaGenusOneProduct
  change analyticOrderAt
    ((positiveZetaGenusOneTailProduct * negativeZetaGenusOneTailProduct) *
      lowHeightZetaGenusOneProduct) z = _
  rw [analyticOrderAt_mul (hposA.mul hnegA) hlowA,
    analyticOrderAt_mul hposA hnegA]
  by_cases hpos : 2 ≤ z.im
  · have hneg0 : analyticOrderAt negativeZetaGenusOneTailProduct z = 0 :=
      analyticOrderAt_eq_zero.mpr (Or.inr
        (negativeZetaGenusOneTailProduct_ne_zero_of_neg_two_lt_im (by linarith)))
    have hlow0 : analyticOrderAt lowHeightZetaGenusOneProduct z = 0 :=
      analyticOrderAt_eq_zero.mpr (Or.inr
        (lowHeightZetaGenusOneProduct_ne_zero_of_two_le_abs_im (by
          rw [abs_of_nonneg (by linarith)]
          exact hpos)))
    rw [analyticOrderAt_positiveZetaGenusOneTailProduct hz hpos, hneg0, hlow0]
    simpa using hxiNat
  · by_cases hneg : z.im ≤ -2
    · have hpos0 : analyticOrderAt positiveZetaGenusOneTailProduct z = 0 :=
        analyticOrderAt_eq_zero.mpr (Or.inr
          (positiveZetaGenusOneTailProduct_ne_zero_of_im_lt_two (by linarith)))
      have hlow0 : analyticOrderAt lowHeightZetaGenusOneProduct z = 0 :=
        analyticOrderAt_eq_zero.mpr (Or.inr
          (lowHeightZetaGenusOneProduct_ne_zero_of_two_le_abs_im (by
            rw [abs_of_nonpos (by linarith)]
            linarith)))
      rw [hpos0, analyticOrderAt_negativeZetaGenusOneTailProduct hz hneg, hlow0]
      simpa using hxiNat
    · have him : |z.im| < 2 := abs_lt.mpr ⟨by linarith, by linarith⟩
      have him' := abs_lt.mp him
      have hpos0 : analyticOrderAt positiveZetaGenusOneTailProduct z = 0 :=
        analyticOrderAt_eq_zero.mpr (Or.inr
          (positiveZetaGenusOneTailProduct_ne_zero_of_im_lt_two him'.2))
      have hneg0 : analyticOrderAt negativeZetaGenusOneTailProduct z = 0 :=
        analyticOrderAt_eq_zero.mpr (Or.inr
          (negativeZetaGenusOneTailProduct_ne_zero_of_neg_two_lt_im him'.1))
      rw [hpos0, hneg0, analyticOrderAt_lowHeightZetaGenusOneProduct hz him]
      simpa using hxiNat

end RiemannLab
