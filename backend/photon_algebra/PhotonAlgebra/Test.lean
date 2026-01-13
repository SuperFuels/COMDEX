import PhotonAlgebra.Basic
import PhotonAlgebra.Normalizer
import PhotonAlgebra.Theorems

namespace PhotonAlgebra

open Expr

private def assert (name : String) (b : Bool) : IO Unit :=
  if b then
    IO.println s!"[PASS] {name}"
  else
    throw (IO.userError s!"[FAIL] {name}")

/-- A few deterministic sample expressions for smoke-testing. -/
private def samples : List Expr :=
  let a := atom "a"
  let b := atom "b"
  let c := atom "c"
  [ a,
    b,
    c,
    plus [a, b],
    times [a, b],
    neg (neg a),
    entangle a (plus [b, c]),
    project (entangle a b),
    collapse (plus [a, empty]),
    cancel a empty
  ]

private def runAll : IO Unit := do
  let a := atom "a"
  let b := atom "b"
  let c := atom "c"

  -- Theorems (T8–T15)
  assert "T8" (theorem_T8 a b c)
  assert "T9" (theorem_T9 a)
  assert "T10" (theorem_T10 a b c)
  assert "T11" (theorem_T11 (plus [a, times [a, b], empty]))
  assert "T12" (theorem_T12 a b)
  assert "T13" (theorem_T13 a b)

  -- T14 is a non-theorem: do NOT assert it is true.
  IO.println s!"[INFO] T14 (non-theorem) returned: {theorem_T14 a b c}"

  assert "T15" (theorem_T15 a)

  -- Small normalizer sanity: idempotence on a few samples
  for e in samples do
    let n1 := norm e
    let n2 := norm n1
    assert s!"idempotence {Expr.key e}" (decide (n1 = n2))

/-- `lake exe photon_algebra_test` entrypoint. -/
def main : IO Unit := do
  IO.println "PhotonAlgebra Lean smoke tests"
  runAll
  IO.println "All checks passed."

end PhotonAlgebra
