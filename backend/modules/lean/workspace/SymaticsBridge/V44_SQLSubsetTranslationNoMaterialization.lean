/-
v44 — SQL subset translation (SELECT/WHERE/GROUP BY + simple JOIN), no materialization.

Goal (bridge anchor):
- Define the SQL semantics as bounded folds (no snapshot materialization required in the *spec*).
- Provide a Lean-checked invariant tying the bridge "Agg" state to the semantic JOIN aggregate.

NOTE:
This file is intentionally "bridge-grade": it anchors the meaning of the benchmarked query
without proving the full incremental-update algebra (the Python benchmark already checks
semantic equivalence vs snapshot across the delta stream).
-/

import Std

namespace SymaticsBridge.V44

abbrev Vec := Nat → Int

-- bounded sum over [0,n)
def sumN (n : Nat) (f : Nat → Int) : Int :=
  (List.range n).foldl (fun acc i => acc + f i) 0

def setAt (x : Vec) (i : Nat) (v : Int) : Vec :=
  fun j => if j = i then v else x j

def bucket (i nBuckets : Nat) : Nat :=
  i % nBuckets

def valIf (p : Int → Prop) [DecidablePred p] (x : Int) : Int :=
  if p x then x else 0

-- GROUP BY bucket, SUM(value) with WHERE predicate
def bucketSum (p : Int → Prop) [DecidablePred p]
    (nRows nBuckets : Nat) (x : Vec) (k : Nat) : Int :=
  sumN nRows (fun i =>
    if bucket i nBuckets = k then valIf p (x i) else 0)

-- simple JOIN as dot-product of bucketed sums
def joinAgg (pA : Int → Prop) [DecidablePred pA]
    (nRows nBuckets : Nat) (a b : Vec) : Int :=
  sumN nBuckets (fun k =>
    bucketSum pA nRows nBuckets a k * bucketSum (fun _ => True) nRows nBuckets b k)

-- Bridge state (what the runtime maintains incrementally)
structure Agg where
  sa : Nat → Int
  sb : Nat → Int
  j  : Int

def initAgg (pA : Int → Prop) [DecidablePred pA]
    (nRows nBuckets : Nat) (a b : Vec) : Agg :=
  {
    sa := fun k => bucketSum pA nRows nBuckets a k
    sb := fun k => bucketSum (fun _ => True) nRows nBuckets b k
    j  := joinAgg pA nRows nBuckets a b
  }

-- Definitional anchor: the bridge aggregate equals the SQL semantics at init.
theorem initAgg_ok (pA : Int → Prop) [DecidablePred pA]
    (nRows nBuckets : Nat) (a b : Vec) :
    (initAgg pA nRows nBuckets a b).j = joinAgg pA nRows nBuckets a b := by
  rfl

end SymaticsBridge.V44
