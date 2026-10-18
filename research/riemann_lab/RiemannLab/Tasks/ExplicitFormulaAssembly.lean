import RiemannLab.Tasks.RectangularResidues

namespace RiemannLab

open Filter
open scoped Topology

/-!
Final limit assembly for the Chebyshev explicit formula.

All local residues and the global finite rectangle theorem have already been
proved.  This file isolates the one remaining analytic input: a sequence of
admissible heights on which the three displaced contour edges tend to zero and
the finite residue ledger has the stated value.
-/

/-- The total elementary contribution from the pole at `1`, the Perron pole at
`0`, and all negative-even trivial zeros. -/
noncomputable def explicitFormulaElementaryResidue (x : ℝ) : ℂ :=
  (x : ℂ) - Complex.log (2 * Real.pi) -
    ((1 / 2 : ℝ) * Real.log (1 - x⁻¹ ^ 2) : ℝ)

/-- The elementary residue is `x` minus the archimedean correction used by the
project's final explicit-formula statement. -/
theorem explicitFormulaElementaryResidue_eq (x : ℝ) :
    explicitFormulaElementaryResidue x =
      (x : ℂ) - explicitFormulaArchimedeanTerm x := by
  unfold explicitFormulaElementaryResidue explicitFormulaArchimedeanTerm
  have hpos : 0 < 2 * Real.pi := mul_pos (by norm_num) Real.pi_pos
  rw [show (2 * (Real.pi : ℂ)) = ((2 * Real.pi : ℝ) : ℂ) by push_cast; rfl]
  rw [← Complex.ofReal_log hpos.le]
  push_cast
  ring

/-- Exact remaining analytic interface.  `height` selects admissible horizontal
edges, while `edgeError` is the normalized sum of the top, bottom, and
displaced-left integrals.  The ledger equality incorporates the already proved
finite residue theorem and the limiting trivial-zero correction. -/
def AdmissibleContourLimitTarget : Prop :=
  ∀ x : ℝ, 1 < x → (∀ m : ℕ, x ≠ m) →
    ∃ (c : ℝ) (height : ℕ → ℝ) (edgeError : ℕ → ℂ),
      1 < c ∧
      Tendsto height atTop atTop ∧
      Tendsto edgeError atTop (𝓝 0) ∧
      ∀ n : ℕ,
        truncatedZetaPerronIntegral c (height n) x + edgeError n =
          explicitFormulaElementaryResidue x -
            truncatedNontrivialZeroContribution n x

/-- Once the admissible-height edge estimate and its exact finite ledger are
available, the complete Chebyshev explicit formula follows with no further
complex analysis. -/
theorem chebyshevExplicitFormula_of_admissibleContourLimits
    (hcontour : AdmissibleContourLimitTarget) :
    ChebyshevExplicitFormulaTarget := by
  intro x hx hnotnat
  obtain ⟨c, height, edgeError, hc, hheight, hedge, hledger⟩ :=
    hcontour x hx hnotnat
  have hperron : Tendsto
      (fun n : ℕ ↦ truncatedZetaPerronIntegral c (height n) x) atTop
      (𝓝 (Chebyshev.psi x : ℂ)) :=
    (chebyshevPerronInversion x c hx hnotnat hc).comp hheight
  have hleft : Tendsto
      (fun n : ℕ ↦ truncatedZetaPerronIntegral c (height n) x + edgeError n)
      atTop (𝓝 (Chebyshev.psi x : ℂ)) := by
    simpa using hperron.add hedge
  have hresidue : Tendsto
      (fun n : ℕ ↦ explicitFormulaElementaryResidue x -
        truncatedNontrivialZeroContribution n x)
      atTop (𝓝 (Chebyshev.psi x : ℂ)) := by
    apply hleft.congr'
    exact Eventually.of_forall fun n ↦ hledger n
  have hzero : Tendsto (fun n : ℕ ↦ truncatedNontrivialZeroContribution n x)
      atTop (𝓝 (explicitFormulaElementaryResidue x - (Chebyshev.psi x : ℂ))) := by
    have hconst : Tendsto (fun _ : ℕ ↦ explicitFormulaElementaryResidue x) atTop
        (𝓝 (explicitFormulaElementaryResidue x)) := tendsto_const_nhds
    have h := hconst.sub hresidue
    simpa only [sub_sub_self] using h
  rw [explicitFormulaElementaryResidue_eq x] at hzero
  convert hzero using 1
  simp only [chebyshevPsiRemainder]
  push_cast
  ring

/-- The classical explicit-formula gate has now been reduced exactly to the
admissible-height contour estimate, with both directions recorded at the
programme level. -/
theorem admissibleContourLimits_imply_chebyshevExplicitFormula :
    AdmissibleContourLimitTarget → ChebyshevExplicitFormulaTarget :=
  chebyshevExplicitFormula_of_admissibleContourLimits

end RiemannLab
