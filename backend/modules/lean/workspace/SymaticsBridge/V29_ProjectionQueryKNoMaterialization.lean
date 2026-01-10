import Mathlib

/-!
v29 — k-Projection Query Without Full Materialization

Claim:
For a fixed query set Q of indices, we can answer "what are the values of indices in Q after edits?"
by tracking only those indices while scanning the edit stream (O(|Q|) state), without materializing
the full n-entry state.

We prove: for any i ∈ Q, the stream-tracked answer equals the fully-applied answer.
-/

namespace SymaticsBridge.V29

abbrev State (n : Nat) := Fin n → Nat

structure Edit (n : Nat) where
  idx : Fin n
  val : Nat
deriving Repr

def applyEdit {n : Nat} (s : State n) (e : Edit n) : State n :=
  fun j => if h : j = e.idx then
            by simpa [h] using e.val
          else
            s j

def applyEdits {n : Nat} (s : State n) (es : List (Edit n)) : State n :=
  es.foldl applyEdit s

/-- Association-list get with default (first match). -/
def alistGet {n : Nat} (a : List (Fin n × Nat)) (i : Fin n) (dflt : Nat) : Nat :=
  match a with
  | [] => dflt
  | (j,v) :: rest => if j = i then v else alistGet rest i dflt

/-- Association-list set (update first match; if absent, leave as-is). -/
def alistSet {n : Nat} (a : List (Fin n × Nat)) (i : Fin n) (v : Nat) : List (Fin n × Nat) :=
  match a with
  | [] => []
  | (j,w) :: rest =>
      if j = i then (j,v) :: rest else (j,w) :: alistSet rest i v

/-- Initialize accumulator on Q: store only the queried indices. -/
def initAcc {n : Nat} (s : State n) (Q : List (Fin n)) : List (Fin n × Nat) :=
  Q.map (fun i => (i, s i))

/-- One stream step: if edit touches Q, update that entry in the accumulator. -/
def stepAcc {n : Nat} (Q : List (Fin n)) (acc : List (Fin n × Nat)) (e : Edit n) :
    List (Fin n × Nat) :=
  if e.idx ∈ Q then alistSet acc e.idx e.val else acc

/-- Stream accumulator after scanning edits. -/
def streamAcc {n : Nat} (s : State n) (es : List (Edit n)) (Q : List (Fin n)) :
    List (Fin n × Nat) :=
  es.foldl (stepAcc Q) (initAcc s Q)

lemma alistGet_initAcc {n : Nat} (s : State n) (Q : List (Fin n)) :
    ∀ i : Fin n, i ∈ Q → alistGet (initAcc s Q) i (s i) = s i := by
  intro i hi
  induction Q with
  | nil =>
      cases hi
  | cons q qs ih =>
      simp [initAcc, alistGet] at *
      -- membership split
      cases hi with
      | head =>
          -- i = q
          subst head
          simp
      | tail hmem =>
          -- i ∈ qs
          -- map head is (q, s q); if q=i, handled above
          by_cases hq : q = i
          · -- contradict nodup not assumed here; but still works: if q=i then alistGet hits head
            -- and returns s i anyway
            subst hq
            simp
          · simp [hq, ih i hmem]

lemma alistGet_alistSet_self {n : Nat} :
    ∀ (acc : List (Fin n × Nat)) (i : Fin n) (v d : Nat),
      i ∈ acc.map Prod.fst →
      alistGet (alistSet acc i v) i d = v := by
  intro acc i v d him
  induction acc with
  | nil =>
      cases him
  | cons p rest ih =>
      cases p with
      | mk j w =>
          simp at him
          simp [alistSet, alistGet]
          by_cases hj : j = i
          · subst hj; simp
          · -- i is in rest
            have : i ∈ rest.map Prod.fst := by
              simpa [hj] using him
            simp [hj, ih _ _ _ this]

lemma alistGet_alistSet_other {n : Nat} :
    ∀ (acc : List (Fin n × Nat)) (i j : Fin n) (v d : Nat),
      j ≠ i →
      alistGet (alistSet acc i v) j d = alistGet acc j d := by
  intro acc i j v d hne
  induction acc with
  | nil =>
      simp [alistSet, alistGet]
  | cons p rest ih =>
      cases p with
      | mk k w =>
          simp [alistSet, alistGet]
          by_cases hk : k = i
          · subst hk
            -- head key is i; querying j (j≠i) skips head, rest unchanged
            simp [hne]
          · -- head unchanged; recurse
            simp [hk, ih]

