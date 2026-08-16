import RiemannLab.Tasks.LiCoupledDominanceCertificate
import Mathlib.NumberTheory.LSeries.RiemannZeta

namespace RiemannLab

open scoped ArithmeticFunction.vonMangoldt

/-!
# Finite prime-cutoff energy for the Li arithmetic target

The finite-place Li term is a regularized quantity: its raw prime sum and a
logarithmic compensation term diverge separately.  This file keeps those two
pieces coupled.  The resulting finite expression is the correct object for a
prime-by-prime invariant or a certified cutoff rover.
-/

/-- The degree `n - 1` polynomial which weights a prime-power logarithm in
the `n`th Li test.  This is the finite binomial form of the associated
Laguerre polynomial used in the Li--Weil explicit formula. -/
noncomputable def liPrimeWeightPolynomial (n : ℕ) (x : ℝ) : ℝ :=
  ∑ j ∈ Finset.range n,
    (n.choose (j + 1) : ℝ) * x ^ j / (j.factorial : ℝ)

/-- The logarithmic counterterm paired with the raw prime sum. -/
noncomputable def liPrimeCutoffCompensation (n : ℕ) (x : ℝ) : ℝ :=
  ∑ j ∈ Finset.range n,
    (n.choose (j + 1) : ℝ) * x ^ (j + 1) / ((j + 1).factorial : ℝ)

/-- A raw finite weighted prime sum, abstracted over the arithmetic weights
and logarithms so that all finite algebra is reusable. -/
noncomputable def liRawPrimeCutoff
    (n : ℕ) (s : Finset ℕ) (weight logValue : ℕ → ℝ) : ℝ :=
  ∑ m ∈ s, weight m * liPrimeWeightPolynomial n (logValue m)

/-- The compensated arithmetic energy at a finite cutoff.  For the Riemann
ledger, `weight m` is `Λ(m)/m`, `logValue m = log m`, and `cutoffLog` is the
logarithm of the cutoff. -/
noncomputable def liPrimeCutoffEnergy
    (archimedean pole : ℕ → ℝ) (n : ℕ) (cutoffLog : ℝ)
    (s : Finset ℕ) (weight logValue : ℕ → ℝ) : ℝ :=
  archimedean n + pole n + liPrimeCutoffCompensation n cutoffLog -
    liRawPrimeCutoff n s weight logValue

/-- Finite interchange: the moment transform of the prime data is exactly
the Laguerre-weighted raw prime sum. -/
theorem liMomentTransform_eq_rawPrimeCutoff
    (n : ℕ) (s : Finset ℕ) (weight logValue : ℕ → ℝ) :
    (∑ j ∈ Finset.range n,
        (n.choose (j + 1) : ℝ) / (j.factorial : ℝ) *
          (∑ m ∈ s, weight m * (logValue m) ^ j)) =
      liRawPrimeCutoff n s weight logValue := by
  simp only [liRawPrimeCutoff, liPrimeWeightPolynomial]
  simp_rw [Finset.mul_sum]
  rw [Finset.sum_comm]
  apply Finset.sum_congr rfl
  intro m hm
  apply Finset.sum_congr rfl
  intro j hj
  ring

/-- Exact one-cutoff update.  This is the checkpoint equation for an
incremental prime rover: the energy change is the compensation increment
minus the newly inserted arithmetic contribution. -/
theorem liPrimeCutoffEnergy_insert
    (archimedean pole : ℕ → ℝ) (n : ℕ) (oldLog newLog : ℝ)
    (s : Finset ℕ) (m : ℕ) (hm : m ∉ s) (weight logValue : ℕ → ℝ) :
    liPrimeCutoffEnergy archimedean pole n newLog (insert m s) weight logValue -
        liPrimeCutoffEnergy archimedean pole n oldLog s weight logValue =
      liPrimeCutoffCompensation n newLog -
        liPrimeCutoffCompensation n oldLog -
          weight m * liPrimeWeightPolynomial n (logValue m) := by
  simp only [liPrimeCutoffEnergy, liRawPrimeCutoff, Finset.sum_insert hm]
  ring

/-! ## Literal Riemann prime checkpoints -/

/-- The literal Riemann finite-prime weight `Λ(m) / m`. -/
noncomputable def riemannLiPrimeArithmeticWeight (m : ℕ) : ℝ :=
  ArithmeticFunction.vonMangoldt m / (m : ℝ)

