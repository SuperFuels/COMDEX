import RiemannLab.Tasks.LiPrimeTailAbel

namespace RiemannLab

open MeasureTheory
open scoped ArithmeticFunction.vonMangoldt

/-!
# Prime-number-theorem envelopes for the Li cutoff tail

This file converts any independently proved pointwise envelope for
`|psi(x) - x|` into a certified Li cutoff-tail radius.
-/

/-- The two integrals in the Abel ledger are exactly one integral against
the Chebyshev remainder. -/
theorem riemannLiPsiIntegral_sub_main_eq_remainder
    (n N M : ℕ) (hN : 1 ≤ N) :
    ((∫ t in Set.Ioc (N : ℝ) M,
        deriv (riemannLiAnalyticPrimeWeight n) t * Chebyshev.psi t) -
      ∫ t in Set.Ioc (N : ℝ) M,
        deriv (riemannLiAnalyticPrimeWeight n) t * t) =
      ∫ t in Set.Ioc (N : ℝ) M,
        deriv (riemannLiAnalyticPrimeWeight n) t *
          chebyshevPsiRemainder t := by
  have hderiv := integrableOn_deriv_riemannLiAnalyticPrimeWeight n N M hN
  have hN0 : (0 : ℝ) ≤ N := by positivity
  have hpsiIcc : IntegrableOn
      (fun t ↦ deriv (riemannLiAnalyticPrimeWeight n) t * Chebyshev.psi t)
      (Set.Icc (N : ℝ) M) := by
    simpa only [Chebyshev.psi_eq_sum_Icc] using
      (integrableOn_mul_sum_Icc
        (fun k ↦ ArithmeticFunction.vonMangoldt k) hN0 hderiv)
  have hmainIcc : IntegrableOn
      (fun t ↦ deriv (riemannLiAnalyticPrimeWeight n) t * t)
      (Set.Icc (N : ℝ) M) :=
    hderiv.mul_continuousOn continuousOn_id isCompact_Icc
  have hsubset : Set.Ioc (N : ℝ) M ⊆ Set.Icc (N : ℝ) M :=
    Set.Ioc_subset_Icc_self
  have hpsi := hpsiIcc.mono_set hsubset
  have hmain := hmainIcc.mono_set hsubset
  rw [← integral_sub hpsi hmain]
  apply integral_congr_ae
  filter_upwards with t
  simp only [chebyshevPsiRemainder]
  ring

/-- Radius obtained from a nonnegative pointwise envelope for
`|psi(x)-x|`. -/
noncomputable def riemannLiEnvelopeRadius
    (envelope : ℝ → ℝ) (n N M : ℕ) : ℝ :=
  |riemannLiAnalyticPrimeWeight n M| * envelope M +
    |riemannLiAnalyticPrimeWeight n N| * envelope N +
      ∫ t in Set.Ioc (N : ℝ) M,
        |deriv (riemannLiAnalyticPrimeWeight n) t| * envelope t

