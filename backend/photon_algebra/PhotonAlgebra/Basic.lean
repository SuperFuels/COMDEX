namespace PhotonAlgebra

/-- Photon Algebra (PA-core) AST for Lean formalization (dependency-free, Lean4 stable).

We avoid `DecidableEq` and any mutual recursion tricks; we use `BEq` instead.

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
  | plus     (states : List Expr)     -- ⊕ (n-ary)
  | times    (states : List Expr)     -- ⊗ (n-ary)
  | entangle (a : Expr) (b : Expr)    -- ↔
  | neg      (state : Expr)           -- ¬
  | cancel   (a : Expr) (b : Expr)    -- ⊖
  | project  (state : Expr)           -- ★
  | collapse (state : Expr)           -- ∇
  deriving Repr, BEq

abbrev EMPTY : Expr := Expr.empty
instance : Inhabited Expr := ⟨Expr.empty⟩

/-- Structural size (simple measure for fuel sizing). -/
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

/-- Deterministic structural key (string) for ordering/dedup.
Not semantic; only for canonicalization. -/
def Expr.key : Expr → String
  | atom s => "A(" ++ s ++ ")"
  | empty  => "E(∅)"
  | plus xs =>
      "P(" ++ joinKeys xs ++ ")"
  | times xs =>
      "T(" ++ joinKeys xs ++ ")"
  | entangle a b =>
      "R(" ++ a.key ++ "↔" ++ b.key ++ ")"
  | neg e =>
      "N(¬" ++ e.key ++ ")"
  | cancel a b =>
      "D(" ++ a.key ++ "⊖" ++ b.key ++ ")"
  | project e =>
      "S(★" ++ e.key ++ ")"
  | collapse e =>
      "C(∇" ++ e.key ++ ")"
where
  joinKeys : List Expr → String
    | []        => ""
    | [x]       => x.key
    | x :: xs   => x.key ++ "," ++ joinKeys xs

/-- Helper: BEq for lists using Expr's BEq. -/
def beqList (xs ys : List Expr) : Bool :=
  match xs, ys with
  | [], [] => true
  | x::xs, y::ys => (x == y) && beqList xs ys
  | _, _ => false

end PhotonAlgebra