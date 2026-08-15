import RiemannLab.Tasks.SquaredCauchyFourier
import Mathlib.NumberTheory.Chebyshev

namespace RiemannLab

open Filter
open scoped Topology
open scoped ArithmeticFunction

/-!
Finite Dirichlet-polynomial inversion after completion of the scalar Perron
kernel. The infinite-series tail is deliberately kept separate.
-/

/-- A finite linear combination of scalar Perron truncations. -/
noncomputable def finiteScalarPerronSum
    (S : Finset ℕ) (coeff : ℕ → ℂ) (c x T : ℝ) : ℂ :=
  ∑ n ∈ S, coeff n * scalarTruncatedPerronIntegral c (x / n) T

/-- The corresponding finite sharp cutoff. -/
noncomputable def finitePerronStepSum
    (S : Finset ℕ) (coeff : ℕ → ℂ) (x : ℝ) : ℂ :=
  ∑ n ∈ S.filter (fun n : ℕ ↦ (n : ℝ) < x), coeff n

theorem div_nat_gt_one_iff {x : ℝ} {n : ℕ} (hn : n ≠ 0) :
    1 < x / n ↔ (n : ℝ) < x := by
  have hnpos : (0 : ℝ) < n := by exact_mod_cast Nat.pos_of_ne_zero hn
  rw [lt_div_iff₀ hnpos]
  simp

theorem div_nat_pos {x : ℝ} {n : ℕ} (hx : 0 < x) (hn : n ≠ 0) :
    0 < x / n := by
  have hnpos : (0 : ℝ) < n := by exact_mod_cast Nat.pos_of_ne_zero hn
  exact div_pos hx hnpos

theorem tendsto_finiteScalarPerronSum
    {S : Finset ℕ} {coeff : ℕ → ℂ} {c x : ℝ}
    (hc : 0 < c) (hx : 0 < x)
    (hn : ∀ n ∈ S, n ≠ 0) (hjump : ∀ n ∈ S, x ≠ n) :
    Tendsto (fun T : ℝ ↦ finiteScalarPerronSum S coeff c x T) atTop
      (𝓝 (finitePerronStepSum S coeff x)) := by
  unfold finiteScalarPerronSum finitePerronStepSum
  have hterm : ∀ n ∈ S, Tendsto
      (fun T : ℝ ↦ coeff n * scalarTruncatedPerronIntegral c (x / n) T) atTop
      (𝓝 (if (n : ℝ) < x then coeff n else 0)) := by
    intro n hnS
    have hn0 := hn n hnS
    have hpos := div_nat_pos hx hn0
    have hne : x / n ≠ 1 := by
      intro h
      have hnreal : (n : ℝ) ≠ 0 := by exact_mod_cast hn0
      have : x = n := by
        apply (div_eq_one_iff_eq hnreal).mp
        simpa using h
      exact hjump n hnS this
    have hscalar := scalarPerronLimitTarget c (x / n) hc hpos hne
    have hmul := hscalar.const_mul (coeff n)
    simpa only [div_nat_gt_one_iff hn0, mul_ite, mul_one, mul_zero] using hmul
  have hsum := tendsto_finsetSum S hterm
  simpa only [Finset.sum_filter] using hsum

/-! The first number-theoretic specialization: finite von Mangoldt inversion. -/

/-- The finite Perron expression formed from the von Mangoldt coefficients up
to the natural floor of `x`. -/
noncomputable def finiteVonMangoldtPerronSum (c x T : ℝ) : ℂ :=
  finiteScalarPerronSum (Finset.Ioc 0 ⌊x⌋₊)
    (fun n : ℕ ↦ (Λ n : ℂ)) c x T

theorem finitePerronStepSum_vonMangoldt_eq_psi
    {x : ℝ} (hx : 0 ≤ x) (hnotnat : ∀ n : ℕ, x ≠ n) :
    finitePerronStepSum (Finset.Ioc 0 ⌊x⌋₊)
        (fun n : ℕ ↦ (Λ n : ℂ)) x =
      (Chebyshev.psi x : ℂ) := by
  unfold finitePerronStepSum
  have hfilter :
      (Finset.Ioc 0 ⌊x⌋₊).filter (fun n : ℕ ↦ (n : ℝ) < x) =
        Finset.Ioc 0 ⌊x⌋₊ := by
    apply Finset.filter_eq_self.2
    intro n hn
    have hnle : (n : ℝ) ≤ x :=
      (Nat.le_floor_iff hx).1 (Finset.mem_Ioc.1 hn).2
    exact lt_of_le_of_ne hnle (Ne.symm (hnotnat n))
  rw [hfilter, Chebyshev.psi]
  push_cast
  rfl

/-- Finite Perron inversion for the von Mangoldt coefficients, away from the
jumps at natural values of `x`. This is the finite-polynomial precursor of the
Chebyshev Perron formula; no infinite Dirichlet-series interchange is used. -/
theorem tendsto_finiteVonMangoldtPerronSum
    {c x : ℝ} (hc : 0 < c) (hx : 0 < x)
    (hnotnat : ∀ n : ℕ, x ≠ n) :
    Tendsto (fun T : ℝ ↦ finiteVonMangoldtPerronSum c x T) atTop
      (nhds (Chebyshev.psi x : ℂ)) := by
  unfold finiteVonMangoldtPerronSum
  have h := tendsto_finiteScalarPerronSum
    (S := Finset.Ioc 0 ⌊x⌋₊)
    (coeff := fun n : ℕ ↦ (Λ n : ℂ))
    hc hx (by
      intro n hn
      exact ne_of_gt (Finset.mem_Ioc.1 hn).1) (by
      intro n _
      exact hnotnat n)
  simpa [finitePerronStepSum_vonMangoldt_eq_psi hx.le hnotnat] using h

end RiemannLab
