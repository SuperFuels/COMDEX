import Mathlib

/-!
v34 — Exact histogram (group-by) from delta stream without full materialization.

We model:
- an initial state s0 : Fin n → Int
- a well-formed edit stream that updates indices (idx, old, new)
- a touched map storing the last new value for each touched idx

Then for any bucketing function b : Int → Nat (e.g. mod M),
the histogram counts computed from the reconstructed final state
equal those computed from full materialization.

This is the “group-by” analogue of v33 (range sums) and v32 (top-k).
-/

namespace SymaticsBridge.V34

abbrev State (n : Nat) := Fin n → Int

structure Edit (n : Nat) where
  idx : Fin n
  old : Int
  new : Int
deriving Repr

def applyEdit {n : Nat} (s : State n) (e : Edit n) : State n :=
  fun j => if h : j = e.idx then by simpa [h] using e.new else s j

def applyEdits {n : Nat} (s : State n) (es : List (Edit n)) : State n :=
  es.foldl applyEdit s

def WellFormed {n : Nat} : State n → List (Edit n) → Prop
  | _s, [] => True
  | s, e :: es => (s e.idx = e.old) ∧ WellFormed (applyEdit s e) es

abbrev TMap (n : Nat) := Fin n → Option Int
def emptyMap {n : Nat} : TMap n := fun _ => none
def mapSet {n : Nat} (m : TMap n) (i : Fin n) (v : Int) : TMap n :=
  fun j => if h : j = i then some v else m j

def trackTouched {n : Nat} (es : List (Edit n)) : TMap n :=
  es.foldl (fun m e => mapSet m e.idx e.new) emptyMap

def finalFromMap {n : Nat} (s0 : State n) (m : TMap n) : State n :=
  fun i => match m i with
    | some v => v
    | none   => s0 i

theorem final_state_eq {n : Nat} (s0 : State n) (es : List (Edit n)) :
    WellFormed s0 es →
    finalFromMap s0 (trackTouched es) = applyEdits s0 es := by
  intro hwf
  induction es generalizing s0 with
  | nil =>
      simp [trackTouched, finalFromMap, applyEdits, emptyMap]
  | cons e rest ih =>
      rcases hwf with ⟨hold, hwf'⟩
      funext i
      by_cases hEq : i = e.idx
      · subst hEq
        simp [trackTouched, finalFromMap, applyEdits, List.foldl, mapSet, applyEdit]
      · have : (applyEdit s0 e) i = s0 i := by simp [applyEdit, hEq]
        have ih' := ih (s0 := applyEdit s0 e) hwf'
        simpa [trackTouched, finalFromMap, applyEdits, List.foldl, mapSet, hEq, this]
          using congrArg (fun f => f i) ih'

/-- Histogram as a count-map: bucket → count. -/
abbrev Hist := Nat → Nat

def histEmpty : Hist := fun _ => 0
def histInc (h : Hist) (k : Nat) : Hist := fun j => if j = k then h j + 1 else h j

/-- Build histogram over all indices using a bucket function b : Int → Nat. -/
def histogram {n : Nat} (b : Int → Nat) (s : State n) : Hist :=
  (List.finRange n).foldl (fun h i => histInc h (b (s i))) histEmpty

theorem histogram_correct {n : Nat} (b : Int → Nat) (s0 : State n) (es : List (Edit n)) :
    WellFormed s0 es →
    histogram b (finalFromMap s0 (trackTouched es))
      =
    histogram b (applyEdits s0 es) := by
  intro hwf
  have hEq := final_state_eq (s0 := s0) (es := es) hwf
  simpa [hEq]

end SymaticsBridge.V34