/-- The finite von Mangoldt sum in the `n`th Li test, cut off at `N`. -/
noncomputable def riemannLiRawPrimeCutoff (n N : ℕ) : ℝ :=
  liRawPrimeCutoff n (Finset.Icc 1 N) riemannLiPrimeArithmeticWeight
    (fun m ↦ Real.log m)

/-- The actual coupled Riemann cutoff energy.  The raw prime sum is never
separated from its compensating logarithmic polynomial. -/
noncomputable def riemannLiPrimeCutoffEnergy (n N : ℕ) : ℝ :=
  liPrimeCutoffEnergy riemannLiSInfinity
    (fun k ↦ if k = 0 then 0 else 1) n (Real.log N)
    (Finset.Icc 1 N) riemannLiPrimeArithmeticWeight (fun m ↦ Real.log m)

/-- The next integer is not contained in the preceding cutoff interval. -/
theorem not_mem_Icc_one_self_succ (N : ℕ) : N + 1 ∉ Finset.Icc 1 N := by
  simp

/-- The literal prime-by-prime checkpoint equation.  It identifies exactly
how much logarithmic compensation is available to pay for the next von
Mangoldt contribution. -/
theorem riemannLiPrimeCutoffEnergy_succ (n N : ℕ) :
    riemannLiPrimeCutoffEnergy n (N + 1) -
        riemannLiPrimeCutoffEnergy n N =
      liPrimeCutoffCompensation n (Real.log (N + 1)) -
        liPrimeCutoffCompensation n (Real.log N) -
          riemannLiPrimeArithmeticWeight (N + 1) *
            liPrimeWeightPolynomial n (Real.log (N + 1)) := by
  have hset : Finset.Icc 1 (N + 1) = insert (N + 1) (Finset.Icc 1 N) := by
    ext m
    simp only [Finset.mem_Icc, Finset.mem_insert]
    omega
  unfold riemannLiPrimeCutoffEnergy
  rw [hset]
  simpa [Nat.cast_add, Nat.cast_one] using liPrimeCutoffEnergy_insert
    (archimedean := riemannLiSInfinity)
    (pole := fun k ↦ if k = 0 then 0 else 1)
    (n := n) (oldLog := Real.log N) (newLog := Real.log (N + 1))
    (s := Finset.Icc 1 N) (m := N + 1)
    (not_mem_Icc_one_self_succ N)
    riemannLiPrimeArithmeticWeight (fun m ↦ Real.log m)

/-- A nonnegative cutoff invariant passes to a nonnegative limiting Li
coefficient.  This is the rigorous bridge from finite prime checkpoints to
the all-index target; the analytic obligation is convergence of the coupled
energy, not convergence of either divergent component separately. -/
theorem nonneg_of_tendsto_liPrimeCutoffEnergy
    {energy : ℕ → ℝ} {limit : ℝ}
    (henergy : ∀ k, 0 ≤ energy k)
    (hlim : Filter.Tendsto energy Filter.atTop (nhds limit)) :
    0 ≤ limit := by
  exact isClosed_Ici.mem_of_tendsto hlim (Filter.Eventually.of_forall henergy)

/-- Eventual, rather than pointwise, nonnegativity is sufficient.  Literal
prime cutoffs can oscillate before entering their limiting regime. -/
theorem nonneg_of_eventually_nonneg_tendsto
    {energy : ℕ → ℝ} {limit : ℝ}
    (henergy : ∀ᶠ k in Filter.atTop, 0 ≤ energy k)
    (hlim : Filter.Tendsto energy Filter.atTop (nhds limit)) :
    0 ≤ limit := by
  exact isClosed_Ici.mem_of_tendsto hlim henergy

/-- A finite checkpoint proves a nonnegative limit once its certified error
radius fits below the checkpoint margin. -/
theorem nonneg_of_checkpoint_with_error
    {checkpoint radius limit : ℝ}
    (_hradius : 0 ≤ radius)
    (herror : |limit - checkpoint| ≤ radius)
    (hmargin : radius ≤ checkpoint) :
    0 ≤ limit := by
  have hlower : checkpoint - radius ≤ limit := by
    have := (abs_le.mp herror).1
    linarith
  linarith

