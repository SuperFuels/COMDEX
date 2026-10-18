import RiemannLab.Tasks.LiSubdominantTail
import RiemannLab.Tasks.ExplicitFormula

namespace RiemannLab

open Filter Topology

/-!
# The summable-envelope interface on the actual zeta-zero type

This file replaces the abstract countable mode family by the subtype of
actual nontrivial zeta zeros.  Multiplicity is the analytic vanishing order
of zeta.  The remaining analytic obligation is stated without disguise:
the chosen localized amplitude must be summable after multiplication by
that multiplicity.
-/

/-- The type of actual nontrivial zeta zeros. -/
def NontrivialZetaZeroPoint := { ρ : ℂ // IsNontrivialZetaZero ρ }

/-- The actual nontrivial zero set is countable, because the verified compact
truncations are finite and exhaust it. -/
theorem nontrivialZetaZeroSet_countable :
    { ρ : ℂ | IsNontrivialZetaZero ρ }.Countable := by
  let U : Set ℂ := ⋃ n : ℕ, (↑(compactNontrivialZetaZeros n) : Set ℂ)
  have hU : U.Countable := by
    apply Set.countable_iUnion
    intro n
    exact (Finset.finite_toSet (compactNontrivialZetaZeros n)).countable
  apply hU.mono
  intro ρ hρ
  obtain ⟨n, hn⟩ := hρ.exists_mem_compactTruncation
  exact Set.mem_iUnion.mpr ⟨n, hn⟩

noncomputable instance : Countable NontrivialZetaZeroPoint := by
  obtain ⟨f, hf⟩ := Set.countable_iff_exists_injective.mp
    nontrivialZetaZeroSet_countable
  exact hf.countable

/-- Li spectral radius of an actual nontrivial zero. -/
noncomputable def zetaLiRate (ρ : NontrivialZetaZeroPoint) : ℝ :=
  ‖1 - ρ.1⁻¹‖

/-- Intrinsic analytic multiplicity of an actual nontrivial zero. -/
noncomputable def zetaZeroMultiplicity (ρ : NontrivialZetaZeroPoint) : ℕ :=
  analyticOrderNatAt riemannZeta ρ.1

/-- Multiplicity-weighted norm of a localized zero amplitude. -/
noncomputable def zetaModeWeight
    (amplitude : NontrivialZetaZeroPoint → ℂ)
    (ρ : NontrivialZetaZeroPoint) : ℝ :=
  zetaZeroMultiplicity ρ * ‖amplitude ρ‖

/-- Actual zeros whose Li rate is at most the chosen subdominant threshold. -/
def SubdominantZetaZeroPoints (r : ℝ) :=
  { ρ : NontrivialZetaZeroPoint // zetaLiRate ρ ≤ r }

noncomputable instance (r : ℝ) : Countable (SubdominantZetaZeroPoints r) :=
  SetCoe.countable _

theorem zetaModeWeight_nonneg
    (amplitude : NontrivialZetaZeroPoint → ℂ) (ρ : NontrivialZetaZeroPoint) :
    0 ≤ zetaModeWeight amplitude ρ := by
  exact mul_nonneg (Nat.cast_nonneg _) (norm_nonneg _)

/-- The abstract infinite-family theorem instantiated on the complete actual
subdominant zeta-zero subtype, including analytic multiplicities. -/
theorem eventually_actual_zeta_tail_lt_target
    (amplitude : NontrivialZetaZeroPoint → ℂ)
    {A r R : ℝ}
    (hsum : Summable (zetaModeWeight amplitude))
    (hA : 0 < A) (hr0 : 0 ≤ r) (hR : 0 < R) (hgap : r < R) :
    ∀ᶠ n : ℕ in atTop,
      ∑' ρ : SubdominantZetaZeroPoints r,
          zetaModeWeight amplitude ρ.1 * zetaLiRate ρ.1 ^ n <
        A * R ^ n := by
  apply eventually_tsum_subdominant_lt_target
    (fun ρ : SubdominantZetaZeroPoints r ↦ zetaModeWeight amplitude ρ.1)
    (fun ρ : SubdominantZetaZeroPoints r ↦ zetaLiRate ρ.1)
  · exact hsum.subtype (fun ρ ↦ zetaLiRate ρ ≤ r)
  · intro ρ
    exact zetaModeWeight_nonneg amplitude ρ.1
  · intro ρ
    exact norm_nonneg (1 - ρ.1.1⁻¹)
  · intro ρ
    exact ρ.2
  · exact hA
  · exact hr0
  · exact hR
  · exact hgap

/-- Under RH failure, the verified expansive target and finite dominant
cluster reduce the entire slower actual zeta divisor to one explicit
summability obligation for the localized amplitude. -/
theorem not_rh_actual_zeta_tail_reduction
    (hRH : ¬RiemannHypothesis) :
    ∃ target : NontrivialZetaZeroPoint, ∃ r : ℝ,
      1 < r ∧
      r < zetaLiRate target ∧
      {z : ℂ | IsNontrivialZetaZero z ∧ r ≤ ‖1 - z⁻¹‖}.Finite ∧
      ∀ (amplitude : NontrivialZetaZeroPoint → ℂ) (A : ℝ),
        Summable (zetaModeWeight amplitude) → 0 < A →
        ∀ᶠ n : ℕ in atTop,
          ∑' ρ : SubdominantZetaZeroPoints r,
              zetaModeWeight amplitude ρ.1 * zetaLiRate ρ.1 ^ n <
            A * zetaLiRate target ^ n := by
  obtain ⟨ρ, r, hρ, hr, hrtarget, hfinite⟩ :=
    not_riemannHypothesis_exists_expansive_target_finite_cluster hRH
  let target : NontrivialZetaZeroPoint := ⟨ρ, hρ⟩
  refine ⟨target, r, hr, ?_, hfinite, ?_⟩
  · simpa [zetaLiRate, target] using hrtarget
  · intro amplitude A hsum hA
    have hgap : r < zetaLiRate target := by
      simpa [zetaLiRate, target] using hrtarget
    exact eventually_actual_zeta_tail_lt_target
      (A := A) (r := r) (R := zetaLiRate target)
      amplitude hsum hA (le_trans zero_le_one hr.le)
      (lt_trans (lt_trans zero_lt_one hr) hgap) hgap

end RiemannLab
