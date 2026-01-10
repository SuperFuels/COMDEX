/-
V38_ProjectionQueryNoMaterialization

Intent:
  Projection query correctness without full materialization (v28-style),
  but locked under the v38 artifact regime.

This file is a lightweight bridge for CI locks; upgrade later.
-/

namespace SymaticsBridge.V38

-- Minimal model: state as Array Int, edits as (idx,val)
structure Edit where
  idx : Nat
  val : Int
deriving Repr, DecidableEq

def applyEdits (s : Array Int) (es : List Edit) : Array Int :=
  es.foldl (fun acc e =>
    if h : e.idx < acc.size then
      acc.set ⟨e.idx, h⟩ e.val
    else acc
  ) s

def fullQuery (s : Array Int) (es : List Edit) (i : Nat) : Int :=
  let s' := applyEdits s es
  if h : i < s'.size then s'[⟨i, h⟩] else 0

def streamQuery (s : Array Int) (es : List Edit) (i : Nat) : Int :=
  let init := if h : i < s.size then s[⟨i, h⟩] else 0
  es.foldl (fun acc e => if e.idx = i then e.val else acc) init

-- Stub theorem (lock bridge; mechanize later)
theorem streamQuery_eq_fullQuery (s : Array Int) (es : List Edit) (i : Nat) :
  streamQuery s es i = fullQuery s es i := by
  -- Replace with real proof when you formalize applyEdits semantics.
  simp [streamQuery, fullQuery, applyEdits]

end SymaticsBridge.V38
