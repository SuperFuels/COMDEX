import Mathlib

/-!
v32 — Heavy hitters (exact TOP-K) from delta stream without full materialization

Idea:
- State s : Fin n → Int
- Deltas are edits (idx, old, new) with well-formedness: old matches current value at idx.
- We track only the touched indices in a finite map `M : Fin n → Option Int`.
- Final value for i is: if i touched then M[i] else s0 i.
- Therefore the computed topK from (touched ∪ untouched-from-s0) equals topK of materialized applyEdits.

This is an exact correctness theorem; no probabilistic sketch.
-/

namespace SymaticsBridge.V32

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

/-- Well-formed delta stream: each edit’s `old` matches the current state at that idx. -/
def WellFormed {n : Nat} : State n → List (Edit n) → Prop
  | _s, [] => True
  | s, e :: es => (s e.idx = e.old) ∧ WellFormed (applyEdit s e) es

/-- Touched-value map modeled as a total function Fin n → Option Int. -/
abbrev TMap (n : Nat) := Fin n → Option Int

def emptyMap {n : Nat} : TMap n := fun _ => none

def mapSet {n : Nat} (m : TMap n) (i : Fin n) (v : Int) : TMap n :=
  fun j => if h : j = i then some v else m j

/-- Track touched indices: update map at edit.idx to edit.new. -/
def trackTouched {n : Nat} (es : List (Edit n)) : TMap n :=
  es.foldl (fun m e => mapSet m e.idx e.new) emptyMap

/-- Reconstruct final value for i from s0 + touched-map. -/
def finalFromMap {n : Nat} (s0 : State n) (m : TMap n) : State n :=
  fun i => match m i with
    | some v => v
    | none   => s0 i

/-- Values list (for topK) from a state over Fin n. -/
def stateVals {n : Nat} (s : State n) : List Int :=
  (List.finRange n).map s

/-- Exact topK values (descending). -/
def topK (k : Nat) (xs : List Int) : List Int :=
  (xs.qsort (fun a b => b < a)).take k

/-- Key lemma: tracking touched indices yields same final state as applying edits. -/
theorem final_state_eq {n : Nat} (s0 : State n) (es : List (Edit n)) :
    WellFormed s0 es →
    finalFromMap s0 (trackTouched es) = applyEdits s0 es := by
  intro hwf
  -- fold induction over edits
  induction es generalizing s0 with
  | nil =>
      simp [trackTouched, finalFromMap, applyEdits, emptyMap]
  | cons e rest ih =>
      rcases hwf with ⟨hold, hwf'⟩
      -- unfold one step of folds
      -- applyEdits (e::rest) = applyEdits (applyEdit s0 e) rest
      -- trackTouched (e::rest) = foldl set (set empty e) rest
      funext i
      -- split whether i = e.idx
      by_cases hEq : i = e.idx
      · subst hEq
        -- finalFromMap uses some e.new at i
        -- applyEdits sets i to e.new at first step, then rest preserves by well-formedness
        simp [trackTouched, finalFromMap, applyEdits, List.foldl, mapSet, applyEdit]
      · -- i != e.idx: first edit doesn't change i; reduce to IH on rest with updated s0
        have : (applyEdit s0 e) i = s0 i := by simp [applyEdit, hEq]
        -- use IH
        have ih' := ih (s0 := applyEdit s0 e) hwf'
        -- now show map-set at other index does not affect lookup at i
        -- and applyEdits agrees via ih'
        -- expand both sides
        simpa [trackTouched, finalFromMap, applyEdits, List.foldl, mapSet, hEq, this] using congrArg (fun f => f i) ih'

/-- Main theorem: topK from touched-map equals topK from full materialization. -/
theorem topK_correct {n : Nat} (s0 : State n) (es : List (Edit n)) (k : Nat) :
    WellFormed s0 es →
    topK k (stateVals (finalFromMap s0 (trackTouched es)))
      =
    topK k (stateVals (applyEdits s0 es)) := by
  intro hwf
  -- immediate from final_state_eq
  simpa [final_state_eq (s0 := s0) (es := es) hwf]

end SymaticsBridge.V32