/-- The exact finite certificate required for the literal Riemann prime
cutoff programme.  Its tail bound must come from independent analytic number
theory; it cannot be defined by inspecting the unknown Li coefficient. -/
structure RiemannLiPrimeCutoffCertificate where
  cutoff : ℕ → ℕ
  radius : ℕ → ℝ
  radius_nonneg : ∀ n, 0 ≤ radius n
  tail_bound : ∀ n,
    |riemannLiCoefficient n -
      riemannLiPrimeCutoffEnergy n (cutoff n)| ≤ radius n
  checkpoint_margin : ∀ n,
    radius n ≤ riemannLiPrimeCutoffEnergy n (cutoff n)

/-- A uniform family of finite prime checkpoints with rigorous tail margins
proves all Li inequalities. -/
theorem RiemannLiPrimeCutoffCertificate.liPositivity
    (C : RiemannLiPrimeCutoffCertificate) : RiemannLiPositivity := by
  intro n
  exact nonneg_of_checkpoint_with_error (C.radius_nonneg n)
    (C.tail_bound n) (C.checkpoint_margin n)

/-- A bound on every sufficiently late finite cutoff passes to the limiting
error bound.  Unlike a direct estimate involving the limit, the hypothesis
contains only finite cutoff values. -/
theorem abs_limit_sub_le_of_uniform_cutoff_tail
    {energy : ℕ → ℝ} {limit radius : ℝ} (N : ℕ)
    (hlim : Filter.Tendsto energy Filter.atTop (nhds limit))
    (htail : ∀ M, N ≤ M → |energy M - energy N| ≤ radius) :
    |limit - energy N| ≤ radius := by
  have htendsto : Filter.Tendsto (fun M ↦ |energy M - energy N|)
      Filter.atTop (nhds |limit - energy N|) :=
    (hlim.sub_const (energy N)).abs
  apply isClosed_Iic.mem_of_tendsto htendsto
  filter_upwards [Filter.eventually_ge_atTop N] with M hM
  exact htail M hM

/-- Fully finite-data tail certificate.  Apart from the classical convergence
bridge, the error hypothesis compares only explicit prime cutoffs. -/
structure RiemannLiUniformCutoffTailCertificate where
  cutoff : ℕ → ℕ
  radius : ℕ → ℝ
  radius_nonneg : ∀ n, 0 ≤ radius n
  cutoff_converges : ∀ n,
    Filter.Tendsto (riemannLiPrimeCutoffEnergy n) Filter.atTop
      (nhds (riemannLiCoefficient n))
  uniform_tail : ∀ n M, cutoff n ≤ M →
    |riemannLiPrimeCutoffEnergy n M -
      riemannLiPrimeCutoffEnergy n (cutoff n)| ≤ radius n
  checkpoint_margin : ∀ n,
    radius n ≤ riemannLiPrimeCutoffEnergy n (cutoff n)

/-- A uniform finite-prime tail certificate proves RH-level Li positivity. -/
theorem RiemannLiUniformCutoffTailCertificate.liPositivity
    (C : RiemannLiUniformCutoffTailCertificate) : RiemannLiPositivity := by
  intro n
  apply nonneg_of_checkpoint_with_error (C.radius_nonneg n)
  · exact abs_limit_sub_le_of_uniform_cutoff_tail (C.cutoff n)
      (C.cutoff_converges n) (C.uniform_tail n)
  · exact C.checkpoint_margin n

/-- If the literal Riemann Li coefficient is the limit of nonnegative
coupled cutoff energies at every index, then all Li coefficients are
nonnegative.  This formulation contains no zero-side hypothesis. -/
theorem riemannLiPositivity_of_primeCutoffEnergies
    (energy : ℕ → ℕ → ℝ)
    (henergy : ∀ n k, 0 ≤ energy n k)
    (hlimit : ∀ n,
      Filter.Tendsto (energy n) Filter.atTop (nhds (riemannLiCoefficient n))) :
    RiemannLiPositivity := by
  intro n
  exact nonneg_of_tendsto_liPrimeCutoffEnergy (henergy n) (hlimit n)

/-- A strictly negative finite checkpoint, together with an upper-tail error
smaller than its margin, forces a negative limiting coefficient. -/
theorem negative_limit_of_cutoff_and_tail
    {checkpoint tail limit : ℝ}
    (hdecomp : limit = checkpoint + tail)
    (hmargin : tail < -checkpoint) :
    limit < 0 := by
  linarith

end RiemannLab
