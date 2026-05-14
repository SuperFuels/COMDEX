import Tessaris.Symatics.Prelude

namespace Tessaris.Symatics.Bridge

/-!
Bridge v16: DAG reuse vs tree duplication (Prelude-only, no mutual recursion).

We model a *binary* tree language (enough for the bridge claim, and avoids List recursion):

  Expr := leaf n | node a b

We pick a fixed subtree `S` and build a family that duplicates `S` k times in a left-associated chain:

  dup(0)   = S
  dup(k+1) = node (dup k) S

Then:
  nodes(dup k) = (k+1)*nodes(S) + k     (tree duplicates S each time + adds k internal nodes)

A DAG/interned representation would store `S` once and then k references:
  dagSize(S,k) = nodes(S) + (k+1)   (one S + k extra reference-nodes; constant-factor model)

This is the formal justification for the v16 benchmark: tree-only encodings scale ~k*|S|,
while DAG/intern stays ~|S| + k.
-/

inductive Expr where
  | leaf : Nat → Expr
  | node : Expr → Expr → Expr
deriving Repr, DecidableEq

open Expr

/-- Syntactic node count. -/
def nodes : Expr → Nat
  | leaf _    => 1
  | node a b  => 1 + nodes a + nodes b

/-- Duplicate S k times as a chain: dup(0)=S; dup(k+1)=node (dup k) S. -/
def dup (S : Expr) : Nat → Expr
  | 0     => S
  | k + 1 => node (dup S k) S

/-- Simple DAG/intern size model: store S once, then k extra references. -/
def dagSize (S : Expr) (k : Nat) : Nat :=
  nodes S + (k + 1)

/-- Lemma: nodes(dup S k) = (k+1)*nodes S + k. -/
theorem nodes_dup (S : Expr) : ∀ k : Nat,
    nodes (dup S k) = (k + 1) * nodes S + k := by
  intro k
  induction k with
  | zero =>
      -- dup S 0 = S
      simp [dup]
  | succ k ih =>
      -- dup S (k+1) = node (dup S k) S
      calc
        nodes (dup S (k + 1))
            = nodes (node (dup S k) S) := by
                simp [dup]
        _   = 1 + nodes (dup S k) + nodes S := by
                simp [nodes]
        _   = 1 + ((k + 1) * nodes S + k) + nodes S := by
                simp [ih]
        _   = ((k + 2) * nodes S) + (k + 1) := by
                -- normalize arithmetic:
                -- 1 + ( (k+1)*a + k ) + a = (k+2)*a + (k+1)
                -- rewrite (k+2)*a = (k+1)*a + a
                -- and (k+1) = 1 + k
                -- then reassociate/commute
                have hMul : (k + 2) * nodes S = (k + 1) * nodes S + nodes S := by
                  -- (k+2) = (k+1)+1, and Nat.mul_succ: m*(n+1)=m*n+m
                  -- Use mul_comm to use the lemma in the convenient orientation.
                  -- (k+2)*a = a*(k+2) = a*((k+1)+1) = a*(k+1)+a = (k+1)*a + a
                  calc
                    (k + 2) * nodes S
                        = nodes S * (k + 2) := by
                            simp [Nat.mul_comm]
                    _   = nodes S * ((k + 1) + 1) := by
                            simp [Nat.add_assoc]
                    _   = nodes S * (k + 1) + nodes S := by
                            simp [Nat.mul_succ]
                    _   = (k + 1) * nodes S + nodes S := by
                            simp [Nat.mul_comm, Nat.add_comm]
                -- Now finish the main normalization using hMul.
                -- Goal: 1 + ((k + 1) * a + k) + a = (k+2)*a + (k+1)
                -- Replace RHS (k+2)*a with (k+1)*a + a, and (k+1) with 1+k, then simp.
                -- We'll do it as a calc chain.
                calc
                  1 + ((k + 1) * nodes S + k) + nodes S
                      = ((k + 1) * nodes S + nodes S) + (1 + k) := by
                          -- regroup and commute: (1 + X + a) -> (X + a) + (1 + k)
                          simp [Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]
                  _   = (k + 2) * nodes S + (k + 1) := by
                          -- use hMul and 1+k = k+1
                          simp [hMul, Nat.add_comm, Nat.add_assoc]
        _   = (k + 1 + 1) * nodes S + (k + 1) := by
                simp [Nat.add_assoc]
        _   = ((k + 1) + 1) * nodes S + (k + 1) := by
                simp [Nat.add_assoc]

/-- Bridge statement: tree duplication vs DAG/intern model. -/
theorem bridge_dag_reuse (S : Expr) (k : Nat) :
    nodes (dup S k) = (k + 1) * nodes S + k ∧ dagSize S k = nodes S + (k + 1) := by
  exact ⟨nodes_dup S k, rfl⟩

end Tessaris.Symatics.Bridge
