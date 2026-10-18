import RiemannLab.Tasks.RiemannLiArithmeticLedger
import RiemannLab.Tasks.ExplicitFormula

namespace RiemannLab

open Filter Topology

/-!
# The exact Taylor-to-zero-sum bridge

This file puts the classical Li zero sum on the same compact,
multiplicity-aware zeta divisor already used by the explicit-formula module.
It isolates the one missing global theorem: convergence of these symmetric
truncations to the Taylor coefficients of the completed xi logarithmic
derivative.
-/

/-- The multiplicity-weighted Li sum over the checked compact zeta divisor. -/
noncomputable def truncatedRiemannLiZeroSum (cutoff index : ℕ) : ℂ :=
  ∑ ρ ∈ compactNontrivialZetaZeros cutoff,
    (zetaDivisorOn (zetaZeroTruncationRegion cutoff) ρ : ℂ) *
      liZeroMode index ρ

@[simp] theorem truncatedRiemannLiZeroSum_zero (cutoff : ℕ) :
    truncatedRiemannLiZeroSum cutoff 0 = 0 := by
  simp [truncatedRiemannLiZeroSum, liZeroMode]

/-- On every selected point, the compact-divisor weight is its literal
analytic zeta multiplicity. -/
theorem zetaDivisorOn_eq_analyticMultiplicity_of_mem
    {cutoff : ℕ} {ρ : ℂ} (hρ : ρ ∈ compactNontrivialZetaZeros cutoff) :
    (zetaDivisorOn (zetaZeroTruncationRegion cutoff) ρ : ℂ) =
      (analyticOrderNatAt riemannZeta ρ : ℂ) := by
  classical
  have hregion : ρ ∈ zetaZeroTruncationRegion cutoff := by
    have hsupp : ρ ∈ compactZetaDivisorSupport
        (zetaZeroTruncationRegion cutoff)
        (zetaZeroTruncationRegion_isCompact cutoff) :=
      (Finset.mem_filter.mp
        (by simpa [compactNontrivialZetaZeros] using hρ)).1
    exact (zetaDivisorOn (zetaZeroTruncationRegion cutoff)).supportWithinDomain
      ((mem_compactZetaDivisorSupport
        (zetaZeroTruncationRegion_isCompact cutoff)).mp hsupp)
  have hρ1 : ρ ≠ 1 := zetaZeroTruncationRegion_avoidsPole cutoff hregion
  rw [zetaDivisorOn_apply (zetaZeroTruncationRegion_avoidsPole cutoff) hregion]
  have hfinite := zetaZeroOrder_ne_top hρ1
  rw [show zetaZeroOrder ρ = (analyticOrderNatAt riemannZeta ρ : ℕ) by
    exact (ENat.coe_toNat_eq_self.mpr hfinite).symm]
  simp

/-- The finite truncation can therefore be read without any implementation
detail of the compact divisor. -/
theorem truncatedRiemannLiZeroSum_eq_analyticMultiplicity
    (cutoff index : ℕ) :
    truncatedRiemannLiZeroSum cutoff index =
      ∑ ρ ∈ compactNontrivialZetaZeros cutoff,
        (analyticOrderNatAt riemannZeta ρ : ℂ) * liZeroMode index ρ := by
  classical
  apply Finset.sum_congr rfl
  intro ρ hρ
  rw [zetaDivisorOn_eq_analyticMultiplicity_of_mem hρ]

/-- The precise classical Hadamard-product obligation.  The truncation is
fixed, symmetric, exhaustive, and carries analytic multiplicities. -/
def RiemannLiTaylorZeroSumBridge : Prop :=
  ∀ index : ℕ,
    Tendsto (fun cutoff : ℕ ↦ truncatedRiemannLiZeroSum cutoff index) atTop
      (𝓝 (riemannLiCoefficient index : ℂ))

/-- The zeroth row of the bridge is already unconditional. -/
theorem riemannLiTaylorZeroSumBridge_zero :
    Tendsto (fun cutoff : ℕ ↦ truncatedRiemannLiZeroSum cutoff 0) atTop
      (𝓝 (riemannLiCoefficient 0 : ℂ)) := by
  simp

/-- Once the classical bridge is supplied, the literal zero sum and the
literal prime--Gamma--pole ledger have the same limit coefficient. -/
theorem RiemannLiTaylorZeroSumBridge.tendsto_arithmeticLedger
    (h : RiemannLiTaylorZeroSumBridge) (index : ℕ) :
    Tendsto (fun cutoff : ℕ ↦ truncatedRiemannLiZeroSum cutoff index) atTop
      (𝓝 ((riemannLiSInfinity index - riemannLiSFinite index +
        (if index = 0 then 0 else 1) : ℝ) : ℂ)) := by
  simpa [riemannLiCoefficient_eq_arithmeticLedger] using h index

end RiemannLab
