import RiemannLab.Tasks.CompactZetaDivisor
import RiemannLab.Tasks.CriticalLineCriterion
import Mathlib.Analysis.SpecialFunctions.Pow.Continuity

namespace RiemannLab

open Filter Metric
open scoped Topology

/-!
Finite, multiplicity-aware zero sums for the von Mangoldt explicit formula.

This file deliberately separates the part now checked by Lean (compact
divisors and finite truncations) from the remaining analytic limit theorem.
`ChebyshevExplicitFormulaTarget` is a proposition to prove, not an axiom or a
claimed result.
-/

/-- A compact ball with a shrinking open neighbourhood of zeta's pole removed.
As `n` grows these regions exhaust every fixed point other than `1`. -/
def zetaZeroTruncationRegion (n : ℕ) : Set ℂ :=
  closedBall 0 n \ ball 1 (((n + 1 : ℕ) : ℝ)⁻¹)

theorem zetaZeroTruncationRegion_isCompact (n : ℕ) :
    IsCompact (zetaZeroTruncationRegion n) :=
  (isCompact_closedBall 0 n).diff isOpen_ball

theorem zetaZeroTruncationRegion_avoidsPole (n : ℕ) :
    zetaZeroTruncationRegion n ⊆ ({1} : Set ℂ)ᶜ := by
  intro s hs
  simp only [zetaZeroTruncationRegion, Set.mem_sdiff, mem_closedBall] at hs
  intro hs1
  subst s
  apply hs.2
  simp only [mem_ball, dist_self]
  positivity

/-- Every fixed point away from the pole lies in some compact truncation. -/
theorem exists_mem_zetaZeroTruncationRegion {s : ℂ} (hs : s ≠ 1) :
    ∃ n : ℕ, s ∈ zetaZeroTruncationRegion n := by
  obtain ⟨a, ha⟩ := exists_nat_ge ‖s‖
  obtain ⟨b, hb⟩ := exists_nat_one_div_lt (dist_pos.mpr hs)
  let n := max a b
  refine ⟨n, ?_⟩
  constructor
  · rw [mem_closedBall, dist_zero_right]
    exact ha.trans (by exact_mod_cast Nat.le_max_left a b)
  · rw [mem_ball, not_lt]
    rw [one_div] at hb
    exact (inv_anti₀ (by positivity) (by
      exact_mod_cast Nat.add_le_add_right (Nat.le_max_right a b) 1)).trans hb.le

/-- The nontrivial zeros in the `n`th compact truncation. The underlying
divisor already carries their multiplicities. -/
noncomputable def compactNontrivialZetaZeros (n : ℕ) : Finset ℂ :=
  by
    classical
    exact (compactZetaDivisorSupport (zetaZeroTruncationRegion n)
      (zetaZeroTruncationRegion_isCompact n)).filter IsNontrivialZetaZero

/-- The kernel `x^ρ / ρ` appearing in the classical explicit formula. -/
noncomputable def explicitFormulaZeroKernel (x : ℝ) (ρ : ℂ) : ℂ :=
  (x : ℂ) ^ ρ / ρ

/-- The meromorphic integrand whose contour shift produces the Chebyshev
explicit formula. -/
noncomputable def explicitFormulaContourKernel (x : ℝ) (s : ℂ) : ℂ :=
  (-logDeriv riemannZeta s) * ((x : ℂ) ^ s / s)

/-- A nontrivial zero cannot be the origin. -/
theorem IsNontrivialZetaZero.ne_zero {ρ : ℂ} (hρ : IsNontrivialZetaZero ρ) : ρ ≠ 0 := by
  intro h
  have hpos := hρ.re_pos
  rw [h] at hpos
  norm_num at hpos

