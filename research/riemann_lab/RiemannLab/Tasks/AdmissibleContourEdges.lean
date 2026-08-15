import RiemannLab.Tasks.DisplacedLeftEdge
import RiemannLab.Tasks.ExplicitFormulaAssembly

namespace RiemannLab

open Filter
open scoped Topology Interval

/-!
Assembly of the three displaced sides of the zeta rectangle.  This file fixes
the signs dictated by `rectangleBoundaryIntegral` and proves that the
normalized combined edge error vanishes from the two quantitative analytic
inputs isolated in the preceding modules.
-/

/-- The normalized contribution of the bottom, top, and displaced-left sides
of the rectangle with right edge `Re(s)=c`. -/
noncomputable def normalizedDisplacedEdgeError
    (x c : ℝ) (n : ℕ) : ℂ :=
  (1 / (2 * (Real.pi : ℂ) * Complex.I)) *
    ((∫ σ in displacedLeftRealPart n..c,
        explicitFormulaContourKernel x
          (σ - admissibleZetaHeight n * Complex.I)) -
      (∫ σ in displacedLeftRealPart n..c,
        explicitFormulaContourKernel x
          (σ + admissibleZetaHeight n * Complex.I)) -
      Complex.I *
        (∫ t in (-admissibleZetaHeight n)..admissibleZetaHeight n,
          explicitFormulaContourKernel x
            (displacedLeftRealPart n + t * Complex.I)))

/-- If the admissible-height logarithmic-derivative estimate holds on the
expanding horizontal strips, and the functional-equation estimate controls
the displaced-left side, then the complete normalized three-edge error tends
to zero.  The expanding-strip hypothesis is deliberately explicit: the fixed
strip estimate alone does not control a left endpoint tending to `-∞`. -/
theorem tendsto_normalizedDisplacedEdgeError_zero
    {x c : ℝ}
    (htop : Tendsto (fun n ↦ ∫ σ in displacedLeftRealPart n..c,
      explicitFormulaContourKernel x
        (σ + admissibleZetaHeight n * Complex.I)) atTop (𝓝 0))
    (hbottom : Tendsto (fun n ↦ ∫ σ in displacedLeftRealPart n..c,
      explicitFormulaContourKernel x
        (σ - admissibleZetaHeight n * Complex.I)) atTop (𝓝 0))
    (hleft : Tendsto (fun n ↦ Complex.I *
      (∫ t in (-admissibleZetaHeight n)..admissibleZetaHeight n,
        explicitFormulaContourKernel x
          (displacedLeftRealPart n + t * Complex.I))) atTop (𝓝 0)) :
    Tendsto (normalizedDisplacedEdgeError x c) atTop (𝓝 0) := by
  have hedges := (hbottom.sub htop).sub hleft
  have hconst : Tendsto
      (fun _ : ℕ ↦ (1 / (2 * (Real.pi : ℂ) * Complex.I))) atTop
      (𝓝 (1 / (2 * (Real.pi : ℂ) * Complex.I))) := tendsto_const_nhds
  convert hconst.mul hedges using 1
  · funext n
    unfold normalizedDisplacedEdgeError
    ring
  · ring

/-- The exact expanding-horizontal-edge input which remains after the
zero-free heights have been constructed. -/
def ExpandingHorizontalEdgesDecayTarget (x c : ℝ) : Prop :=
  Tendsto (fun n ↦ ∫ σ in displacedLeftRealPart n..c,
    explicitFormulaContourKernel x
      (σ + admissibleZetaHeight n * Complex.I)) atTop (𝓝 0) ∧
  Tendsto (fun n ↦ ∫ σ in displacedLeftRealPart n..c,
    explicitFormulaContourKernel x
      (σ - admissibleZetaHeight n * Complex.I)) atTop (𝓝 0)

/-- The two remaining analytic estimates imply decay of the full normalized
three-edge contribution. -/
theorem tendsto_normalizedDisplacedEdgeError_zero_of_targets
    {x c : ℝ}
    (hhorizontal : ExpandingHorizontalEdgesDecayTarget x c)
    (hleft : DisplacedLeftKernelDecayTarget x) :
    Tendsto (normalizedDisplacedEdgeError x c) atTop (𝓝 0) :=
  tendsto_normalizedDisplacedEdgeError_zero
    hhorizontal.1 hhorizontal.2 (tendsto_displacedLeft_edge_zero hleft)

end RiemannLab
