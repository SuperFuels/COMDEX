import Mathlib

/-!
v28 — Projection Query Without Full Materialization (Template+Delta stream query)

Buyer-facing claim:
Given a state vector and a stream of sparse edits (deltas), you can answer a query for one index `i`
by scanning only the deltas and tracking a single accumulator, without materializing the full state.
This is provably equal to applying the deltas to the full state and then reading `i`.

This is the "zero full decompression / no full materialization" guarantee for common queries.
-/

namespace SymaticsBridge.V28

/-- A state is a function from indices to values. -/
abbrev State (n : Nat) := Fin n → Nat

/-- One edit in a delta stream: set index `idx` to `val`. -/
structure Edit (n : Nat) where
  idx : Fin n
  val : Nat
deriving Repr

/-- Apply one edit to a state. -/
def applyEdit {n : Nat} (s : State n) (e : Edit n) : State n :=
  fun j => if h : j = e.idx then
            -- rewrite by equality
            by simpa [h] using e.val
          else
            s j

/-- Apply a list of edits to a state (left fold). -/
def applyEdits {n : Nat} (s : State n) (es : List (Edit n)) : State n :=
  es.foldl applyEdit s

/-- Full-materialization query result: apply edits, then read index `i`. -/
def fullQuery {n : Nat} (s : State n) (es : List (Edit n)) (i : Fin n) : Nat :=
  (applyEdits s es) i

/-- Stream query: track only the value at index `i` while scanning edits. -/
def streamQuery {n : Nat} (s : State n) (es : List (Edit n)) (i : Fin n) : Nat :=
  es.foldl (fun acc e => if e.idx = i then e.val else acc) (s i)

/-- Key lemma: applying one edit then reading `i` matches the one-step stream update. -/
lemma oneStep {n : Nat} (s : State n) (e : Edit n) (i : Fin n) :
    (applyEdit s e) i = (if e.idx = i then e.val else s i) := by
  unfold applyEdit
  by_cases h : i = e.idx
  · -- then i hits the edited index
    subst h
    simp
  · -- otherwise unchanged
    have : ¬ i = e.idx := h
    simp [this]

/-- Main theorem: streamQuery equals fullQuery for any edit list. -/
theorem streamQuery_correct {n : Nat} (s : State n) (es : List (Edit n)) (i : Fin n) :
    streamQuery s es i = fullQuery s es i := by
  -- Induction on the edit list
  induction es generalizing s with
  | nil =>
      simp [streamQuery, fullQuery, applyEdits]
  | cons e rest ih =>
      -- unfold one fold step on both sides
      simp [streamQuery, fullQuery, applyEdits, List.foldl] at *
      -- reduce to the one-step lemma + IH
      -- streamQuery step:
      -- acc' = if e.idx=i then e.val else (s i)
      -- then ih on rest with updated state
      have hs : (applyEdit s e) i = (if e.idx = i then e.val else s i) := oneStep s e i
      -- rewrite, then apply IH with s := applyEdit s e
      -- note: foldl on rest matches applyEdits on rest
      simpa [hs] using (ih (s := applyEdit s e))

end SymaticsBridge.V28