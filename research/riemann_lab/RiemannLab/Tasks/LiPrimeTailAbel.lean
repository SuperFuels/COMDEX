import RiemannLab.Tasks.LiPrimeCutoffEnergy
import Mathlib.NumberTheory.AbelSummation

namespace RiemannLab

open MeasureTheory
open scoped ArithmeticFunction.vonMangoldt

/-!
# Abel decomposition of the Li prime-cutoff tail

This file exposes the exact location of the required cancellation.  The raw
von Mangoldt tail is transformed into boundary values of `psi` and an
integral remainder.  No zero-side hypothesis and no Li positivity assumption
is used.
-/

/-- The smooth weight whose values at integers occur in the finite Li prime
sum. -/
noncomputable def riemannLiAnalyticPrimeWeight (n : ℕ) (x : ℝ) : ℝ :=
  liPrimeWeightPolynomial n (Real.log x) / x

theorem contDiffOn_riemannLiAnalyticPrimeWeight (n : ℕ) :
    ContDiffOn ℝ 1 (riemannLiAnalyticPrimeWeight n) (Set.Ioi 0) := by
  unfold riemannLiAnalyticPrimeWeight liPrimeWeightPolynomial
  have hid : ContDiffOn ℝ 1 (fun x : ℝ ↦ x) (Set.Ioi 0) := by
    exact contDiffOn_id
  have hlog : ContDiffOn ℝ 1 Real.log (Set.Ioi 0) := by
    simpa only using hid.log (fun x hx ↦ ne_of_gt hx)
  have hnum : ContDiffOn ℝ 1
      (fun x : ℝ ↦ ∑ j ∈ Finset.range n,
        (n.choose (j + 1) : ℝ) * Real.log x ^ j / (j.factorial : ℝ))
      (Set.Ioi 0) := by
    apply ContDiffOn.sum
    intro j hj
    exact (contDiffOn_const.mul (hlog.pow j)).div_const _
  exact hnum.div hid (fun x hx ↦ ne_of_gt hx)

theorem differentiableAt_riemannLiAnalyticPrimeWeight_of_pos
    (n : ℕ) {x : ℝ} (hx : 0 < x) :
    DifferentiableAt ℝ (riemannLiAnalyticPrimeWeight n) x := by
  exact ((contDiffOn_riemannLiAnalyticPrimeWeight n).contDiffAt
    (isOpen_Ioi.mem_nhds hx)).differentiableAt (by norm_num)

theorem integrableOn_deriv_riemannLiAnalyticPrimeWeight
    (n N M : ℕ) (hN : 1 ≤ N) :
    IntegrableOn (deriv (riemannLiAnalyticPrimeWeight n))
      (Set.Icc (N : ℝ) M) := by
  have hcont : ContinuousOn (deriv (riemannLiAnalyticPrimeWeight n))
      (Set.Ioi 0) :=
    (contDiffOn_riemannLiAnalyticPrimeWeight n).continuousOn_deriv_of_isOpen
      isOpen_Ioi (by norm_num)
  apply ContinuousOn.integrableOn_Icc
  apply hcont.mono
  intro x hx
  have hNreal : (1 : ℝ) ≤ N := by exact_mod_cast hN
  exact lt_of_lt_of_le zero_lt_one (hNreal.trans hx.1)

/-- The compensation polynomial differentiates to the prime weight
polynomial. -/
theorem hasDerivAt_liPrimeCutoffCompensation (n : ℕ) (x : ℝ) :
    HasDerivAt (liPrimeCutoffCompensation n)
      (liPrimeWeightPolynomial n x) x := by
  unfold liPrimeCutoffCompensation liPrimeWeightPolynomial
  apply HasDerivAt.fun_sum
  intro j hj
  have h := ((hasDerivAt_pow (j + 1) x).const_mul
    (n.choose (j + 1) : ℝ)).div_const ((j + 1).factorial : ℝ)
  apply h.congr_deriv
  rw [Nat.factorial_succ]
  norm_num [Nat.cast_mul, Nat.cast_add]
  field_simp