/-- A pointwise prime-number-theorem envelope bounds the exact finite cutoff
oscillation.  Every quantity in the conclusion is independent of zeros and
Li positivity. -/
theorem abs_riemannLiPrimeCutoffEnergy_sub_le_envelope
    (envelope : ℝ → ℝ) (n N M : ℕ) (hN : 1 ≤ N) (hNM : N ≤ M)
    (henvelope : ∀ x ∈ Set.Icc (N : ℝ) M,
      |chebyshevPsiRemainder x| ≤ envelope x)
    (hintegrable : IntegrableOn
      (fun t ↦ |deriv (riemannLiAnalyticPrimeWeight n) t| * envelope t)
      (Set.Ioc (N : ℝ) M)) :
    |riemannLiPrimeCutoffEnergy n M - riemannLiPrimeCutoffEnergy n N| ≤
      riemannLiEnvelopeRadius envelope n N M := by
  rw [riemannLiPrimeCutoffEnergy_sub_eq_neg_tail n N M hNM, abs_neg,
    riemannLiCompensatedPrimeTail_eq_psiRemainder_unconditional n N M hN hNM,
    riemannLiPsiIntegral_sub_main_eq_remainder n N M hN]
  have hintegral :
      |∫ t in Set.Ioc (N : ℝ) M,
          deriv (riemannLiAnalyticPrimeWeight n) t *
            chebyshevPsiRemainder t| ≤
        ∫ t in Set.Ioc (N : ℝ) M,
          |deriv (riemannLiAnalyticPrimeWeight n) t| * envelope t := by
    change ‖∫ t in Set.Ioc (N : ℝ) M,
      deriv (riemannLiAnalyticPrimeWeight n) t *
        chebyshevPsiRemainder t‖ ≤ _
    apply norm_integral_le_of_norm_le hintegrable
    apply ae_restrict_of_forall_mem measurableSet_Ioc
    intro x hx
    simp only [Real.norm_eq_abs, abs_mul]
    exact mul_le_mul_of_nonneg_left
      (henvelope x ⟨hx.1.le, hx.2⟩) (abs_nonneg _)
  calc
    |_ - _ - _| ≤ |_| + |_| + |_| := by
      have hthree (a b c : ℝ) : |a - b - c| ≤ |a| + |b| + |c| := by
        calc
          |a - b - c| ≤ |a - b| + |c| := abs_sub _ _
          _ ≤ (|a| + |b|) + |c| := add_le_add (abs_sub a b) le_rfl
          _ = |a| + |b| + |c| := rfl
      exact hthree _ _ _
    _ ≤ |riemannLiAnalyticPrimeWeight n M| * envelope M +
          |riemannLiAnalyticPrimeWeight n N| * envelope N +
            (∫ t in Set.Ioc (N : ℝ) M,
              |deriv (riemannLiAnalyticPrimeWeight n) t| * envelope t) := by
      simp only [abs_mul]
      exact add_le_add
        (add_le_add
          (mul_le_mul_of_nonneg_left
            (henvelope (M : ℝ) ⟨by exact_mod_cast hNM, le_rfl⟩) (abs_nonneg _))
          (mul_le_mul_of_nonneg_left
            (henvelope (N : ℝ) ⟨le_rfl, by exact_mod_cast hNM⟩) (abs_nonneg _)))
        hintegral
    _ = riemannLiEnvelopeRadius envelope n N M := rfl

/-! ## Exact limitation of the pinned Chebyshev bound -/

/-- The linear envelope available from pinned Mathlib's elementary Chebyshev
estimate. -/
noncomputable def linearChebyshevEnvelope (x : ℝ) : ℝ :=
  (Real.log 4 + 5) * x

/-- The elementary library estimate gives a valid linear bound for the
Chebyshev remainder. -/
theorem abs_chebyshevPsiRemainder_le_linearEnvelope
    {x : ℝ} (hx : 0 ≤ x) :
    |chebyshevPsiRemainder x| ≤ linearChebyshevEnvelope x := by
  have hpsi0 := Chebyshev.psi_nonneg x
  have hpsi := Chebyshev.psi_le_const_mul_self hx
  have hlog : 0 ≤ Real.log 4 := Real.log_nonneg (by norm_num)
  rw [abs_le]
  constructor <;> simp only [chebyshevPsiRemainder, linearChebyshevEnvelope]
  · nlinarith
  · nlinarith

@[simp] theorem liPrimeWeightPolynomial_one (x : ℝ) :
    liPrimeWeightPolynomial 1 x = 1 := by
  norm_num [liPrimeWeightPolynomial]

/-- Already for the first Li weight, the linear Chebyshev envelope leaves a
nonvanishing boundary cost.  Hence this elementary estimate cannot prove
cutoff convergence through the absolute-value tail method. -/
theorem linearEnvelope_first_boundary_eq
    {x : ℝ} (hx : 0 < x) :
    |riemannLiAnalyticPrimeWeight 1 x| * linearChebyshevEnvelope x =
      Real.log 4 + 5 := by
  rw [riemannLiAnalyticPrimeWeight, liPrimeWeightPolynomial_one,
    linearChebyshevEnvelope, abs_div, abs_one, abs_of_pos hx]
  field_simp

end RiemannLab
