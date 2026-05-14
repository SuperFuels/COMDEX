import PhotonAlgebra.Basic
import PhotonAlgebra.Normalizer
import PhotonAlgebra.NormalizerWF
import PhotonAlgebra.Theorems

open PhotonAlgebra

def assertEqExpr (label : String) (x y : Expr) : IO Unit := do
  if x == y then
    pure ()
  else
    IO.eprintln s!"FAIL: {label}"
    IO.eprintln s!"  fuel = {repr x}"
    IO.eprintln s!"  wf   = {repr y}"
    throw (IO.userError label)

def main : IO Unit := do
  let a : Expr := Expr.atom "a"
  let b : Expr := Expr.atom "b"
  let c : Expr := Expr.atom "c"

  let e1 := PROD a (SUM b c)
  let e2 := SUM (PROD a b) (PROD a c)

  let nfFuel1 := normalize e1
  let nfWF1   := normalizeWF e1
  let nfFuel2 := normalize e2
  let nfWF2   := normalizeWF e2

  IO.println "PhotonAlgebra smoke-test (Lean)"
  IO.println s!"wf (a ⊗ (b ⊕ c)) = {repr nfWF1}"
  IO.println s!"wf ((a ⊗ b) ⊕ (a ⊗ c)) = {repr nfWF2}"

  -- Undeniable: must match the fuel normalizer too.
  assertEqExpr "fuel vs wf: a ⊗ (b ⊕ c)" nfFuel1 nfWF1
  assertEqExpr "fuel vs wf: (a ⊗ b) ⊕ (a ⊗ c)" nfFuel2 nfWF2

  -- Also ensure the two forms agree under WF.
  assertEqExpr "wf distributivity witness" nfWF1 nfWF2

  IO.println "OK (compiled + normalize + normalizeWF agree)."