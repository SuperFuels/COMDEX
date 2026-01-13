namespace PhotonAlgebra

/-- Photon Algebra (PA-core) AST for the Lean formalization.

Minimal, dependency-free Lean 4 encoding intended for:
- a deterministic normalizer (directed strategy)
- theorem checkers (T8–T15) as normal-form equalities

Operator mapping:
  plus      = ⊕
  times     = ⊗
  entangle  = ↔
  neg       = ¬
  cancel    = ⊖
  project   = ★
  collapse  = ∇

`empty` corresponds to ∅.
-/
inductive Expr where
  | atom     (name : String)
  | empty
  | plus     (states : List Expr)          -- ⊕ (n-ary)
  | times    (states : List Expr)          -- ⊗ (n-ary)
  | entangle (a : Expr) (b : Expr)         -- ↔ (binary)
  | neg      (state : Expr)                -- ¬ (unary)
  | cancel   (a : Expr) (b : Expr)         -- ⊖ (binary)
  | project  (state : Expr)                -- ★ (unary)
  | collapse (state : Expr)                -- ∇ (unary)
  deriving Repr, DecidableEq

abbrev EMPTY : Expr := Expr.empty

/-- A simple structural size measure used for termination arguments in the normalizer. -/
def Expr.size : Expr → Nat
  | atom _         => 1
  | empty          => 1
  | plus xs        => 1 + xs.foldl (fun acc e => acc + e.size) 0
  | times xs       => 1 + xs.foldl (fun acc e => acc + e.size) 0
  | entangle a b   => 1 + a.size + b.size
  | neg e          => 1 + e.size
  | cancel a b     => 1 + a.size + b.size
  | project e      => 1 + e.size
  | collapse e     => 1 + e.size

/-- Deterministic structural key (string) for ordering.

We only use this for sorting lists during reification.
It is *not* part of any semantics.
-/
def Expr.key : Expr → String
  | atom s => "A(" ++ s ++ ")"
  | empty => "E(∅)"
  | plus xs => "P(" ++ String.intercalate "," (xs.map Expr.key) ++ ")"
  | times xs => "T(" ++ String.intercalate "," (xs.map Expr.key) ++ ")"
  | entangle a b => "R(" ++ a.key ++ "↔" ++ b.key ++ ")"
  | neg e => "N(¬" ++ e.key ++ ")"
  | cancel a b => "D(" ++ a.key ++ "⊖" ++ b.key ++ ")"
  | project e => "S(★" ++ e.key ++ ")"
  | collapse e => "C(∇" ++ e.key ++ ")"

end PhotonAlgebra
