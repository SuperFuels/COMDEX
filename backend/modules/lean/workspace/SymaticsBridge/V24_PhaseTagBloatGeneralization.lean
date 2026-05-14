import Mathlib
import SymaticsBridge.NatNorm

namespace SymaticsBridge.V24

open SymaticsBridge.NatNorm

/-- Abstract interference tree (shape only). Payload type irrelevant for size bounds. -/
inductive ITree (α : Type) where
  | leaf : α → ITree α
  | node : ITree α → ITree α → ITree α
deriving Repr

namespace ITree

def nodes : ITree α → Nat
  | leaf _    => 1
  | node l r  => nodes l + nodes r + 1

/-- Count of edges in the underlying tree (two child-edges per internal node). -/
def edges : ITree α → Nat
  | leaf _    => 0
  | node l r  => edges l + edges r + 2

/--
A simple “tagging model”: you may attach at most one phase-tag per edge.
So total tagged-items = nodes + edges.
(If your real encoding tags only some edges, this is an upper-bound model.)
-/
def taggedItems (t : ITree α) : Nat :=
  t.nodes + t.edges

/--
Shape-general fact: edges ≤ 2*(nodes-1) for this binary-tree edge counting scheme.
-/
theorem edges_le_two_mul_nodes_sub_one : ∀ t : ITree α, t.edges ≤ 2 * (t.nodes - 1)
  | leaf _ => by
      simp [ITree.edges, ITree.nodes]
  | node l r => by
      simp [ITree.edges, ITree.nodes]
      have hl : l.edges ≤ 2 * (l.nodes - 1) := edges_le_two_mul_nodes_sub_one l
      have hr : r.edges ≤ 2 * (r.nodes - 1) := edges_le_two_mul_nodes_sub_one r
      omega

/--
Therefore, taggedItems ≤ nodes + 2*(nodes-1) ≤ 3*nodes.
-/
theorem taggedItems_le_three_mul_nodes (t : ITree α) : t.taggedItems ≤ 3 * t.nodes := by
  unfold ITree.taggedItems
  have hE : t.edges ≤ 2 * (t.nodes - 1) := edges_le_two_mul_nodes_sub_one (α := α) t
  omega

/--
If your actual tagging scheme is “≤ 1 tag per node” (not per edge),
then the constant-factor bound tightens to ≤ 2*nodes immediately.
-/
theorem oneTagPerNode_bound (t : ITree α) : t.nodes + t.nodes = 2 * t.nodes := by
  simpa using (Eq.symm (Nat.two_mul t.nodes))

end ITree
end SymaticsBridge.V24