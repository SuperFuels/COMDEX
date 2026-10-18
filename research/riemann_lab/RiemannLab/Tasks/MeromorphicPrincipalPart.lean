import RiemannLab.Tasks.RectangularResidues
import Mathlib.Analysis.Meromorphic.Order

namespace RiemannLab

open Filter
open scoped Topology

/-!
Generic removal of a simple meromorphic principal part.  This converts the
local residue limits already proved for the zeta contour kernel into the
analytic remainders required by the finite rectangular residue theorem.
-/

/-- If a meromorphic function satisfies `(z-p)F(z) → r`, then subtracting
`r/(z-p)` leaves a function admitting an analytic extension across `p`. -/
theorem exists_analyticAt_sub_principalPart
    {F : ℂ → ℂ} {p r : ℂ}
    (hF : MeromorphicAt F p)
    (hr : Tendsto (fun z : ℂ ↦ (z - p) * F z) (𝓝[≠] p) (𝓝 r)) :
    ∃ g : ℂ → ℂ, AnalyticAt ℂ g p ∧
      (fun z : ℂ ↦ F z - r * (z - p)⁻¹) =ᶠ[𝓝[≠] p] g := by
  let H : ℂ → ℂ := fun z ↦ F z - r * (z - p)⁻¹
  have hshift : MeromorphicAt (fun z : ℂ ↦ z - p) p := by fun_prop
  have hprincipal : MeromorphicAt (fun z : ℂ ↦ r * (z - p)⁻¹) p := by
    exact (MeromorphicAt.const r p).mul hshift.inv
  have hH : MeromorphicAt H p := hF.sub hprincipal
  have hmul : MeromorphicAt (fun z : ℂ ↦ (z - p) * H z) p :=
    hshift.mul hH
  have hlim : Tendsto (fun z : ℂ ↦ (z - p) * H z) (𝓝[≠] p) (𝓝 0) := by
    have hconst : Tendsto (fun _ : ℂ ↦ r) (𝓝[≠] p) (𝓝 r) := tendsto_const_nhds
    have h := hr.sub hconst
    have h' : Tendsto (fun z : ℂ ↦ (z - p) * F z - r) (𝓝[≠] p) (𝓝 0) := by
      simpa using h
    apply h'.congr'
    filter_upwards [self_mem_nhdsWithin] with z hz
    have hzp : z - p ≠ 0 := sub_ne_zero.mpr hz
    dsimp [H]
    field_simp [hzp]
  have horderPos : 0 < meromorphicOrderAt (fun z : ℂ ↦ (z - p) * H z) p :=
    (tendsto_zero_iff_meromorphicOrderAt_pos hmul).mp hlim
  have horderMul :
      meromorphicOrderAt (fun z : ℂ ↦ (z - p) * H z) p =
        1 + meromorphicOrderAt H p := by
    change meromorphicOrderAt ((fun z : ℂ ↦ z - p) * H) p = _
    simpa only [meromorphicOrderAt_id_sub_const] using meromorphicOrderAt_mul hshift hH
  have horderH : 0 ≤ meromorphicOrderAt H p := by
    rw [horderMul] at horderPos
    cases horder : meromorphicOrderAt H p with
    | top => simp
    | coe n =>
        simp [horder] at horderPos
        have hposInt : (0 : ℤ) < 1 + n := by exact_mod_cast horderPos
        norm_cast
        omega
  simpa only [H] using (hH.meromorphicOrderAt_nonneg_iff.mp horderH)

end RiemannLab
