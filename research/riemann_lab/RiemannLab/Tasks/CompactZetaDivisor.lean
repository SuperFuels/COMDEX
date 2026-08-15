import RiemannLab.Tasks.ZetaZeroMultiplicity
import Mathlib.Analysis.Meromorphic.Divisor

namespace RiemannLab

open MeromorphicOn
open Filter
open scoped Topology

/-!
A compact, multiplicity-aware divisor for the zeros of the Riemann zeta function.

Mathlib currently exposes zeta as analytic on `{1}ᶜ`, rather than as a globally
meromorphic function.  Consequently every theorem below records explicitly that
the compact region avoids the pole at `1`.  This is enough for compact
exhaustions of the nontrivial zeros and prevents the pole from being silently
treated as a zero.
-/

/-- The zeta divisor restricted to a set `K`. Its integer values are vanishing
orders; outside `K` it is zero. -/
noncomputable def zetaDivisorOn (K : Set ℂ) :
    Function.locallyFinsuppWithin K ℤ :=
  divisor riemannZeta K

/-- Zeta is analytic on any region which avoids its pole at `1`. -/
theorem analyticOnNhd_riemannZeta_of_avoidsPole {K : Set ℂ}
    (hK : K ⊆ ({1} : Set ℂ)ᶜ) : AnalyticOnNhd ℂ riemannZeta K :=
  analyticOn_riemannZeta.mono hK

/-- On a compact set, only finitely many entries of the zeta divisor are nonzero. -/
theorem zetaDivisorOn_support_finite {K : Set ℂ} (hK : IsCompact K) :
    (zetaDivisorOn K).support.Finite :=
  (zetaDivisorOn K).finiteSupport hK

/-- Pointwise identification of the divisor with the analytic vanishing order. -/
theorem zetaDivisorOn_apply {K : Set ℂ} (havoid : K ⊆ ({1} : Set ℂ)ᶜ)
    {s : ℂ} (hs : s ∈ K) :
    zetaDivisorOn K s = ((zetaZeroOrder s).map (↑)).untop₀ := by
  exact (analyticOnNhd_riemannZeta_of_avoidsPole havoid).divisor_apply hs

/-- The compact zeta divisor has nonnegative multiplicities. -/
theorem zetaDivisorOn_nonneg {K : Set ℂ} (havoid : K ⊆ ({1} : Set ℂ)ᶜ) :
    0 ≤ zetaDivisorOn K :=
  (analyticOnNhd_riemannZeta_of_avoidsPole havoid).divisor_nonneg

/-- Zeta has finite analytic order at every point other than its pole.  The
proof propagates finiteness from `2`, where zeta is nonzero, across the
connected punctured plane. -/
theorem zetaZeroOrder_ne_top {s : ℂ} (hs : s ≠ 1) : zetaZeroOrder s ≠ ⊤ := by
  have hconnected : IsPreconnected (({1} : Set ℂ)ᶜ) :=
    (isConnected_compl_singleton_of_one_lt_rank (by simp) (1 : ℂ)).isPreconnected
  have h2mem : (2 : ℂ) ∈ ({1} : Set ℂ)ᶜ := by norm_num
  have hsmem : s ∈ ({1} : Set ℂ)ᶜ := by simpa using hs
  have h2order : zetaZeroOrder (2 : ℂ) = 0 := by
    apply (analyticOn_riemannZeta (2 : ℂ) h2mem).analyticOrderAt_eq_zero.mpr
    exact riemannZeta_ne_zero_of_one_le_re (by norm_num)
  exact analyticOn_riemannZeta.analyticOrderAt_ne_top_of_isPreconnected
    hconnected h2mem hsmem (by
      change zetaZeroOrder (2 : ℂ) ≠ ⊤
      simp [h2order])

/-- At every nontrivial zeta zero, the residue of `ζ'/ζ` is its complete
analytic multiplicity. -/
theorem IsNontrivialZetaZero.tendsto_mul_zetaLogDeriv {ρ : ℂ}
    (hρ : IsNontrivialZetaZero ρ) :
    Filter.Tendsto (fun s ↦ (s - ρ) * logDeriv riemannZeta s)
      (nhdsWithin ρ {ρ}ᶜ) (𝓝 (analyticOrderNatAt riemannZeta ρ : ℂ)) := by
  have hρ1 : ρ ≠ 1 := by
    intro h
    subst ρ
    have hlt := hρ.re_lt_one
    norm_num at hlt
  simpa using
    RiemannLab.AnalyticAt.tendsto_mul_logDeriv_zeroOrder hρ.analyticAt
      (zetaZeroOrder_ne_top hρ1)

/-- The finite set of points carrying nonzero zeta multiplicity in `K`. -/
noncomputable def compactZetaDivisorSupport (K : Set ℂ) (hK : IsCompact K) : Finset ℂ :=
  (zetaDivisorOn_support_finite hK).toFinset

@[simp]
theorem mem_compactZetaDivisorSupport {K : Set ℂ} (hK : IsCompact K) {s : ℂ} :
    s ∈ compactZetaDivisorSupport K hK ↔ zetaDivisorOn K s ≠ 0 := by
  simp [compactZetaDivisorSupport, Function.mem_support]

/-- On an admissible compact region, the support of the divisor is exactly the
zero set of zeta. -/
theorem mem_compactZetaDivisorSupport_iff_zero {K : Set ℂ} (hK : IsCompact K)
    (havoid : K ⊆ ({1} : Set ℂ)ᶜ) {s : ℂ} (hs : s ∈ K) :
    s ∈ compactZetaDivisorSupport K hK ↔ riemannZeta s = 0 := by
  rw [mem_compactZetaDivisorSupport, zetaDivisorOn_apply havoid hs]
  simp [WithTop.untop₀_eq_zero, zetaZeroOrder_ne_top (by simpa using havoid hs),
    zetaZeroOrder_eq_zero_iff (by simpa using havoid hs)]

/-- A finite weighted sum over zeta zeros in a compact region, with every zero
counted according to its divisor multiplicity. -/
noncomputable def compactZetaZeroSum (K : Set ℂ) (hK : IsCompact K)
    (weight : ℂ → ℂ) : ℂ :=
  ∑ s ∈ compactZetaDivisorSupport K hK, (zetaDivisorOn K s : ℂ) * weight s

@[simp]
theorem compactZetaZeroSum_zero (K : Set ℂ) (hK : IsCompact K) :
    compactZetaZeroSum K hK 0 = 0 := by
  simp [compactZetaZeroSum]

end RiemannLab
