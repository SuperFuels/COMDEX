import RiemannLab.Tasks.ZetaDampedSummability
import RiemannLab.Tasks.LiFiniteSpectralIsolation

namespace RiemannLab

open ComplexConjugate

/-!
# Two-sided zeta damping and finite low-height block

The functional equation transports the verified positive-height shell
envelope to negative height without losing analytic multiplicity.  The zeros
not covered by the two tails form a finite compact block.
-/

/-- Reflection through `s ↦ 1-s` preserves the analytic order of the entire
xi function. -/
theorem riemannXiEntire_order_one_sub (s : ℂ) :
    analyticOrderAt riemannXiEntire (1 - s) =
      analyticOrderAt riemannXiEntire s := by
  let g : ℂ → ℂ := fun z ↦ 1 - z
  have hg : AnalyticAt ℂ g s := by fun_prop
  have hderiv : deriv g s ≠ 0 := by
    simp [g]
  have hcomp : analyticOrderAt (riemannXiEntire ∘ g) s =
      analyticOrderAt riemannXiEntire (g s) :=
    analyticOrderAt_comp_of_deriv_ne_zero hg hderiv
  have hfun : riemannXiEntire ∘ g = riemannXiEntire := by
    funext z
    exact riemannXiEntire_one_sub z
  rw [hfun] at hcomp
  simpa [g] using hcomp.symm

/-- Natural multiplicity is preserved by functional-equation reflection. -/
theorem riemannXiEntire_multiplicity_one_sub (s : ℂ) :
    analyticOrderNatAt riemannXiEntire (1 - s) =
      analyticOrderNatAt riemannXiEntire s := by
  unfold analyticOrderNatAt
  rw [riemannXiEntire_order_one_sub]

/-- Zeta multiplicity is preserved by reflection on nontrivial zeros. -/
theorem zetaMultiplicity_one_sub {ρ : ℂ} (hρ : IsNontrivialZetaZero ρ) :
    analyticOrderNatAt riemannZeta (1 - ρ) =
      analyticOrderNatAt riemannZeta ρ := by
  rw [← hρ.one_sub.xiMultiplicity_eq_zetaMultiplicity,
    ← hρ.xiMultiplicity_eq_zetaMultiplicity,
    riemannXiEntire_multiplicity_one_sub]

/-- A multiplicity-bearing point in the reflected negative copy of the
`n`th positive shell.  Its actual zeta zero is `1-ρ`. -/
def NegativeZetaShellPoint (n : ℕ) := PositiveZetaShellPoint n

noncomputable instance (n : ℕ) : Fintype (NegativeZetaShellPoint n) :=
  inferInstanceAs (Fintype (PositiveZetaShellPoint n))

/-- Disjoint shell model for the negative-height divisor. -/
def NegativeHighZetaShellIndex := Σ n : ℕ, NegativeZetaShellPoint n

/-- The negative tail carries exactly the transported fourth-power mass. -/
noncomputable def negativeHighZetaDampedMass
    (i : NegativeHighZetaShellIndex) : ℝ :=
  analyticOrderNatAt riemannZeta (1 - i.2.1) /
    (((i.1 + 1 : ℕ) : ℝ) ^ 4)

/-- The complete negative-height divisor is summable after the same damping. -/
theorem summable_negativeHighZetaDampedMass :
    Summable negativeHighZetaDampedMass := by
  have heq : negativeHighZetaDampedMass = positiveHighZetaDampedMass := by
    funext i
    have hzero : IsNontrivialZetaZero i.2.1 :=
      (mem_positiveUnitZetaShellFinset.mp i.2.property).1
    unfold negativeHighZetaDampedMass positiveHighZetaDampedMass
    rw [zetaMultiplicity_one_sub hzero,
      ← hzero.xiMultiplicity_eq_zetaMultiplicity]
  rw [heq]
  exact summable_positiveHighZetaDampedMass

/-- Every nontrivial zero of ordinate at most `-2` occurs in the reflected
negative shell model. -/
theorem exists_mem_reflected_negativeZetaShell
    {ρ : ℂ} (hρ : IsNontrivialZetaZero ρ) (him : ρ.im ≤ -2) :
    ∃ n : ℕ, 1 - ρ ∈ positiveUnitZetaShellFinset (n + 2) := by
  apply exists_mem_positiveUnitZetaShellFinset hρ.one_sub
  simpa using (neg_le_neg him)

/-- The nontrivial zeros in the central height band. -/
def lowHeightNontrivialZetaZeros : Set ℂ :=
  {ρ : ℂ | IsNontrivialZetaZero ρ ∧ |ρ.im| < 2}

/-- The central band is a finite zero block. -/
theorem lowHeightNontrivialZetaZeros_finite :
    lowHeightNontrivialZetaZeros.Finite := by
  let K : Set ℂ := Metric.closedBall (0 : ℂ) 3
  have hK : IsCompact K := isCompact_closedBall 0 3
  apply (compact_inter_zeta_zeros_finite hK).subset
  intro ρ hρ
  refine ⟨?_, hρ.1.1⟩
  rw [Metric.mem_closedBall, dist_zero_right]
  have hre : ρ.re ^ 2 ≤ 1 := by
    nlinarith [hρ.1.re_pos, hρ.1.re_lt_one]
  have him : ρ.im ^ 2 < 4 := by
    have := (sq_lt_sq₀ (abs_nonneg ρ.im) (by norm_num : (0 : ℝ) ≤ 2)).mpr hρ.2
    norm_num [sq_abs] at this ⊢
    exact this
  rw [← sq_le_sq₀ (norm_nonneg ρ) (by norm_num : (0 : ℝ) ≤ 3),
    Complex.sq_norm]
  simp only [Complex.normSq_apply]
  nlinarith

/-- A finite low-height block contributes a summable family for every
amplitude; no asymptotic estimate is required there. -/
theorem summable_on_lowHeightNontrivialZetaZeros
    (amplitude : NontrivialZetaZeroPoint → ℂ) :
    Summable (fun ρ : {z : NontrivialZetaZeroPoint | |z.1.im| < 2} ↦
      zetaModeWeight amplitude ρ.1) := by
  let e : NontrivialZetaZeroPoint ↪ ℂ :=
    ⟨Subtype.val, Subtype.val_injective⟩
  have hfinite : {z : NontrivialZetaZeroPoint | |z.1.im| < 2}.Finite := by
    have hpre := lowHeightNontrivialZetaZeros_finite.preimage_embedding e
    have heq : e ⁻¹' lowHeightNontrivialZetaZeros =
        {z : NontrivialZetaZeroPoint | |z.1.im| < 2} := by
      ext z
      simp [e, lowHeightNontrivialZetaZeros, z.property]
    rw [← heq]
    exact hpre
  letI := hfinite.fintype
  apply Summable.of_finite

end RiemannLab
