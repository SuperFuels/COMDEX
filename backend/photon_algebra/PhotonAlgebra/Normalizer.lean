import PhotonAlgebra.NormalizerWF

namespace PhotonAlgebra
open PhotonAlgebra

/-- One step is definitionally the WF normalizer (Option A). -/
abbrev normStep : Expr → Expr := normalizeWF

/-- Fuel-bounded normalization to a fixpoint. -/
def normalizeFuel : Nat → Expr → Expr
  | 0, e => e
  | Nat.succ k, e =>
      let e' := normStep e
      if e' == e then
        e
      else
        normalizeFuel k e'

/-- Public normalizer (PA-core). -/
def normalize (e : Expr) : Expr :=
  normalizeFuel (e.size * e.size + 50) e

end PhotonAlgebra
