import Mathlib

/-!
v31 — Exact TOP-K within a query set Q from old/new deltas (no full materialization)

We track only indices in Q while scanning edits (idx, old, new).
At the end, we compute topK on the tracked map; it equals topK on the fully applied state restricted to Q.

We keep the statement set-like: Q has no duplicates.
-/

namespace SymaticsBridge.V31

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

/-- Well-formed delta stream: each edit's `old` equals current state at that idx when applied. -/
def WellFormed {n : Nat} : State n → List (Edit n) → Prop
  | _s, [] => True
  | s, e :: es => (s e.idx = e.old) ∧ WellFormed (applyEdit s e) es

/-- Association list map for tracked values (Fin n → Int). -/
abbrev AMap (n : Nat) := List (Fin n × Int)

def amapGet? {n : Nat} (m : AMap n) (i : Fin n) : Option Int :=
  (m.find? (fun p => p.1 = i)).map (fun p => p.2)

def amapSet {n : Nat} (m : AMap n) (i : Fin n) (v : Int) : AMap n :=
  let m' := m.filter (fun p => p.1 ≠ i)
  (i, v) :: m'

/-- Initialize tracked map from s0 and query list Q. -/
def initTrack {n : Nat} (s0 : State n) (Q : List (Fin n)) : AMap n :=
  Q.map (fun i => (i, s0 i))

/-- One edit step: update tracked map iff idx ∈ Q. -/
def stepTrack {n : Nat} (Q : List (Fin n)) (m : AMap n) (e : Edit n) : AMap n :=
  if e.idx ∈ Q then amapSet m e.idx e.new else m

/-- Track only Q across all edits. -/
def trackQ {n : Nat} (s0 : State n) (es : List (Edit n)) (Q : List (Fin n)) : AMap n :=
  es.foldl (stepTrack Q) (initTrack s0 Q)

/-- Restrict a state to Q as a list of pairs. -/
def restrictQ {n : Nat} (s : State n) (Q : List (Fin n)) : AMap n :=
  Q.map (fun i => (i, s i))

/-- Values list from an AMap. -/
def vals {n : Nat} (m : AMap n) : List Int :=
  m.map (fun p => p.2)

/-- topK values (descending), exact: sort and take. -/
def topK (k : Nat) (xs : List Int) : List Int :=
  (xs.qsort (fun a b => b < a)).take k

/-!
Correctness skeleton:

We prove that for set-like Q and well-formed edits,
for each i∈Q: tracked value at i equals (applyEdits s0 es) i.
Then vals(trackQ) is a permutation of vals(restrictQ), hence topK equal.
We keep it simple: prove equality of sorted lists; then take k.
-/

/-- If Q has no duplicates, initTrack contains exactly one entry per i∈Q. -/
def QNoDups {n : Nat} (Q : List (Fin n)) : Prop := Q.Nodup

lemma trackQ_correct_pointwise {n : Nat} (s0 : State n) (es : List (Edit n)) (Q : List (Fin n)) :
    QNoDups Q →
    WellFormed s0 es →
    ∀ i, i ∈ Q →
      amapGet? (trackQ s0 es Q) i = some ((applyEdits s0 es) i) := by
  intro hnodup hwf
  -- Induct over edits, maintaining pointwise correctness
  induction es generalizing s0 with
  | nil =>
      intro i hi
      -- trackQ is initTrack, applyEdits is s0
      simp [trackQ, initTrack, applyEdits, amapGet?]
      -- find? on map(Q) finds (i,s0 i)
      -- Mathlib simp can handle with `List.find?_map` style lemmas are messy;
      -- we can rely on List.find? over (i, v)::... with Nodup ensuring uniqueness.
      -- Keep proof minimal by using `by` rewrite with `List.mem_map` + `List.find?_some`.
      -- (Your existing bridge files likely already have a small AMap lemma library; reuse it.)
      admit
  | cons e rest ih =>
      intro i hi
      rcases hwf with ⟨hold, hwf'⟩
      -- split on whether edit hits i
      by_cases hEq : e.idx = i
      · subst hEq
        have hmem : e.idx ∈ Q := hi
        -- track step will set i to e.new
        -- applyEdits also sets i to e.new at this step
        simp [trackQ, applyEdits, List.foldl, stepTrack, hmem, amapGet?, amapSet, applyEdit]
        admit
      · -- edit does not hit i; tracked value and applyEdits at i unchanged
        have : (applyEdit s0 e) i = s0 i := by
          simp [applyEdit, hEq]
        -- proceed induction on rest with updated state
        have := ih (s0 := applyEdit s0 e) (Q := Q) hnodup hwf' i hi
        -- relate trackQ fold step when idx ∉ i
        -- two cases: e.idx ∈ Q but different index, or e.idx ∉ Q
        -- either way, amapGet? at i unaffected by amapSet at different index.
        admit

/-- Main topK correctness (values): topK computed from tracked Q equals topK from fully materialized state restricted to Q. -/
theorem topK_correct {n : Nat} (s0 : State n) (es : List (Edit n)) (Q : List (Fin n)) (k : Nat) :
    QNoDups Q →
    WellFormed s0 es →
    topK k (vals (trackQ s0 es Q)) = topK k (vals (restrictQ (applyEdits s0 es) Q)) := by
  intro hnodup hwf
  -- Use pointwise equality to show the multiset of values matches, hence sorted lists match.
  -- Then taking k yields equality.
  -- (Implement using `List.Perm` + `List.sort_eq` or multiset coercions.)
  admit

end SymaticsBridge.V31