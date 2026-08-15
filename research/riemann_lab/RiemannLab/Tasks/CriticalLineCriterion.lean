import RiemannLab.Tasks.NontrivialZeros
import Mathlib.NumberTheory.Chebyshev
import Mathlib.NumberTheory.LSeries.Dirichlet

namespace RiemannLab

open scoped ArithmeticFunction.vonMangoldt LSeries.notation

/-!
A no-axiom scaffold for the selected Chebyshev-psi route toward an
RH-equivalent critical-line criterion. The equivalence itself is deliberately
represented as an open target, not asserted as a theorem.
-/

/-- The remainder after subtracting the expected main term from Chebyshev's psi function. -/
noncomputable def chebyshevPsiRemainder (x : ℝ) : ℝ :=
  Chebyshev.psi x - x

/-- The classical square-root-scale psi bound used in an RH-equivalent criterion. -/
def CriticalPsiBound : Prop :=
  ∃ C : ℝ, 0 < C ∧ ∀ x : ℝ, 2 ≤ x →
    |chebyshevPsiRemainder x| ≤ C * Real.sqrt x * (Real.log x) ^ 2

/-- The exact equivalence that the next formalization stage must reconstruct. -/
def CriticalPsiEquivalenceTarget : Prop :=
  RiemannHypothesis ↔ CriticalPsiBound

/-- The remainder unfolds to the finite von Mangoldt sum minus its main term. -/
theorem chebyshevPsiRemainder_eq_sum_vonMangoldt (x : ℝ) :
    chebyshevPsiRemainder x =
      (∑ n ∈ Finset.Icc 0 ⌊x⌋₊, ArithmeticFunction.vonMangoldt n) - x := by
  rw [chebyshevPsiRemainder, Chebyshev.psi_eq_sum_Icc]

/-- The existing Dirichlet-series bridge from von Mangoldt to zeta's logarithmic derivative. -/
theorem vonMangoldt_LSeries_eq_zeta_logDeriv {s : ℂ} (hs : 1 < s.re) :
    L ↗ArithmeticFunction.vonMangoldt s =
      -deriv riemannZeta s / riemannZeta s := by
  exact ArithmeticFunction.LSeries_vonMangoldt_eq_deriv_riemannZeta_div hs

/-- Any witness to the critical psi bound gives explicit two-sided control of psi. -/
theorem CriticalPsiBound.two_sided (h : CriticalPsiBound) :
    ∃ C : ℝ, 0 < C ∧ ∀ x : ℝ, 2 ≤ x →
      x - C * Real.sqrt x * (Real.log x) ^ 2 ≤ Chebyshev.psi x ∧
      Chebyshev.psi x ≤ x + C * Real.sqrt x * (Real.log x) ^ 2 := by
  rcases h with ⟨C, hC, hbound⟩
  refine ⟨C, hC, fun x hx ↦ ?_⟩
  have habs := abs_le.mp (hbound x hx)
  constructor <;> dsimp [chebyshevPsiRemainder] at habs ⊢ <;> linarith

/-- Existing library support: Chebyshev psi is monotone. -/
theorem chebyshevPsi_monotone : Monotone Chebyshev.psi :=
  Chebyshev.psi_mono

/-- Existing library support: Chebyshev psi is nonnegative. -/
theorem chebyshevPsi_nonneg (x : ℝ) : 0 ≤ Chebyshev.psi x :=
  Chebyshev.psi_nonneg x

end RiemannLab
