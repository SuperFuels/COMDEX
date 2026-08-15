import RiemannLab.Tasks.FinitePrincipalParts
import Mathlib.Analysis.Meromorphic.Complex

namespace RiemannLab

open Filter
open scoped Topology

/-!
Meromorphy and removable principal parts for the actual zeta explicit-formula
kernel.
-/

/-- The Riemann zeta function is meromorphic at its pole `1`. -/
theorem meromorphicAt_riemannZeta_one : MeromorphicAt riemannZeta 1 := by
  let rhs : ℂ → ℂ := fun s ↦
    (s * completedRiemannZeta₀ s - 1 - s / (1 - s)) /
      (2 * Real.pi ^ (-s / 2) * Complex.Gamma (s / 2 + 1))
  have hLambda : MeromorphicAt completedRiemannZeta₀ 1 :=
    (differentiable_completedZeta₀.analyticAt 1).meromorphicAt
  have hpow : MeromorphicAt (fun s : ℂ ↦ (Real.pi : ℂ) ^ (-s / 2)) 1 :=
    ((differentiable_id.neg.div_const 2).const_cpow
      (.inl (Complex.ofReal_ne_zero.mpr Real.pi_ne_zero))).analyticAt 1 |>.meromorphicAt
  have hinner : AnalyticAt ℂ (fun s : ℂ ↦ s / 2 + 1) 1 := by fun_prop
  have hGamma : MeromorphicAt (fun s : ℂ ↦ Complex.Gamma (s / 2 + 1)) 1 :=
    Meromorphic.Gamma.meromorphicAt.comp_analyticAt hinner
  have hrhs : MeromorphicAt rhs 1 := by
    dsimp [rhs]
    exact (((MeromorphicAt.id 1).mul hLambda).sub (MeromorphicAt.const 1 1) |>.sub
      ((MeromorphicAt.id 1).div
        ((MeromorphicAt.const 1 1).sub (MeromorphicAt.id 1)))).div
      (((MeromorphicAt.const 2 1).mul hpow).mul hGamma)
  exact hrhs.congr (Eventually.of_forall fun s ↦
    (riemannZeta_eq_mul_completedRiemannZeta₀ s).symm)

/-- Zeta is meromorphic at every complex point: analytic away from `1`, and
meromorphic at `1` by its completed-zeta representation. -/
theorem meromorphicAt_riemannZeta (p : ℂ) : MeromorphicAt riemannZeta p := by
  rcases eq_or_ne p 1 with rfl | hp
  · exact meromorphicAt_riemannZeta_one
  · exact (analyticOn_riemannZeta p (by simpa using hp)).meromorphicAt