/-- After logarithmic substitution the compensation derivative is exactly
the smooth Li prime weight. -/
theorem hasDerivAt_liPrimeCutoffCompensation_log
    (n : ℕ) {x : ℝ} (hx : x ≠ 0) :
    HasDerivAt (fun t ↦ liPrimeCutoffCompensation n (Real.log t))
      (riemannLiAnalyticPrimeWeight n x) x := by
  change HasDerivAt (liPrimeCutoffCompensation n ∘ Real.log)
    (liPrimeWeightPolynomial n (Real.log x) / x) x
  simpa only [div_eq_mul_inv] using
    (hasDerivAt_liPrimeCutoffCompensation n (Real.log x)).comp x
      (Real.hasDerivAt_log hx)

/-- The compensation hypothesis needed below is an elementary theorem, not
an arithmetic assumption: integration by parts turns its increment into the
boundary-minus-derivative expression paired with Abel summation. -/
theorem liPrimeCutoffCompensation_sub_eq_boundary_sub_integral
    (n N M : ℕ) (hN : 1 ≤ N) (hNM : N ≤ M)
    (hdiff : ∀ t ∈ Set.Icc (N : ℝ) M,
      DifferentiableAt ℝ (riemannLiAnalyticPrimeWeight n) t)
    (hint : IntegrableOn (deriv (riemannLiAnalyticPrimeWeight n))
      (Set.Icc (N : ℝ) M)) :
    liPrimeCutoffCompensation n (Real.log M) -
        liPrimeCutoffCompensation n (Real.log N) =
      riemannLiAnalyticPrimeWeight n M * M -
        riemannLiAnalyticPrimeWeight n N * N -
          ∫ t in Set.Ioc (N : ℝ) M,
            deriv (riemannLiAnalyticPrimeWeight n) t * t := by
  have hreal : (N : ℝ) ≤ M := by exact_mod_cast hNM
  have huicc : Set.uIcc (N : ℝ) M = Set.Icc (N : ℝ) M :=
    Set.uIcc_of_le hreal
  have hne (x : ℝ) (hx : x ∈ Set.uIcc (N : ℝ) M) : x ≠ 0 := by
    rw [huicc] at hx
    have hNreal : (1 : ℝ) ≤ N := by exact_mod_cast hN
    linarith [hx.1]
  have hweightInt : IntervalIntegrable (riemannLiAnalyticPrimeWeight n)
      volume (N : ℝ) M :=
    (DifferentiableOn.continuousOn fun x hx ↦
      (hdiff x hx).differentiableWithinAt).intervalIntegrable_of_Icc
      hreal
  have hcompFTC := intervalIntegral.integral_eq_sub_of_hasDerivAt
    (f := fun x ↦ liPrimeCutoffCompensation n (Real.log x))
    (f' := riemannLiAnalyticPrimeWeight n)
    (fun x hx ↦ hasDerivAt_liPrimeCutoffCompensation_log n (hne x hx))
    hweightInt
  have hderivInt : IntervalIntegrable
      (deriv (riemannLiAnalyticPrimeWeight n)) volume (N : ℝ) M :=
    (intervalIntegrable_iff_integrableOn_Icc_of_le hreal).2 hint
  have hibp := intervalIntegral.integral_mul_deriv_eq_deriv_mul
    (u := riemannLiAnalyticPrimeWeight n) (v := fun x : ℝ ↦ x)
    (u' := deriv (riemannLiAnalyticPrimeWeight n)) (v' := fun _ ↦ 1)
    (fun x hx ↦ (hdiff x (by simpa [huicc] using hx)).hasDerivAt)
    (fun x _ ↦ hasDerivAt_id' x)
    hderivInt intervalIntegrable_const
  rw [← intervalIntegral.integral_of_le hreal]
  calc
    liPrimeCutoffCompensation n (Real.log ↑M) -
          liPrimeCutoffCompensation n (Real.log ↑N) =
        ∫ x in (N : ℝ)..M, riemannLiAnalyticPrimeWeight n x := hcompFTC.symm
    _ = ∫ x in (N : ℝ)..M, riemannLiAnalyticPrimeWeight n x * 1 := by simp
    _ = riemannLiAnalyticPrimeWeight n M * M -
          riemannLiAnalyticPrimeWeight n N * N -
            ∫ x in (N : ℝ)..M,
              deriv (riemannLiAnalyticPrimeWeight n) x * x := hibp

/-- Abel summation for the literal Li prime weight. -/
theorem riemannLiPrimeTail_abel
    (n N M : ℕ) (hNM : N ≤ M)
    (hdiff : ∀ t ∈ Set.Icc (N : ℝ) M,
      DifferentiableAt ℝ (riemannLiAnalyticPrimeWeight n) t)
    (hint : IntegrableOn (deriv (riemannLiAnalyticPrimeWeight n))
      (Set.Icc (N : ℝ) M)) :
    (∑ k ∈ Finset.Ioc N M,
        riemannLiAnalyticPrimeWeight n k *
          ArithmeticFunction.vonMangoldt k) =
      riemannLiAnalyticPrimeWeight n M * Chebyshev.psi M -
        riemannLiAnalyticPrimeWeight n N * Chebyshev.psi N -
          ∫ t in Set.Ioc (N : ℝ) M,
            deriv (riemannLiAnalyticPrimeWeight n) t * Chebyshev.psi t := by
  have h := sum_mul_eq_sub_sub_integral_mul'
    (c := fun k ↦ ArithmeticFunction.vonMangoldt k)
    hNM hdiff hint
  simpa only [Chebyshev.psi_eq_sum_Icc, Nat.floor_natCast] using h

/-- The finite tail after subtracting the exact logarithmic compensation. -/
noncomputable def riemannLiCompensatedPrimeTail (n N M : ℕ) : ℝ :=
  (∑ k ∈ Finset.Ioc N M,
      riemannLiAnalyticPrimeWeight n k *
        ArithmeticFunction.vonMangoldt k) -
    (liPrimeCutoffCompensation n (Real.log M) -
      liPrimeCutoffCompensation n (Real.log N))

theorem riemannLiAnalyticPrimeWeight_nat_mul_vonMangoldt
    (n m : ℕ) (hm : m ≠ 0) :
    riemannLiAnalyticPrimeWeight n m * ArithmeticFunction.vonMangoldt m =
      riemannLiPrimeArithmeticWeight m *
        liPrimeWeightPolynomial n (Real.log m) := by
  unfold riemannLiAnalyticPrimeWeight riemannLiPrimeArithmeticWeight
  have hmreal : (m : ℝ) ≠ 0 := by exact_mod_cast hm
  field_simp

/-- One-step update for the compensated tail. -/
theorem riemannLiCompensatedPrimeTail_succ
    (n N M : ℕ) (hNM : N ≤ M) :
    riemannLiCompensatedPrimeTail n N (M + 1) =
      riemannLiCompensatedPrimeTail n N M +
        riemannLiPrimeArithmeticWeight (M + 1) *
          liPrimeWeightPolynomial n (Real.log (M + 1)) -
        (liPrimeCutoffCompensation n (Real.log (M + 1)) -
          liPrimeCutoffCompensation n (Real.log M)) := by
  rw [riemannLiCompensatedPrimeTail, riemannLiCompensatedPrimeTail,
    Finset.sum_Ioc_succ_top hNM]
  rw [riemannLiAnalyticPrimeWeight_nat_mul_vonMangoldt n (M + 1)
    (Nat.succ_ne_zero M)]
  simp only [Nat.cast_add, Nat.cast_one]
  ring

/-- Exact connection between the stored cutoff energy and the analytic
compensated tail. -/
theorem riemannLiPrimeCutoffEnergy_sub_eq_neg_tail
    (n N M : ℕ) (hNM : N ≤ M) :
    riemannLiPrimeCutoffEnergy n M - riemannLiPrimeCutoffEnergy n N =
      -riemannLiCompensatedPrimeTail n N M := by
  induction M, hNM using Nat.le_induction with
  | base => simp [riemannLiCompensatedPrimeTail]
  | succ M hNM ih =>
      calc
        riemannLiPrimeCutoffEnergy n (M + 1) -
              riemannLiPrimeCutoffEnergy n N =
            (riemannLiPrimeCutoffEnergy n (M + 1) -
              riemannLiPrimeCutoffEnergy n M) +
                (riemannLiPrimeCutoffEnergy n M -
                  riemannLiPrimeCutoffEnergy n N) := by ring
        _ = (liPrimeCutoffCompensation n (Real.log (M + 1)) -
              liPrimeCutoffCompensation n (Real.log M) -
                riemannLiPrimeArithmeticWeight (M + 1) *
                  liPrimeWeightPolynomial n (Real.log (M + 1))) -
              riemannLiCompensatedPrimeTail n N M := by
            rw [riemannLiPrimeCutoffEnergy_succ, ih]
            ring
        _ = -riemannLiCompensatedPrimeTail n N (M + 1) := by
            rw [riemannLiCompensatedPrimeTail_succ n N M hNM]
            ring

/-- Exact remainder identity.  `hcomp` is the elementary integration-by-parts
formula for the compensation polynomial.  The only arithmetic quantities on
the right are `psi(x) - x`. -/
theorem riemannLiCompensatedPrimeTail_eq_psiRemainder
    (n N M : ℕ) (hNM : N ≤ M)
    (hdiff : ∀ t ∈ Set.Icc (N : ℝ) M,
      DifferentiableAt ℝ (riemannLiAnalyticPrimeWeight n) t)
    (hint : IntegrableOn (deriv (riemannLiAnalyticPrimeWeight n))
      (Set.Icc (N : ℝ) M))
    (hcomp :
      liPrimeCutoffCompensation n (Real.log M) -
          liPrimeCutoffCompensation n (Real.log N) =
        riemannLiAnalyticPrimeWeight n M * M -
          riemannLiAnalyticPrimeWeight n N * N -
            ∫ t in Set.Ioc (N : ℝ) M,
              deriv (riemannLiAnalyticPrimeWeight n) t * t) :
    riemannLiCompensatedPrimeTail n N M =
      riemannLiAnalyticPrimeWeight n M * chebyshevPsiRemainder M -
        riemannLiAnalyticPrimeWeight n N * chebyshevPsiRemainder N -
          ((∫ t in Set.Ioc (N : ℝ) M,
              deriv (riemannLiAnalyticPrimeWeight n) t * Chebyshev.psi t) -
            ∫ t in Set.Ioc (N : ℝ) M,
              deriv (riemannLiAnalyticPrimeWeight n) t * t) := by
  rw [riemannLiCompensatedPrimeTail,
    riemannLiPrimeTail_abel n N M hNM hdiff hint, hcomp]
  simp only [chebyshevPsiRemainder]
  ring

/-- A direct norm bound for the finite compensated tail.  Subsequent work can
insert any unconditional bound for `psi(x) - x` and the weighted integral. -/
theorem abs_riemannLiCompensatedPrimeTail_le
    (n N M : ℕ) (hNM : N ≤ M)
    (hdiff : ∀ t ∈ Set.Icc (N : ℝ) M,
      DifferentiableAt ℝ (riemannLiAnalyticPrimeWeight n) t)
    (hint : IntegrableOn (deriv (riemannLiAnalyticPrimeWeight n))
      (Set.Icc (N : ℝ) M))
    (hcomp :
      liPrimeCutoffCompensation n (Real.log M) -
          liPrimeCutoffCompensation n (Real.log N) =
        riemannLiAnalyticPrimeWeight n M * M -
          riemannLiAnalyticPrimeWeight n N * N -
            ∫ t in Set.Ioc (N : ℝ) M,
              deriv (riemannLiAnalyticPrimeWeight n) t * t) :
    |riemannLiCompensatedPrimeTail n N M| ≤
      |riemannLiAnalyticPrimeWeight n M * chebyshevPsiRemainder M| +
        |riemannLiAnalyticPrimeWeight n N * chebyshevPsiRemainder N| +
          |(∫ t in Set.Ioc (N : ℝ) M,
              deriv (riemannLiAnalyticPrimeWeight n) t * Chebyshev.psi t) -
            ∫ t in Set.Ioc (N : ℝ) M,
              deriv (riemannLiAnalyticPrimeWeight n) t * t| := by
  rw [riemannLiCompensatedPrimeTail_eq_psiRemainder
    n N M hNM hdiff hint hcomp]
  have hthree (a b c : ℝ) : |a - b - c| ≤ |a| + |b| + |c| := by
    calc
      |a - b - c| ≤ |a - b| + |c| := abs_sub _ _
      _ ≤ (|a| + |b|) + |c| := add_le_add (abs_sub a b) le_rfl
      _ = |a| + |b| + |c| := rfl
  exact hthree _ _ _

/-- Fully discharged exact tail identity: the compensation term is supplied
by the proved elementary integration-by-parts theorem. -/
theorem riemannLiCompensatedPrimeTail_eq_psiRemainder_exact
    (n N M : ℕ) (hN : 1 ≤ N) (hNM : N ≤ M)
    (hdiff : ∀ t ∈ Set.Icc (N : ℝ) M,
      DifferentiableAt ℝ (riemannLiAnalyticPrimeWeight n) t)
    (hint : IntegrableOn (deriv (riemannLiAnalyticPrimeWeight n))
      (Set.Icc (N : ℝ) M)) :
    riemannLiCompensatedPrimeTail n N M =
      riemannLiAnalyticPrimeWeight n M * chebyshevPsiRemainder M -
        riemannLiAnalyticPrimeWeight n N * chebyshevPsiRemainder N -
          ((∫ t in Set.Ioc (N : ℝ) M,
              deriv (riemannLiAnalyticPrimeWeight n) t * Chebyshev.psi t) -
            ∫ t in Set.Ioc (N : ℝ) M,
              deriv (riemannLiAnalyticPrimeWeight n) t * t) := by
  exact riemannLiCompensatedPrimeTail_eq_psiRemainder n N M hNM hdiff hint
    (liPrimeCutoffCompensation_sub_eq_boundary_sub_integral
      n N M hN hNM hdiff hint)

/-- Fully discharged norm bound for the finite prime tail. -/
theorem abs_riemannLiCompensatedPrimeTail_le_exact
    (n N M : ℕ) (hN : 1 ≤ N) (hNM : N ≤ M)
    (hdiff : ∀ t ∈ Set.Icc (N : ℝ) M,
      DifferentiableAt ℝ (riemannLiAnalyticPrimeWeight n) t)
    (hint : IntegrableOn (deriv (riemannLiAnalyticPrimeWeight n))
      (Set.Icc (N : ℝ) M)) :
    |riemannLiCompensatedPrimeTail n N M| ≤
      |riemannLiAnalyticPrimeWeight n M * chebyshevPsiRemainder M| +
        |riemannLiAnalyticPrimeWeight n N * chebyshevPsiRemainder N| +
          |(∫ t in Set.Ioc (N : ℝ) M,
              deriv (riemannLiAnalyticPrimeWeight n) t * Chebyshev.psi t) -
            ∫ t in Set.Ioc (N : ℝ) M,
              deriv (riemannLiAnalyticPrimeWeight n) t * t| := by
  exact abs_riemannLiCompensatedPrimeTail_le n N M hNM hdiff hint
    (liPrimeCutoffCompensation_sub_eq_boundary_sub_integral
      n N M hN hNM hdiff hint)

/-- Final finite-tail identity with every calculus side condition discharged. -/
theorem riemannLiCompensatedPrimeTail_eq_psiRemainder_unconditional
    (n N M : ℕ) (hN : 1 ≤ N) (hNM : N ≤ M) :
    riemannLiCompensatedPrimeTail n N M =
      riemannLiAnalyticPrimeWeight n M * chebyshevPsiRemainder M -
        riemannLiAnalyticPrimeWeight n N * chebyshevPsiRemainder N -
          ((∫ t in Set.Ioc (N : ℝ) M,
              deriv (riemannLiAnalyticPrimeWeight n) t * Chebyshev.psi t) -
            ∫ t in Set.Ioc (N : ℝ) M,
              deriv (riemannLiAnalyticPrimeWeight n) t * t) := by
  apply riemannLiCompensatedPrimeTail_eq_psiRemainder_exact n N M hN hNM
  · intro t ht
    have hNreal : (1 : ℝ) ≤ N := by exact_mod_cast hN
    exact differentiableAt_riemannLiAnalyticPrimeWeight_of_pos n
      (lt_of_lt_of_le zero_lt_one (hNreal.trans ht.1))
  · exact integrableOn_deriv_riemannLiAnalyticPrimeWeight n N M hN

/-- Final unconditional finite-tail norm bound. -/
theorem abs_riemannLiCompensatedPrimeTail_le_unconditional
    (n N M : ℕ) (hN : 1 ≤ N) (hNM : N ≤ M) :
    |riemannLiCompensatedPrimeTail n N M| ≤
      |riemannLiAnalyticPrimeWeight n M * chebyshevPsiRemainder M| +
        |riemannLiAnalyticPrimeWeight n N * chebyshevPsiRemainder N| +
          |(∫ t in Set.Ioc (N : ℝ) M,
              deriv (riemannLiAnalyticPrimeWeight n) t * Chebyshev.psi t) -
            ∫ t in Set.Ioc (N : ℝ) M,
              deriv (riemannLiAnalyticPrimeWeight n) t * t| := by
  apply abs_riemannLiCompensatedPrimeTail_le_exact n N M hN hNM
  · intro t ht
    have hNreal : (1 : ℝ) ≤ N := by exact_mod_cast hN
    exact differentiableAt_riemannLiAnalyticPrimeWeight_of_pos n
      (lt_of_lt_of_le zero_lt_one (hNreal.trans ht.1))
  · exact integrableOn_deriv_riemannLiAnalyticPrimeWeight n N M hN

/-- The explicit finite `psi`-remainder radius produced by Abel summation. -/
noncomputable def riemannLiPsiTailRadius (n N M : ℕ) : ℝ :=
  |riemannLiAnalyticPrimeWeight n M * chebyshevPsiRemainder M| +
    |riemannLiAnalyticPrimeWeight n N * chebyshevPsiRemainder N| +
      |(∫ t in Set.Ioc (N : ℝ) M,
          deriv (riemannLiAnalyticPrimeWeight n) t * Chebyshev.psi t) -
        ∫ t in Set.Ioc (N : ℝ) M,
          deriv (riemannLiAnalyticPrimeWeight n) t * t|

/-- Every finite cutoff oscillation is controlled by the explicit
`psi(x)-x` radius. -/
theorem abs_riemannLiPrimeCutoffEnergy_sub_le_psiTailRadius
    (n N M : ℕ) (hN : 1 ≤ N) (hNM : N ≤ M) :
    |riemannLiPrimeCutoffEnergy n M - riemannLiPrimeCutoffEnergy n N| ≤
      riemannLiPsiTailRadius n N M := by
  rw [riemannLiPrimeCutoffEnergy_sub_eq_neg_tail n N M hNM, abs_neg]
  exact abs_riemannLiCompensatedPrimeTail_le_unconditional n N M hN hNM

/-- The final tail-cancellation certificate stated wholly through finite
prime cutoffs and the Chebyshev remainder. -/
structure RiemannLiPsiTailCertificate where
  cutoff : ℕ → ℕ
  radius : ℕ → ℝ
  cutoff_pos : ∀ n, 1 ≤ cutoff n
  radius_nonneg : ∀ n, 0 ≤ radius n
  cutoff_converges : ∀ n,
    Filter.Tendsto (riemannLiPrimeCutoffEnergy n) Filter.atTop
      (nhds (riemannLiCoefficient n))
  psi_tail_bound : ∀ n M, cutoff n ≤ M →
    riemannLiPsiTailRadius n (cutoff n) M ≤ radius n
  checkpoint_margin : ∀ n,
    radius n ≤ riemannLiPrimeCutoffEnergy n (cutoff n)

/-- A uniform `psi`-tail certificate proves every Riemann Li inequality. -/
theorem RiemannLiPsiTailCertificate.liPositivity
    (C : RiemannLiPsiTailCertificate) : RiemannLiPositivity := by
  let U : RiemannLiUniformCutoffTailCertificate :=
    { cutoff := C.cutoff
      radius := C.radius
      radius_nonneg := C.radius_nonneg
      cutoff_converges := C.cutoff_converges
      uniform_tail := by
        intro n M hM
        exact (abs_riemannLiPrimeCutoffEnergy_sub_le_psiTailRadius
          n (C.cutoff n) M (C.cutoff_pos n) hM).trans
            (C.psi_tail_bound n M hM)
      checkpoint_margin := C.checkpoint_margin }
  exact U.liPositivity

end RiemannLab
