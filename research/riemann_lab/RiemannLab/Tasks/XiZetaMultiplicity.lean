import RiemannLab.Tasks.LiZetaTailEnvelope
import RiemannLab.Tasks.SharpJensenZeroCount

namespace RiemannLab

open Filter Topology Complex

/-!
# Equality of xi and zeta multiplicities in the critical strip

The quantitative Jensen theorem counts the divisor of the entire xi-type
function, while the Li tail uses the analytic multiplicity of zeta.  This file
closes that interface: the elementary and Gamma factors are analytic and
nonzero at every nontrivial zero, so the two vanishing orders agree exactly.
-/

/-- The nonvanishing factor relating the entire xi-type function to zeta in
the open critical strip. -/
noncomputable def xiZetaFactor (s : ℂ) : ℂ :=
  s * (s - 1) * Gammaℝ s

theorem analyticAt_Gammaℝ_of_re_pos {s : ℂ} (hs : 0 < s.re) :
    AnalyticAt ℂ Gammaℝ s := by
  letI : NeZero (Real.pi : ℂ) := ⟨ofReal_ne_zero.mpr Real.pi_ne_zero⟩
  rw [analyticAt_iff_eventually_differentiableAt]
  have hopen : IsOpen {z : ℂ | 0 < z.re} := isOpen_lt continuous_const continuous_re
  filter_upwards [hopen.mem_nhds hs] with z hz
  unfold Gammaℝ
  apply DifferentiableAt.mul
  · exact (differentiableAt_const_cpow_of_neZero
      (Real.pi : ℂ) (-z / 2)).comp z (by fun_prop)
  · exact (differentiableAt_Gamma (z / 2) (fun m hm ↦ by
      have hre := congrArg Complex.re hm
      simp at hre
      nlinarith)).comp z (by fun_prop)

theorem analyticAt_xiZetaFactor_of_re_pos {s : ℂ} (hs : 0 < s.re) :
    AnalyticAt ℂ xiZetaFactor s := by
  unfold xiZetaFactor
  exact ((analyticAt_id.mul (analyticAt_id.sub analyticAt_const)).mul
    (analyticAt_Gammaℝ_of_re_pos hs))

theorem xiZetaFactor_ne_zero_of_criticalStrip
    {s : ℂ} (hs0 : 0 < s.re) (hs1 : s.re < 1) :
    xiZetaFactor s ≠ 0 := by
  unfold xiZetaFactor
  apply mul_ne_zero
  · apply mul_ne_zero
    · exact ne_zero_of_re_pos hs0
    · exact sub_ne_zero.mpr (by
        intro h
        have hre := congrArg Complex.re h
        simp at hre
        linarith)
  · exact Gammaℝ_ne_zero_of_re_pos hs0

/-- Pointwise factorization throughout the open critical strip. -/
theorem riemannXiEntire_eq_xiZetaFactor_mul_zeta
    {s : ℂ} (hs0 : 0 < s.re) (hs1 : s.re < 1) :
    riemannXiEntire s = xiZetaFactor s * riemannZeta s := by
  have hsne0 : s ≠ 0 := ne_zero_of_re_pos hs0
  have hsne1 : s ≠ 1 := by
    intro h
    have hre := congrArg Complex.re h
    simp at hre
    linarith
  rw [riemannXiEntire_eq_mul_completedRiemannZeta hsne0 hsne1,
    riemannZeta_def_of_ne_zero hsne0]
  unfold xiZetaFactor
  field_simp [Gammaℝ_ne_zero_of_re_pos hs0]

/-- The factorization holds on a complete neighborhood of every nontrivial
zero, which is the correct germ-level input for analytic order. -/
theorem riemannXiEntire_eventuallyEq_xiZetaFactor_mul_zeta
    {ρ : ℂ} (hρ : IsNontrivialZetaZero ρ) :
    riemannXiEntire =ᶠ[nhds ρ] fun s ↦ xiZetaFactor s * riemannZeta s := by
  have hopen : IsOpen {s : ℂ | 0 < s.re ∧ s.re < 1} :=
    (isOpen_lt continuous_const continuous_re).inter
      (isOpen_lt continuous_re continuous_const)
  filter_upwards [hopen.mem_nhds ⟨hρ.re_pos, hρ.re_lt_one⟩] with s hs
  exact riemannXiEntire_eq_xiZetaFactor_mul_zeta hs.1 hs.2

/-- At every nontrivial zero, xi and zeta have exactly the same analytic
order, before conversion to a natural-number multiplicity. -/
theorem IsNontrivialZetaZero.xiOrder_eq_zetaOrder
    {ρ : ℂ} (hρ : IsNontrivialZetaZero ρ) :
    analyticOrderAt riemannXiEntire ρ = analyticOrderAt riemannZeta ρ := by
  have hfactorAnalytic := analyticAt_xiZetaFactor_of_re_pos hρ.re_pos
  have hfactorOrder : analyticOrderAt xiZetaFactor ρ = 0 :=
    analyticOrderAt_eq_zero.mpr
      (Or.inr (xiZetaFactor_ne_zero_of_criticalStrip hρ.re_pos hρ.re_lt_one))
  have hcongr : analyticOrderAt riemannXiEntire ρ =
      analyticOrderAt (fun s ↦ xiZetaFactor s * riemannZeta s) ρ :=
    analyticOrderAt_congr
      (riemannXiEntire_eventuallyEq_xiZetaFactor_mul_zeta hρ)
  rw [hcongr]
  change analyticOrderAt (xiZetaFactor * riemannZeta) ρ = _
  rw [analyticOrderAt_mul hfactorAnalytic hρ.analyticAt, hfactorOrder, zero_add]

/-- Natural-number form of the exact order equality. -/
theorem IsNontrivialZetaZero.xiMultiplicity_eq_zetaMultiplicity
    {ρ : ℂ} (hρ : IsNontrivialZetaZero ρ) :
    analyticOrderNatAt riemannXiEntire ρ =
      analyticOrderNatAt riemannZeta ρ := by
  unfold analyticOrderNatAt
  rw [hρ.xiOrder_eq_zetaOrder]

/-- The multiplicity used by the actual Li tail is therefore exactly the
entire-xi multiplicity counted by Jensen. -/
theorem zetaZeroMultiplicity_eq_xi
    (ρ : NontrivialZetaZeroPoint) :
    zetaZeroMultiplicity ρ = analyticOrderNatAt riemannXiEntire ρ.1 := by
  exact ρ.2.xiMultiplicity_eq_zetaMultiplicity.symm

end RiemannLab
