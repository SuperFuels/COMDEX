/-
V43 — Multi-writer deterministic merge (CRDT-style, no materialization)

Core-only Lean (no Std imports).
We model merge as pointwise Nat.max on packed update payloads.
This gives deterministic, commutative, associative merge (a join-semilattice).
-/

namespace SymaticsBridge.V43

def Vec := Nat → Nat

def mergeDelta (d1 d2 : Vec) : Vec :=
  fun i => Nat.max (d1 i) (d2 i)

-- commutativity
theorem mergeDelta_comm (d1 d2 : Vec) : mergeDelta d1 d2 = mergeDelta d2 d1 := by
  funext i
  simp [mergeDelta, Nat.max_comm]

-- associativity
theorem mergeDelta_assoc (d1 d2 d3 : Vec) :
  mergeDelta (mergeDelta d1 d2) d3 = mergeDelta d1 (mergeDelta d2 d3) := by
  funext i
  simp [mergeDelta, Nat.max_assoc]

-- “apply a delta” is just merging it into the state
def applyDelta (x d : Vec) : Vec := mergeDelta x d

-- applying two deltas is order-independent (CRDT join property)
theorem applyDelta_two_comm (x d1 d2 : Vec) :
  applyDelta (applyDelta x d1) d2 = applyDelta (applyDelta x d2) d1 := by
  funext i
  -- Goal: max (max (x i) (d1 i)) (d2 i) = max (max (x i) (d2 i)) (d1 i)
  -- Use assoc + comm to rewrite both sides to max (x i) (max (d1 i) (d2 i))
  calc
    Nat.max (Nat.max (x i) (d1 i)) (d2 i)
        = Nat.max (x i) (Nat.max (d1 i) (d2 i)) := by
            -- max (max x d1) d2 = max x (max d1 d2)
            simpa [Nat.max_assoc] using (Nat.max_assoc (x i) (d1 i) (d2 i))
    _   = Nat.max (x i) (Nat.max (d2 i) (d1 i)) := by
            simp [Nat.max_comm]
    _   = Nat.max (Nat.max (x i) (d2 i)) (d1 i) := by
            -- reverse of assoc: max x (max d2 d1) = max (max x d2) d1
            simpa [Nat.max_assoc] using (Nat.max_assoc (x i) (d2 i) (d1 i)).symm
  -- close by unfolding applyDelta/mergeDelta
  -- (simp already handled the max-shape; just unfold)
  all_goals
    simp [applyDelta, mergeDelta]

end SymaticsBridge.V43