/-- The full local residue of the explicit-formula contour kernel at a
nontrivial zero, including both multiplicity and the Perron weight. -/
theorem IsNontrivialZetaZero.tendsto_mul_explicitFormulaContourKernel
    {ρ : ℂ} (hρ : IsNontrivialZetaZero ρ) {x : ℝ} (hx : 0 < x) :
    Tendsto (fun s ↦ (s - ρ) * explicitFormulaContourKernel x s) (𝓝[≠] ρ)
      (𝓝 (-(analyticOrderNatAt riemannZeta ρ : ℂ) * explicitFormulaZeroKernel x ρ)) := by
  have hweight : Tendsto (fun s : ℂ ↦ (x : ℂ) ^ s / s) (𝓝[≠] ρ)
      (𝓝 ((x : ℂ) ^ ρ / ρ)) := by
    have hcontinuous : ContinuousAt (fun s : ℂ ↦ (x : ℂ) ^ s / s) ρ :=
      (continuousAt_const_cpow (Complex.ofReal_ne_zero.mpr hx.ne')).div
        continuousAt_id hρ.ne_zero
    exact hcontinuous.tendsto.mono_left nhdsWithin_le_nhds
  have hproduct := hρ.tendsto_mul_zetaLogDeriv.neg.mul hweight
  simpa [explicitFormulaContourKernel, explicitFormulaZeroKernel, mul_assoc,
    neg_mul] using hproduct

/-- The finite, symmetrically expanding nontrivial-zero contribution, with
each zero weighted by its divisor multiplicity. -/
noncomputable def truncatedNontrivialZeroContribution (n : ℕ) (x : ℝ) : ℂ :=
  ∑ ρ ∈ compactNontrivialZetaZeros n,
    (zetaDivisorOn (zetaZeroTruncationRegion n) ρ : ℂ) *
      explicitFormulaZeroKernel x ρ

/-- The finite residue ledger contributed by all nontrivial zeros in the
`n`th compact truncation. -/
noncomputable def truncatedNontrivialZeroResidueSum (n : ℕ) (x : ℝ) : ℂ :=
  ∑ ρ ∈ compactNontrivialZetaZeros n,
    -(zetaDivisorOn (zetaZeroTruncationRegion n) ρ : ℂ) *
      explicitFormulaZeroKernel x ρ

/-- The residue ledger is exactly the negative of the zero contribution in
the conventional explicit-formula sign convention. -/
theorem truncatedNontrivialZeroResidueSum_eq_neg (n : ℕ) (x : ℝ) :
    truncatedNontrivialZeroResidueSum n x =
      -truncatedNontrivialZeroContribution n x := by
  classical
  simp only [truncatedNontrivialZeroResidueSum, truncatedNontrivialZeroContribution,
    Finset.sum_neg_distrib, neg_mul]

/-- Every term selected by the finite truncation really is a nontrivial zeta
zero. -/
theorem mem_compactNontrivialZetaZeros {n : ℕ} {ρ : ℂ}
    (hρ : ρ ∈ compactNontrivialZetaZeros n) : IsNontrivialZetaZero ρ := by
  classical
  simpa [compactNontrivialZetaZeros] using (Finset.mem_filter.mp hρ).2

/-- On a compact truncation, the local contour residue agrees exactly with
the integer multiplicity stored in the compact zeta divisor. -/
theorem tendsto_mul_explicitFormulaContourKernel_eq_divisor
    {n : ℕ} {ρ : ℂ} (hρ : ρ ∈ compactNontrivialZetaZeros n)
    {x : ℝ} (hx : 0 < x) :
    Tendsto (fun s ↦ (s - ρ) * explicitFormulaContourKernel x s) (𝓝[≠] ρ)
      (𝓝 (-(zetaDivisorOn (zetaZeroTruncationRegion n) ρ : ℂ) *
        explicitFormulaZeroKernel x ρ)) := by
  classical
  have hzero := mem_compactNontrivialZetaZeros hρ
  have hregion : ρ ∈ zetaZeroTruncationRegion n := by
    have hsupp : ρ ∈ compactZetaDivisorSupport (zetaZeroTruncationRegion n)
        (zetaZeroTruncationRegion_isCompact n) :=
      (Finset.mem_filter.mp (by simpa [compactNontrivialZetaZeros] using hρ)).1
    exact (zetaDivisorOn (zetaZeroTruncationRegion n)).supportWithinDomain
      ((mem_compactZetaDivisorSupport
        (zetaZeroTruncationRegion_isCompact n)).mp hsupp)
  have hρ1 : ρ ≠ 1 := zetaZeroTruncationRegion_avoidsPole n hregion
  have hcast : (zetaDivisorOn (zetaZeroTruncationRegion n) ρ : ℂ) =
      (analyticOrderNatAt riemannZeta ρ : ℂ) := by
    rw [zetaDivisorOn_apply (zetaZeroTruncationRegion_avoidsPole n) hregion]
    have hfinite := zetaZeroOrder_ne_top hρ1
    rw [show zetaZeroOrder ρ = (analyticOrderNatAt riemannZeta ρ : ℕ) by
      exact (ENat.coe_toNat_eq_self.mpr hfinite).symm]
    simp
  simpa [hcast] using hzero.tendsto_mul_explicitFormulaContourKernel hx

/-- The compact finite sets exhaust all nontrivial zeros. -/
theorem IsNontrivialZetaZero.exists_mem_compactTruncation {ρ : ℂ}
    (hρ : IsNontrivialZetaZero ρ) :
    ∃ n : ℕ, ρ ∈ compactNontrivialZetaZeros n := by
  classical
  have hρ1 : ρ ≠ 1 := by
    intro h
    subst ρ
    have hlt := hρ.re_lt_one
    norm_num at hlt
  obtain ⟨n, hn⟩ := exists_mem_zetaZeroTruncationRegion hρ1
  have hsupport : ρ ∈ compactZetaDivisorSupport (zetaZeroTruncationRegion n)
      (zetaZeroTruncationRegion_isCompact n) :=
    (mem_compactZetaDivisorSupport_iff_zero
      (zetaZeroTruncationRegion_isCompact n)
      (zetaZeroTruncationRegion_avoidsPole n) hn).mpr hρ.1
  refine ⟨n, ?_⟩
  simp [compactNontrivialZetaZeros, hsupport, hρ]

/-- Every selected zero has strictly positive divisor multiplicity. -/
theorem compactNontrivialZetaZero_multiplicity_pos {n : ℕ} {ρ : ℂ}
    (hρ : ρ ∈ compactNontrivialZetaZeros n) :
    0 < zetaDivisorOn (zetaZeroTruncationRegion n) ρ := by
  classical
  have hsupport : ρ ∈ compactZetaDivisorSupport (zetaZeroTruncationRegion n)
      (zetaZeroTruncationRegion_isCompact n) :=
    (Finset.mem_filter.mp (by simpa [compactNontrivialZetaZeros] using hρ)).1
  have hne : zetaDivisorOn (zetaZeroTruncationRegion n) ρ ≠ 0 :=
    (mem_compactZetaDivisorSupport
      (zetaZeroTruncationRegion_isCompact n)).mp hsupport
  exact lt_of_le_of_ne
    ((zetaDivisorOn_nonneg (zetaZeroTruncationRegion_avoidsPole n)) ρ) hne.symm

/-- The elementary (pole and trivial-zero) term in the classical explicit
formula, written over the reals for `x > 1`. -/
noncomputable def explicitFormulaArchimedeanTerm (x : ℝ) : ℝ :=
  Real.log (2 * Real.pi) + (1 / 2 : ℝ) * Real.log (1 - x⁻¹ ^ 2)

/-- The remaining explicit-formula theorem required by the selected psi route.

For nonintegral `x > 1`, the finite multiplicity-weighted sums must converge to
the negative psi remainder minus the elementary pole/trivial-zero term. The
nonintegrality hypothesis avoids having to choose a half-weight convention at
jump points of `Chebyshev.psi`.
-/
def ChebyshevExplicitFormulaTarget : Prop :=
  ∀ x : ℝ, 1 < x → (∀ m : ℕ, x ≠ m) →
    Tendsto (fun n : ℕ ↦ truncatedNontrivialZeroContribution n x) atTop
      (𝓝 (-(chebyshevPsiRemainder x : ℂ) - explicitFormulaArchimedeanTerm x))

/-- Unfolded form of the exact analytic bridge still to prove. -/
theorem chebyshevExplicitFormulaTarget_iff :
    ChebyshevExplicitFormulaTarget ↔
      ∀ x : ℝ, 1 < x → (∀ m : ℕ, x ≠ m) →
        Tendsto (fun n : ℕ ↦ truncatedNontrivialZeroContribution n x) atTop
          (𝓝 (-(chebyshevPsiRemainder x : ℂ) - explicitFormulaArchimedeanTerm x)) :=
  Iff.rfl

end RiemannLab
