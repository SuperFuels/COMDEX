import RiemannLab.Tasks.CompletedXiLogDerivative
import RiemannLab.Tasks.LiArithmeticDominance
import Mathlib.Analysis.Analytic.Order

namespace RiemannLab

/-!
# The derivative-normalized Riemann Li sequence

This file gives the actual xi-derived sequence used by the minimal prefix
programme.  It uses the Taylor coefficients of the classical Li generating
function.  Equality with the symmetric zero sum and the complete arithmetic
ledger are subsequent analytic obligations.
-/

/-- The derivative of the logarithmic Li generating function. -/
noncomputable def riemannLiGeneratingDerivative (z : ℂ) : ℂ :=
  (1 - z)⁻¹ ^ 2 * completedLiDiskFunction z

/-- Taylor coefficients of the Riemann Li generating derivative, with the
standard normalization `lambda 0 = 0`.  The real part makes the target a real
sequence before the conjugation-symmetry theorem is installed. -/
noncomputable def riemannLiCoefficient : ℕ → ℝ
  | 0 => 0
  | n + 1 =>
      (iteratedDeriv n riemannLiGeneratingDerivative 0 /
        (n.factorial : ℂ)).re

@[simp]
theorem riemannLiCoefficient_zero : riemannLiCoefficient 0 = 0 := rfl

/-- The exact positivity proposition for the xi-derived Li sequence. -/
def RiemannLiPositivity : Prop :=
  ∀ n, 0 ≤ riemannLiCoefficient n

/-- Li positivity is exactly positivity of the minimal Fejer-prefix family
for the actual derivative-defined sequence. -/
theorem riemannLiPositivity_iff_prefixEnergy :
    RiemannLiPositivity ↔
      HasNonnegativeLiPrefixEnergy riemannLiCoefficient := by
  rw [nonnegativeLiPrefixEnergy_iff riemannLiCoefficient
    riemannLiCoefficient_zero]
  rfl

/-- Each actual Li coefficient is its stationary Fejer-prefix energy. -/
theorem riemannLiPrefixEnergy_eq (n : ℕ) :
    liPrefixEnergy riemannLiCoefficient n = riemannLiCoefficient n :=
  liPrefixEnergy_eq riemannLiCoefficient riemannLiCoefficient_zero n

end RiemannLab
