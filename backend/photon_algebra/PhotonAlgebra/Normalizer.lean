import PhotonAlgebra.Basic

namespace PhotonAlgebra
open PhotonAlgebra

-- THIS must be the real one-step rewriting function.
def normStep : Expr → Expr
  | e => e   -- replace with your original definition

def normalizeFuel : Nat → Expr → Expr
  | 0, e => e
  | Nat.succ k, e =>
      let e' := normStep e
      if e' == e then e else normalizeFuel k e'

def normalize (e : Expr) : Expr :=
  normalizeFuel (e.size * e.size + 50) e

end PhotonAlgebra