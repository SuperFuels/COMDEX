import RiemannLab.Tasks.LiPrimeTailEnvelope

namespace RiemannLab

open MeasureTheory

/-!
# Explicit PNT interface for the Li tail programme

The numerical constants here deliberately define a clean, slightly relaxed
envelope of the classical `x * polylog(x) * exp(-c * sqrt(log x))` form.  The
deep analytic theorem establishing such an envelope is kept as a proposition,
not introduced as an axiom.
-/

/-- A convenient explicit de la Vallee Poussin type envelope. -/
noncomputable def explicitPNTEnvelope (x : ℝ) : ℝ :=
  10 * x * (Real.log x) ^ 2 *
    Real.exp (-(4 / 5 : ℝ) * Real.sqrt (Real.log x))

/-- The external classical theorem which must be reconstructed in Lean. -/
def ExplicitChebyshevPNTBound : Prop :=
  ∀ x : ℝ, 3 ≤ x →
    |chebyshevPsiRemainder x| ≤ explicitPNTEnvelope x

theorem continuousOn_explicitPNTEnvelope :
    ContinuousOn explicitPNTEnvelope (Set.Ioi 1) := by
  unfold explicitPNTEnvelope
  have hid : ContinuousOn (fun x : ℝ ↦ x) (Set.Ioi 1) :=
    continuous_id.continuousOn
  have hlog : ContinuousOn Real.log (Set.Ioi 1) := by
    simpa only using hid.log (fun x hx ↦ ne_of_gt (zero_lt_one.trans hx))
  have harg : ContinuousOn
      (fun x : ℝ ↦ -(4 / 5 : ℝ) * Real.sqrt (Real.log x))
      (Set.Ioi 1) :=
    continuousOn_const.mul hlog.sqrt
  have hexp : ContinuousOn
      (fun x : ℝ ↦ Real.exp (-(4 / 5 : ℝ) * Real.sqrt (Real.log x)))
      (Set.Ioi 1) := by
    simpa only [Function.comp_def] using
      Real.continuous_exp.comp_continuousOn harg
  exact (((continuousOn_const.mul hid).mul (hlog.pow 2)).mul hexp)

/-- The explicit envelope is integrable against every fixed Li derivative on
finite cutoff intervals. -/
theorem integrableOn_liDeriv_mul_explicitPNTEnvelope
    (n N M : ℕ) (hN : 3 ≤ N) :
    IntegrableOn
      (fun t ↦ |deriv (riemannLiAnalyticPrimeWeight n) t| *
        explicitPNTEnvelope t)
      (Set.Ioc (N : ℝ) M) := by
  have hderiv : ContinuousOn (deriv (riemannLiAnalyticPrimeWeight n))
      (Set.Ioi 0) :=
    (contDiffOn_riemannLiAnalyticPrimeWeight n).continuousOn_deriv_of_isOpen
      isOpen_Ioi (by norm_num)
  have hsubset0 : Set.Icc (N : ℝ) M ⊆ Set.Ioi (0 : ℝ) := by
    intro x hx
    have hNreal : (3 : ℝ) ≤ N := by exact_mod_cast hN
    exact lt_of_lt_of_le (by norm_num) (hNreal.trans hx.1)
  have hsubset1 : Set.Icc (N : ℝ) M ⊆ Set.Ioi (1 : ℝ) := by
    intro x hx
    have hNreal : (3 : ℝ) ≤ N := by exact_mod_cast hN
    exact lt_of_lt_of_le (by norm_num) (hNreal.trans hx.1)
  have hcont : ContinuousOn
      (fun t ↦ |deriv (riemannLiAnalyticPrimeWeight n) t| *
        explicitPNTEnvelope t) (Set.Icc (N : ℝ) M) :=
    (hderiv.mono hsubset0).abs.mul
      (continuousOn_explicitPNTEnvelope.mono hsubset1)
  exact hcont.integrableOn_Icc.mono_set Set.Ioc_subset_Icc_self

/-- Conditional installation of the explicit PNT envelope into the checked
Li tail machinery. -/
theorem abs_riemannLiPrimeCutoffEnergy_sub_le_explicitPNT
    (hPNT : ExplicitChebyshevPNTBound)
    (n N M : ℕ) (hN : 3 ≤ N) (hNM : N ≤ M) :
    |riemannLiPrimeCutoffEnergy n M - riemannLiPrimeCutoffEnergy n N| ≤
      riemannLiEnvelopeRadius explicitPNTEnvelope n N M := by
  apply abs_riemannLiPrimeCutoffEnergy_sub_le_envelope
    explicitPNTEnvelope n N M (hN.trans' (by norm_num)) hNM
  · intro x hx
    apply hPNT x
    have hNreal : (3 : ℝ) ≤ N := by exact_mod_cast hN
    exact hNreal.trans hx.1
  · exact integrableOn_liDeriv_mul_explicitPNTEnvelope n N M hN

/-! ## Logical status of the checkpoint margin -/

/-- Any convergent real sequence with a strictly positive limit eventually
admits a checkpoint whose uniform tail radius fits below the checkpoint.
Thus existence of such margins is essentially a positivity statement, not a
consequence of convergence alone. -/
theorem exists_uniform_cutoff_margin_of_pos_limit
    {energy : ℕ → ℝ} {limit : ℝ}
    (hlim : Filter.Tendsto energy Filter.atTop (nhds limit))
    (hpos : 0 < limit) :
    ∃ N : ℕ, ∃ radius : ℝ,
      0 ≤ radius ∧
      (∀ M, N ≤ M → |energy M - energy N| ≤ radius) ∧
      radius ≤ energy N := by
  obtain ⟨N, hN⟩ := (Metric.tendsto_atTop.mp hlim)
    (limit / 4) (by positivity)
  refine ⟨N, limit / 2, by positivity, ?_, ?_⟩
  · intro M hM
    have hM' := hN M hM
    have hN' := hN N le_rfl
    rw [Real.dist_eq] at hM' hN'
    calc
      |energy M - energy N| =
          |(energy M - limit) - (energy N - limit)| := by ring_nf
      _ ≤ |energy M - limit| + |energy N - limit| := abs_sub _ _
      _ ≤ limit / 4 + limit / 4 := (add_lt_add hM' hN').le
      _ = limit / 2 := by ring
  · have hN' := hN N le_rfl
    rw [Real.dist_eq] at hN'
    have hlower := (abs_lt.mp hN').1
    linarith

end RiemannLab
