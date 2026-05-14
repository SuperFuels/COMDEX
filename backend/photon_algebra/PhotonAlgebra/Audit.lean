import PhotonAlgebra.Basic
import PhotonAlgebra.Normalizer
import PhotonAlgebra.NormalizerWF
import PhotonAlgebra.NormalizerBridge

open PhotonAlgebra

namespace PhotonAlgebra

def assert (label : String) (b : Bool) : IO Unit := do
  if b then
    pure ()
  else
    throw (IO.userError s!"AUDIT FAIL: {label}")

def audit : IO Unit := do
  let a : Expr := Expr.atom "a"
  let b : Expr := Expr.atom "b"
  let c : Expr := Expr.atom "c"

  let sum  (x y : Expr) := Expr.plus [x, y]
  let prod (x y : Expr) := Expr.times [x, y]

  let e1 := prod a (sum b c)
  let e2 := sum (prod a b) (prod a c)

  IO.println "Audit: normalize (fuel) vs normalizeWF (structural)"
  assert "agrees e1" (agrees e1)
  assert "agrees e2" (agrees e2)
  assert "wf e1==e2" ((normalizeWF e1) == (normalizeWF e2))
  IO.println "Audit OK"

end PhotonAlgebra

-- IMPORTANT: exe entrypoint must be top-level (not namespaced)
def main : IO Unit :=
  PhotonAlgebra.audit