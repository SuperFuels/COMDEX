import RiemannLab.Tasks.RiemannLiArithmeticLedger

namespace RiemannLab

/-!
# Non-circular coupled certificates for Li dominance

The literal finite-place term is currently defined as the analytic residual
in the completed prime--Gamma--pole identity.  Re-expanding that definition
cannot prove positivity: it simply recovers the Li coefficient.  This file
records the extra, genuinely arithmetic data a non-circular proof must
provide, and proves by countermodel that the ledger identity plus separate
placewise nonnegativity is insufficient.
-/

/-- A two-stage domination certificate.  The intermediate majorant is where
independent prime estimates must enter: it bounds the finite-place term from
above and is itself absorbed by the coupled archimedean-plus-pole budget. -/
structure LiCoupledDominanceCertificate
    {a : ℕ → ℝ} (D : LiArithmeticDecomposition a) where
  majorant : ℕ → ℝ
  finitePlace_le : ∀ n, D.finitePlace n ≤ majorant n
  majorant_le_budget : ∀ n, majorant n ≤ D.archimedean n + D.pole n

/-- A coupled certificate proves the exact minimal dominance condition. -/
theorem LiCoupledDominanceCertificate.hasDominance
    {a : ℕ → ℝ} {D : LiArithmeticDecomposition a}
    (C : LiCoupledDominanceCertificate D) : D.HasDominance := by
  intro n
  exact (C.finitePlace_le n).trans (C.majorant_le_budget n)

/-- Hence the represented sequence is nonnegative at every index. -/
theorem LiCoupledDominanceCertificate.sequence_nonneg
    {a : ℕ → ℝ} {D : LiArithmeticDecomposition a}
    (C : LiCoupledDominanceCertificate D) : ∀ n, 0 ≤ a n :=
  D.dominance_iff_sequence_nonneg.mp C.hasDominance

/-- Specialized non-circular certificate target for the actual Riemann Li
ledger. -/
abbrev RiemannLiCoupledDominanceCertificate :=
  LiCoupledDominanceCertificate riemannLiArithmeticDecomposition

theorem RiemannLiCoupledDominanceCertificate.liPositivity
    (C : RiemannLiCoupledDominanceCertificate) : RiemannLiPositivity := by
  exact C.sequence_nonneg

/-- The concrete two inequalities that a prime-side construction must prove.
No use of `riemannLiCoefficient` is permitted in the certificate fields. -/
theorem riemannLiPositivity_of_coupled_majorant
    (majorant : ℕ → ℝ)
    (hfinite : ∀ n, riemannLiSFinite n ≤ majorant n)
    (hbudget : ∀ n, majorant n ≤ riemannLiSInfinity n +
      (if n = 0 then 0 else 1)) :
    RiemannLiPositivity := by
  let C : RiemannLiCoupledDominanceCertificate :=
    { majorant := majorant
      finitePlace_le := hfinite
      majorant_le_budget := hbudget }
  exact C.liPositivity

/-! ## Ledger-only no-go theorem -/

/-- A normalized sequence that is negative at every positive index. -/
def negativeUnitLiModel : ℕ → ℝ
  | 0 => 0
  | _ + 1 => -1

@[simp] theorem negativeUnitLiModel_zero : negativeUnitLiModel 0 = 0 := rfl

/-- An exact three-place ledger for the negative model in which every
individual place sequence is nonnegative. -/
def negativeUnitLiDecomposition :
    LiArithmeticDecomposition negativeUnitLiModel where
  archimedean := fun _ ↦ 0
  finitePlace := fun n ↦ if n = 0 then 0 else 1
  pole := fun _ ↦ 0
  identity := by
    intro n
    cases n <;> simp [negativeUnitLiModel]

theorem negativeUnitLiDecomposition_archimedean_nonneg (n : ℕ) :
    0 ≤ negativeUnitLiDecomposition.archimedean n := by
  change 0 ≤ (0 : ℝ)
  norm_num

theorem negativeUnitLiDecomposition_finitePlace_nonneg (n : ℕ) :
    0 ≤ negativeUnitLiDecomposition.finitePlace n := by
  change 0 ≤ (if n = 0 then (0 : ℝ) else 1)
  split <;> norm_num

theorem negativeUnitLiDecomposition_pole_nonneg (n : ℕ) :
    0 ≤ negativeUnitLiDecomposition.pole n := by
  change 0 ≤ (0 : ℝ)
  norm_num

/-- Despite the exact ledger and nonnegativity of all three separate place
sequences, dominance fails already at index one. -/
theorem negativeUnitLiDecomposition_not_dominant :
    ¬negativeUnitLiDecomposition.HasDominance := by
  intro h
  have h1 := h 1
  norm_num [negativeUnitLiDecomposition] at h1

/-- Therefore no theorem based only on an exact decomposition and separate
placewise nonnegativity can imply Li dominance.  Quantitative coupling is an
irreducible additional input. -/
theorem separate_place_nonnegativity_does_not_imply_dominance :
    ∃ (a : ℕ → ℝ) (D : LiArithmeticDecomposition a),
      (∀ n, 0 ≤ D.archimedean n) ∧
      (∀ n, 0 ≤ D.finitePlace n) ∧
      (∀ n, 0 ≤ D.pole n) ∧
      ¬D.HasDominance := by
  exact ⟨negativeUnitLiModel, negativeUnitLiDecomposition,
    negativeUnitLiDecomposition_archimedean_nonneg,
    negativeUnitLiDecomposition_finitePlace_nonneg,
    negativeUnitLiDecomposition_pole_nonneg,
    negativeUnitLiDecomposition_not_dominant⟩

end RiemannLab
