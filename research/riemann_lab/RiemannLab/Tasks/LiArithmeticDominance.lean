import RiemannLab.Tasks.LiPrefixEnergy

namespace RiemannLab

/-!
# Minimal arithmetic dominance target for Li positivity

The arithmetic explicit formula has the shape
`lambda n = archimedean n - finitePlace n + pole n`.  Once that identity is
instantiated for zeta, Li positivity is exactly one scalar dominance
inequality at each index.  No stronger operator assumption is required.
-/

/-- Abstract exact arithmetic ledger for a normalized Li-type sequence. -/
structure LiArithmeticDecomposition (a : ℕ → ℝ) where
  archimedean : ℕ → ℝ
  finitePlace : ℕ → ℝ
  pole : ℕ → ℝ
  identity : ∀ n, a n = archimedean n - finitePlace n + pole n

/-- The sole arithmetic inequality required by the decomposition. -/
def LiArithmeticDecomposition.HasDominance
    {a : ℕ → ℝ} (D : LiArithmeticDecomposition a) : Prop :=
  ∀ n, D.finitePlace n ≤ D.archimedean n + D.pole n

/-- Arithmetic dominance is exactly termwise positivity of the represented
sequence. -/
theorem LiArithmeticDecomposition.dominance_iff_sequence_nonneg
    {a : ℕ → ℝ} (D : LiArithmeticDecomposition a) :
    D.HasDominance ↔ ∀ n, 0 ≤ a n := by
  constructor
  · intro h n
    rw [D.identity]
    linarith [h n]
  · intro h n
    have hn := h n
    rw [D.identity] at hn
    linarith

/-- For a normalized sequence, the arithmetic dominance target is exactly
positivity of all Fejér-prefix energies. -/
theorem LiArithmeticDecomposition.dominance_iff_prefixEnergy
    {a : ℕ → ℝ} (D : LiArithmeticDecomposition a) (ha0 : a 0 = 0) :
    D.HasDominance ↔ HasNonnegativeLiPrefixEnergy a := by
  rw [D.dominance_iff_sequence_nonneg,
    nonnegativeLiPrefixEnergy_iff a ha0]

/-- Failure at one arithmetic index is already a finite negative prefix
certificate. -/
theorem LiArithmeticDecomposition.negative_prefix_of_dominance_failure
    {a : ℕ → ℝ} (D : LiArithmeticDecomposition a) (ha0 : a 0 = 0)
    {n : ℕ} (hfail : D.archimedean n + D.pole n < D.finitePlace n) :
    liPrefixEnergy a n < 0 := by
  rw [liPrefixEnergy_eq a ha0 n, D.identity]
  linarith

end RiemannLab
