import Mathlib

/-!
v36 — Cosine Similarity (Squared) from Delta Stream (No Materialization)

Buyer-facing claim:
You can maintain a normalized similarity score over a high-cardinality state stream
using only sparse deltas, without reconstructing full snapshots.

We use cosine^2 to avoid sqrt:
  cos^2(x,w) = (dot x w)^2 / (normSq x * normSq w)

Streaming invariants for a point update at index i:
  dot'    = dot  + (new-old)*w_i
  normSq' = normSq + (new^2 - old^2)

This is an exact algebraic identity.
-/

namespace SymaticsBridge.V36

open BigOperators

/-- Dot product over `Fin n`. -/
def dot {n : Nat} (x w : Fin n → Int) : Int :=
  ∑ i : Fin n, x i * w i

/-- Squared L2 norm over `Fin n`. -/
def normSq {n : Nat} (x : Fin n → Int) : Int :=
  ∑ i : Fin n, x i * x i

/-- Point update: set `x i = v`. -/
def update {n : Nat} (x : Fin n → Int) (i : Fin n) (v : Int) : Fin n → Int :=
  fun j => if j = i then v else x j

/-- Dot product update identity for a point update. -/
theorem dot_update {n : Nat} (x w : Fin n → Int) (i : Fin n) (old new : Int)
    (hold : x i = old) :
    dot (update x i new) w = dot x w + (new - old) * w i := by
  classical
  -- expand dot as a sum and split the i term
  simp [dot, update, Finset.sum_ite_eq', hold, sub_eq_add_neg, add_assoc, add_left_comm,
    add_comm, mul_add, add_mul, mul_assoc, mul_left_comm, mul_comm, Finset.sum_add_distrib]

/-- Norm-squared update identity for a point update. -/
theorem normSq_update {n : Nat} (x : Fin n → Int) (i : Fin n) (old new : Int)
    (hold : x i = old) :
    normSq (update x i new) = normSq x + (new*new - old*old) := by
  classical
  -- same shape: split the i term in the sum
  simp [normSq, update, Finset.sum_ite_eq', hold, sub_eq_add_neg, add_assoc, add_left_comm,
    add_comm, mul_add, add_mul, mul_assoc, mul_left_comm, mul_comm, Finset.sum_add_distrib]

/-!
Interpretation:
Given a delta (i, old, new), you can update both dot and normSq in O(1).
Thus cos^2 can be computed from (dot, normSq) without reconstructing x.
-/

end SymaticsBridge.V36