/-- For positive `x`, the complete logarithmic-derivative Perron kernel is
meromorphic at every point. -/
theorem meromorphicAt_explicitFormulaContourKernel
    {x : ℝ} (hx : 0 < x) (p : ℂ) :
    MeromorphicAt (explicitFormulaContourKernel x) p := by
  have hzeta := meromorphicAt_riemannZeta p
  have hpow : MeromorphicAt (fun s : ℂ ↦ (x : ℂ) ^ s) p :=
    (differentiable_id.const_cpow
      (.inl (Complex.ofReal_ne_zero.mpr hx.ne'))).analyticAt p |>.meromorphicAt
  unfold explicitFormulaContourKernel logDeriv
  exact (hzeta.deriv.div hzeta).neg.mul (hpow.div (.id p))

/-- The principal part at a nontrivial zero, including its full divisor
multiplicity, has an analytic remainder. -/
theorem exists_analyticAt_explicitFormulaContourKernel_sub_nontrivialPrincipalPart
    {ρ : ℂ} (hρ : IsNontrivialZetaZero ρ) {x : ℝ} (hx : 0 < x) :
    ∃ g : ℂ → ℂ, AnalyticAt ℂ g ρ ∧
      (fun s ↦ explicitFormulaContourKernel x s -
        (-(analyticOrderNatAt riemannZeta ρ : ℂ) * explicitFormulaZeroKernel x ρ) *
          (s - ρ)⁻¹) =ᶠ[𝓝[≠] ρ] g :=
  exists_analyticAt_sub_principalPart
    (meromorphicAt_explicitFormulaContourKernel hx ρ)
    (hρ.tendsto_mul_explicitFormulaContourKernel hx)

/-- The principal part at a negative-even trivial zero has an analytic
remainder. -/
theorem exists_analyticAt_explicitFormulaContourKernel_sub_trivialPrincipalPart
    (n : ℕ) {x : ℝ} (hx : 0 < x) :
    let ρ : ℂ := -2 * (n + 1)
    ∃ g : ℂ → ℂ, AnalyticAt ℂ g ρ ∧
      (fun s ↦ explicitFormulaContourKernel x s -
        (-explicitFormulaZeroKernel x ρ) * (s - ρ)⁻¹) =ᶠ[𝓝[≠] ρ] g := by
  dsimp only
  exact exists_analyticAt_sub_principalPart
    (meromorphicAt_explicitFormulaContourKernel hx _)
    (tendsto_mul_explicitFormulaContourKernel_at_trivialZero n hx)

/-- The main-term pole at `1` is removable after subtracting `x/(s-1)`. -/
theorem exists_analyticAt_explicitFormulaContourKernel_sub_onePrincipalPart
    {x : ℝ} (hx : 0 < x) :
    ∃ g : ℂ → ℂ, AnalyticAt ℂ g 1 ∧
      (fun s ↦ explicitFormulaContourKernel x s - (x : ℂ) * (s - 1)⁻¹)
        =ᶠ[𝓝[≠] 1] g :=
  exists_analyticAt_sub_principalPart
    (meromorphicAt_explicitFormulaContourKernel hx 1)
    (tendsto_mul_explicitFormulaContourKernel_at_one hx)

/-- The Perron pole at `0` is removable after subtracting its
`-log(2π)/s` principal part. -/
theorem exists_analyticAt_explicitFormulaContourKernel_sub_zeroPrincipalPart
    {x : ℝ} (hx : 0 < x) :
    ∃ g : ℂ → ℂ, AnalyticAt ℂ g 0 ∧
      (fun s ↦ explicitFormulaContourKernel x s -
        (-Complex.log (2 * Real.pi)) * s⁻¹) =ᶠ[𝓝[≠] 0] g := by
  have hlim : Tendsto (fun z : ℂ ↦ (z - 0) * explicitFormulaContourKernel x z)
      (𝓝[≠] 0) (𝓝 (-Complex.log (2 * Real.pi))) := by
    simpa only [sub_zero] using tendsto_mul_explicitFormulaContourKernel_at_zero hx
  simpa only [sub_zero] using exists_analyticAt_sub_principalPart
    (meromorphicAt_explicitFormulaContourKernel hx 0) hlim

/-- The four possible pole descriptions for the explicit-formula contour
kernel, together with the precomputed residue assigned to that point. -/
inductive ExplicitFormulaPoleData (x : ℝ) (residue : ℂ → ℂ) (p : ℂ) : Prop
  | one (hp : p = 1) (hr : residue p = x)
  | zero (hp : p = 0) (hr : residue p = -Complex.log (2 * Real.pi))
  | trivial (n : ℕ) (hp : p = -2 * (n + 1))
      (hr : residue p = -explicitFormulaZeroKernel x p)
  | nontrivial (hp : IsNontrivialZetaZero p)
      (hr : residue p =
        -(analyticOrderNatAt riemannZeta p : ℂ) * explicitFormulaZeroKernel x p)

/-- Finite principal-parts decomposition instantiated for the actual zeta
contour kernel.  A finite set containing every singularity under discussion
is enough: the resulting remainder is analytic everywhere once analyticity
of the kernel away from that set has been established. -/
theorem exists_analyticAt_all_explicitFormulaContourKernel_sub_finsetPrincipalParts
    {x : ℝ} (hx : 0 < x) (P : Finset ℂ) (residue : ℂ → ℂ)
    (hpole : ∀ p ∈ P, ExplicitFormulaPoleData x residue p)
    (hana : ∀ z ∉ P, AnalyticAt ℂ (explicitFormulaContourKernel x) z) :
    ∃ g : ℂ → ℂ, (∀ z, AnalyticAt ℂ g z) ∧
      ∀ z ∉ P, explicitFormulaContourKernel x z =
        g z + ∑ p ∈ P, residue p * (z - p)⁻¹ := by
  apply exists_analyticAt_all_sub_finset_principalParts
    (explicitFormulaContourKernel x) residue P
  · intro p hp
    exact meromorphicAt_explicitFormulaContourKernel hx p
  · intro p hp
    have h := hpole p hp
    cases h with
    | one hp hr =>
        subst p
        simpa only [hr] using tendsto_mul_explicitFormulaContourKernel_at_one hx
    | zero hp hr =>
        subst p
        simpa only [sub_zero, hr] using
          tendsto_mul_explicitFormulaContourKernel_at_zero hx
    | trivial n hp hr =>
        subst p
        simpa only [hr] using
          tendsto_mul_explicitFormulaContourKernel_at_trivialZero n hx
    | nontrivial hp hr =>
        simpa only [hr] using hp.tendsto_mul_explicitFormulaContourKernel hx
  · exact hana

end RiemannLab
