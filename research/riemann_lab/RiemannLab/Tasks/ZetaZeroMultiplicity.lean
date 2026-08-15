import RiemannLab.Tasks.NontrivialZeros
import Mathlib.Analysis.Analytic.Order
import Mathlib.Analysis.Calculus.LogDeriv

namespace RiemannLab

open Filter
open scoped Topology

/-!
Multiplicity-aware infrastructure for zeta zeros. We use the analytic order in
`ℕ∞`; proving finite support on compact regions and integrating this with the
complex divisor API are the next explicit-formula milestones.
-/

/-- Analytic vanishing order of zeta at a point. -/
noncomputable def zetaZeroOrder (s : ℂ) : ℕ∞ :=
  analyticOrderAt riemannZeta s

/-- Zeta is analytic at every nontrivial zero. -/
theorem IsNontrivialZetaZero.analyticAt {s : ℂ}
    (hs : IsNontrivialZetaZero s) : AnalyticAt ℂ riemannZeta s := by
  apply analyticOn_riemannZeta
  intro hs1
  subst s
  have hlt := hs.re_lt_one
  norm_num at hlt

/-- A nontrivial zero has nonzero analytic vanishing order. -/
theorem IsNontrivialZetaZero.zetaZeroOrder_ne_zero {s : ℂ}
    (hs : IsNontrivialZetaZero s) : zetaZeroOrder s ≠ 0 := by
  exact analyticOrderAt_ne_zero.mpr ⟨hs.analyticAt, hs.1⟩

/-- Away from the pole, vanishing order zero is equivalent to zeta being nonzero. -/
theorem zetaZeroOrder_eq_zero_iff {s : ℂ} (hs : s ≠ 1) :
    zetaZeroOrder s = 0 ↔ riemannZeta s ≠ 0 := by
  unfold zetaZeroOrder
  apply AnalyticAt.analyticOrderAt_eq_zero
  exact analyticOn_riemannZeta s (by simpa using hs)

/-- The logarithmic derivative of an analytic function has residue equal to
its full vanishing order.  This is the multiplicity-aware generalization of
Mathlib's simple-zero logarithmic-residue theorem. -/
theorem AnalyticAt.tendsto_mul_logDeriv_zeroOrder
    {f : ℂ → ℂ} {z₀ : ℂ} (hf : AnalyticAt ℂ f z₀)
    (hfinite : analyticOrderAt f z₀ ≠ ⊤) :
    Tendsto (fun z ↦ (z - z₀) * logDeriv f z) (𝓝[≠] z₀)
      (𝓝 (analyticOrderNatAt f z₀ : ℂ)) := by
  have horder : analyticOrderAt f z₀ = (analyticOrderNatAt f z₀ : ℕ) := by
    exact (ENat.coe_toNat_eq_self.mpr hfinite).symm
  obtain ⟨g, hgAnalytic, hg0, hfactor⟩ :=
    (hf.analyticOrderAt_eq_natCast.mp horder)
  have hgEventually : ∀ᶠ z in 𝓝 z₀, g z ≠ 0 :=
    (hgAnalytic.continuousAt.ne_iff_eventually_ne continuousAt_const).mp hg0
  have hsmall : Tendsto (fun z : ℂ ↦ (z - z₀) * logDeriv g z)
      (𝓝[≠] z₀) (𝓝 0) := by
    have hfirst : Tendsto (fun z : ℂ ↦ z - z₀) (𝓝[≠] z₀) (𝓝 0) := by
      change Tendsto (id - fun _ : ℂ ↦ z₀) (𝓝[≠] z₀) (𝓝 0)
      convert (continuousAt_id.sub
        (continuousAt_const (x := z₀) (y := z₀) : ContinuousAt (fun _ : ℂ ↦ z₀) z₀))
        |>.continuousWithinAt.tendsto using 1 <;> simp
    have hsecond : Tendsto (logDeriv g) (𝓝[≠] z₀) (𝓝 (logDeriv g z₀)) := by
      exact (hgAnalytic.deriv.continuousAt.div hgAnalytic.continuousAt hg0).tendsto.mono_left
        nhdsWithin_le_nhds
    simpa using hfirst.mul hsecond
  have hmodel : Tendsto
      (fun z : ℂ ↦ (analyticOrderNatAt f z₀ : ℂ) + (z - z₀) * logDeriv g z)
      (𝓝[≠] z₀) (𝓝 (analyticOrderNatAt f z₀ : ℂ)) := by
    simpa using tendsto_const_nhds.add hsmall
  apply hmodel.congr'
  have hfactorNE : f =ᶠ[𝓝[≠] z₀]
      (fun z ↦ (z - z₀) ^ analyticOrderNatAt f z₀ * g z) :=
    hfactor.filter_mono nhdsWithin_le_nhds
  have hderivNE : deriv f =ᶠ[𝓝[≠] z₀]
      deriv (fun z ↦ (z - z₀) ^ analyticOrderNatAt f z₀ * g z) :=
    Filter.EventuallyEq.nhdsNE_deriv hfactorNE
  filter_upwards [hfactorNE, hderivNE,
      hgEventually.filter_mono nhdsWithin_le_nhds,
      hgAnalytic.eventually_analyticAt.filter_mono nhdsWithin_le_nhds,
      self_mem_nhdsWithin] with z hz hz' hgz hgzAnalytic hz0
  have hsub : z - z₀ ≠ 0 := sub_ne_zero.mpr hz0
  have hpowDiff : DifferentiableAt ℂ (fun w : ℂ ↦ (w - z₀) ^ analyticOrderNatAt f z₀) z :=
    by fun_prop
  have hpow0 : (z - z₀) ^ analyticOrderNatAt f z₀ ≠ 0 := pow_ne_zero _ hsub
  have hlog : logDeriv f z =
      logDeriv (fun w : ℂ ↦ (w - z₀) ^ analyticOrderNatAt f z₀ * g w) z := by
    simp only [logDeriv_apply]
    rw [hz, hz']
  have hshiftLog : logDeriv (fun w : ℂ ↦ w - z₀) z = 1 / (z - z₀) := by
    have hd : HasDerivAt (fun w : ℂ ↦ w - z₀) 1 z := by
      simpa only [id_eq] using (hasDerivAt_id z).sub_const z₀
    rw [logDeriv_apply, hd.deriv]
  rw [hlog, logDeriv_mul z hpow0 hgz hpowDiff hgzAnalytic.differentiableAt,
    logDeriv_fun_pow (by fun_prop), hshiftLog]
  field_simp

end RiemannLab