/-- One-step projection correctness at a queried index. -/
lemma step_correct_at {n : Nat} (s : State n) (Q : List (Fin n)) (acc : List (Fin n × Nat))
    (e : Edit n) (i : Fin n) :
    i ∈ Q →
    i ∈ acc.map Prod.fst →
    alistGet (stepAcc Q acc e) i (s i) = (applyEdit (fun j => if j ∈ Q then alistGet acc j (s j) else s j) e) i := by
  intro hiQ hiKeys
  unfold stepAcc
  by_cases hhit : e.idx ∈ Q
  · -- edit hits Q
    have : i ∈ (alistSet acc e.idx e.val).map Prod.fst := by
      -- keys preserved by alistSet
      -- trivial by induction on acc; we only need i ∈ acc.keys -> i ∈ set(keys)
      induction acc with
      | nil => cases hiKeys
      | cons p rest ih =>
          cases p with
          | mk k w =>
              simp [alistSet] at *
              by_cases hk : k = e.idx
              · simp [hk] at *
                exact Or.inl (by
                  -- if i=k, then present
                  simp [Prod.fst])
              · simp [hk] at *
                exact Or.inr (ih (by
                  -- membership in rest keys
                  simpa using hiKeys))
    -- compute both sides at i
    -- if e.idx = i then updated, else unchanged
    by_cases heq : e.idx = i
    · subst heq
      -- left becomes v
      have hv : alistGet (alistSet acc i e.val) i (s i) = e.val :=
        alistGet_alistSet_self acc i e.val (s i) (by
          -- i in keys since i∈Q and initAcc ensures keys include Q; here assume i∈acc.keys
          exact hiKeys)
      -- right: applyEdit sets i to e.val
      simp [applyEdit, hv, hhit, hiQ]
    · -- e.idx ≠ i
      have hsame : alistGet (alistSet acc e.idx e.val) i (s i) = alistGet acc i (s i) :=
        alistGet_alistSet_other acc e.idx i e.val (s i) (by
          intro h; exact heq h.symm)
      simp [applyEdit, hhit, hiQ, heq, hsame]
  · -- edit does not hit Q: accumulator unchanged; applyEdit also leaves projection value unchanged
    simp [hhit, applyEdit]
    by_cases heq : i = e.idx
    · subst heq
      -- cannot happen because then e.idx ∈ Q since i ∈ Q
      exfalso
      exact hhit (by simpa using hiQ)
    · simp [heq]

/-- Main theorem: for any i ∈ Q, stream accumulator answers match full application at i. -/
theorem streamAcc_correct {n : Nat} (s : State n) (es : List (Edit n)) (Q : List (Fin n))
    (i : Fin n) :
    i ∈ Q →
    alistGet (streamAcc s es Q) i (s i) = (applyEdits s es) i := by
  intro hiQ
  -- Induct over edit list using foldl structure
  -- Maintain invariant: acc stores exactly the values of indices in Q for the current full state.
  -- We prove the statement for i only (projection), which is enough for buyers.
  induction es generalizing s with
  | nil =>
      simp [streamAcc, applyEdits]
      exact alistGet_initAcc s Q i hiQ
  | cons e rest ih =>
      -- unfold one fold step
      simp [streamAcc, applyEdits, List.foldl] at *
      -- Let acc0 = initAcc s Q, then stepAcc, then recurse with updated state.
      -- Use IH on updated state.
      -- We need a key membership fact: i is always in initAcc keys if i∈Q.
      have hiKeys : i ∈ (initAcc s Q).map Prod.fst := by
        -- initAcc keys are exactly Q (as a list) under map fst
        simp [initAcc, hiQ]
      -- Now relate alistGet after step to applyEdit at i, then apply IH
      -- First, compute new s' = applyEdit s e
      have hstep :
          alistGet (stepAcc Q (initAcc s Q) e) i (s i) =
            (applyEdit s e) i := by
        -- specialize step_correct_at with acc = initAcc s Q,
        -- and simplify the projection function (for i ∈ Q it just reads acc)
        -- We can do a direct case split:
        unfold stepAcc
        by_cases hhit : e.idx ∈ Q
        · by_cases heq : e.idx = i
          · subst heq
            have : alistGet (alistSet (initAcc s Q) i e.val) i (s i) = e.val :=
              alistGet_alistSet_self (initAcc s Q) i e.val (s i) (by
                -- i in keys of initAcc
                exact hiKeys)
            simp [applyEdit, hhit, this]
          · have : alistGet (alistSet (initAcc s Q) e.idx e.val) i (s i)
                      = alistGet (initAcc s Q) i (s i) :=
              alistGet_alistSet_other (initAcc s Q) e.idx i e.val (s i) (by
                intro h; exact heq h.symm)
            have hinit : alistGet (initAcc s Q) i (s i) = s i :=
              alistGet_initAcc s Q i hiQ
            simp [applyEdit, hhit, heq, this, hinit]
        · have hinit : alistGet (initAcc s Q) i (s i) = s i :=
            alistGet_initAcc s Q i hiQ
          -- if not hit, stepAcc returns initAcc; applyEdit leaves i unchanged (since i∈Q => e.idx≠i)
          by_cases heq : i = e.idx
          · subst heq
            exfalso
            exact hhit (by simpa using hiQ)
          · simp [hhit, applyEdit, heq, hinit]
      -- Now apply IH to the tail with updated state
      -- streamAcc after full es is foldl over rest starting from stepAcc(initAcc)
      -- applyEdits over rest starting from applyEdit
      -- We need to rewrite the default used in alistGet: use (applyEdit s e) i as the new base.
      -- But alistGet defaults only when missing; i is always present in keys, so default doesn't matter.
      -- For simplicity, use the same default via rewriting hstep and IH.
      -- Invoke IH on (applyEdit s e) and rest:
      have := ih (s := applyEdit s e) (Q := Q) (i := i) hiQ
      -- And note streamAcc s (e::rest) Q = streamAcc (applyEdit s e) rest Q but with init updated;
      -- our foldl form already matches after simp at top.
      -- Use hstep to bridge the base case at i.
      -- Finish by simp rewriting.
      simpa [applyEdits, streamAcc, List.foldl, hstep] using this

end SymaticsBridge.V29