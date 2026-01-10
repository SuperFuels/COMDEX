/-
V42 — Incremental Merkle-style state commitment from deltas (no materialization)

Level-A target: no `sorry`.
Dependency-light (core Lean only).

We model a perfect binary Merkle tree abstractly:
- leaf hash:  HLeaf : Int → Hash
- node hash:  HNode : Hash → Hash → Hash

We define:
- rootHash   : full recompute
- updateAt   : structural update at a path (List Bool)
- incRoot    : incremental root recompute along that path (reuse untouched subtree hashes)

Key theorem:
  rootHash (updateAt t p v) = incRoot t p v
-/

namespace SymaticsBridge.V42

abbrev Hash := Nat

variable (HLeaf : Int → Hash)
variable (HNode : Hash → Hash → Hash)

inductive Tree (α : Type) where
  | leaf : α → Tree α
  | node : Tree α → Tree α → Tree α
deriving Repr

open Tree

def rootHash : Tree Int → Hash
| leaf a      => HLeaf a
| node l r    => HNode (rootHash l) (rootHash r)

/-- Update a leaf selected by a path; false=left, true=right.
    If the path ends early at a node, we leave it unchanged (bench always supplies full-height paths). -/
def updateAt : Tree Int → List Bool → Int → Tree Int
| leaf _,    _,      v => leaf v
| node l r,  [],     _ => node l r
| node l r,  b :: p, v =>
    if b then node l (updateAt r p v)
    else      node (updateAt l p v) r

/-- Incremental root recomputation: only re-hash along the updated path. -/
def incRoot : Tree Int → List Bool → Int → Hash
| leaf _,    _,      v => HLeaf v
| node l r,  [],     _ => rootHash (HLeaf:=HLeaf) (HNode:=HNode) (node l r)
| node l r,  b :: p, v =>
    if b then
      HNode (rootHash (HLeaf:=HLeaf) (HNode:=HNode) l) (incRoot r p v)
    else
      HNode (incRoot l p v) (rootHash (HLeaf:=HLeaf) (HNode:=HNode) r)

theorem root_update_eq_inc (t : Tree Int) (p : List Bool) (v : Int) :
  rootHash (HLeaf:=HLeaf) (HNode:=HNode) (updateAt t p v)
    =
  incRoot (HLeaf:=HLeaf) (HNode:=HNode) t p v := by
  induction t generalizing p with
  | leaf a =>
      cases p <;> simp [rootHash, updateAt, incRoot]
  | node l r ihl ihr =>
      cases p with
      | nil =>
          simp [rootHash, updateAt, incRoot]
      | cons b p =>
          cases b <;> simp [rootHash, updateAt, incRoot, ihl, ihr]

end SymaticsBridge.V42
