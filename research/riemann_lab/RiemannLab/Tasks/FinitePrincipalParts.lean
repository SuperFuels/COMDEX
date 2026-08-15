import RiemannLab.Tasks.MeromorphicPrincipalPart
import Mathlib.Data.Finset.Update

namespace RiemannLab

open Filter Set
open scoped Topology

/-!
Patching finitely many local meromorphic principal parts into one globally
analytic remainder.  This is the abstract contour-level bridge between local
residue computations and the rectangular finite-residue theorem.
-/

/-- A meromorphic function with a prescribed simple principal part at each
point of a finite set, and analytic away from that set, is a finite sum of
those principal parts plus one entire function.  The word "simple" refers to
the denominator; the residue may already contain the full multiplicity of a
zero of the underlying function. -/
theorem exists_analyticAt_all_sub_finset_principalParts
    (F residue : ℂ → ℂ) (P : Finset ℂ)
    (hmer : ∀ p ∈ P, MeromorphicAt F p)
    (hres : ∀ p ∈ P,
      Tendsto (fun z : ℂ ↦ (z - p) * F z) (𝓝[≠] p) (𝓝 (residue p)))
    (hana : ∀ z ∉ P, AnalyticAt ℂ F z) :
    ∃ g : ℂ → ℂ, (∀ z, AnalyticAt ℂ g z) ∧
      ∀ z ∉ P, F z = g z + ∑ p ∈ P, residue p * (z - p)⁻¹ := by
  classical
  let H : ℂ → ℂ := fun z ↦ F z - ∑ p ∈ P, residue p * (z - p)⁻¹
  have hlocal : ∀ p : ↑P, ∃ gp : ℂ → ℂ, AnalyticAt ℂ gp p ∧
      H =ᶠ[𝓝[≠] (p : ℂ)] gp := by
    intro p
    obtain ⟨gp, hgp, heq⟩ := exists_analyticAt_sub_principalPart
      (hmer p p.property) (hres p p.property)
    let other : ℂ → ℂ := fun z ↦
      ∑ q ∈ P.erase (p : ℂ), residue q * (z - q)⁻¹
    have hother : AnalyticAt ℂ other p := by
      dsimp [other]
      have hterm : ∀ q ∈ P.erase (p : ℂ),
          AnalyticAt ℂ (fun z ↦ residue q * (z - q)⁻¹) p := by
        intro q hq
        have hqp : q ≠ (p : ℂ) := Finset.ne_of_mem_erase hq
        have hpq : (p : ℂ) - q ≠ 0 := sub_ne_zero.mpr hqp.symm
        fun_prop
      exact Finset.analyticAt_fun_sum _ hterm
    refine ⟨fun z ↦ gp z - other z, hgp.sub hother, ?_⟩
    filter_upwards [heq] with z hz
    dsimp [H, other] at hz ⊢
    rw [← Finset.sum_erase_add _ _ p.property]
    calc
      F z - ((∑ x ∈ P.erase (p : ℂ), residue x * (z - x)⁻¹) +
          residue p * (z - p)⁻¹) =
          (F z - residue p * (z - p)⁻¹) -
            ∑ x ∈ P.erase (p : ℂ), residue x * (z - x)⁻¹ := by ring
      _ = gp z - ∑ q ∈ P.erase (p : ℂ), residue q * (z - q)⁻¹ := by rw [hz]
  choose gpAt hlocalAna hlocalEq using hlocal
  let g : ℂ → ℂ := fun z ↦ if hz : z ∈ P then gpAt ⟨z, hz⟩ z else H z
  refine ⟨g, ?_, ?_⟩
  · intro z
    by_cases hz : z ∈ P
    · let p : ↑P := ⟨z, hz⟩
      have havoid : ∀ᶠ y in 𝓝 z, ∀ q ∈ P.erase z, y ≠ q := by
        rw [P.erase z |>.eventually_all]
        intro q hq
        have hmem : {q}ᶜ ∈ 𝓝 z := compl_singleton_mem_nhds_iff.mpr
          (Finset.ne_of_mem_erase hq).symm
        filter_upwards [hmem] with y hy
        simpa only [Set.mem_compl_iff, Set.mem_singleton_iff] using hy
      have hlocalN : ∀ᶠ y in 𝓝 z, y ≠ z → H y = gpAt p y := by
        simpa only [p, Set.mem_compl_iff, Set.mem_singleton_iff] using
          (eventuallyEq_nhdsWithin_iff.mp (hlocalEq p))
      have heq : gpAt p =ᶠ[𝓝 z] g := by
        filter_upwards [havoid, hlocalN] with y hy hloc
        by_cases hyz : y = z
        · subst y
          simp only [g, dif_pos hz]
          congr
        · have hyP : y ∉ P := by
            intro hyP
            have : y ∈ P.erase z := Finset.mem_erase.mpr ⟨hyz, hyP⟩
            exact hy y this rfl
          simp only [g, dif_neg hyP]
          exact (hloc hyz).symm
      exact (hlocalAna p).congr heq
    · have havoid : ∀ᶠ y in 𝓝 z, ∀ q ∈ P, y ≠ q := by
        rw [P.eventually_all]
        intro q hq
        have hmem : {q}ᶜ ∈ 𝓝 z := compl_singleton_mem_nhds_iff.mpr
          (fun h ↦ hz (h ▸ hq))
        filter_upwards [hmem] with y hy
        simpa only [Set.mem_compl_iff, Set.mem_singleton_iff] using hy
      have hsum : AnalyticAt ℂ (fun y ↦ ∑ p ∈ P, residue p * (y - p)⁻¹) z := by
        apply Finset.analyticAt_fun_sum
        intro p hp
        have hzp : z - p ≠ 0 := sub_ne_zero.mpr (fun h ↦ hz (h ▸ hp))
        fun_prop
      have hH : AnalyticAt ℂ H z := (hana z hz).sub hsum
      apply hH.congr
      filter_upwards [havoid] with y hy
      have hyP : y ∉ P := fun hyP ↦ hy y hyP rfl
      simp only [g, dif_neg hyP]
  · intro z hz
    simp only [g, dif_neg hz, H]
    ring

end RiemannLab
