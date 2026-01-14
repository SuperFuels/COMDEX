import Std

namespace PhotonAlgebra

/-- Photon Algebra core AST. -/
inductive Expr where
  | atom     (name : String)
  | empty
  | plus     (states : List Expr)
  | times    (states : List Expr)
  | entangle (a : Expr) (b : Expr)
  | neg      (state : Expr)
  | cancel   (a : Expr) (b : Expr)
  | project  (state : Expr)
  | collapse (state : Expr)
  deriving Repr

/-- Deterministic structural key used for canonicalization/sorting. -/
def Expr.key : Expr → String
  | atom name       => "A:" ++ name
  | empty           => "E"
  | plus states     =>
      "P[" ++ String.intercalate "," (states.map Expr.key) ++ "]"
  | times states    =>
      "T[" ++ String.intercalate "," (states.map Expr.key) ++ "]"
  | entangle a b    => "En(" ++ a.key ++ "," ++ b.key ++ ")"
  | neg e           => "N(" ++ e.key ++ ")"
  | cancel a b      => "C(" ++ a.key ++ "," ++ b.key ++ ")"
  | project e       => "Pr(" ++ e.key ++ ")"
  | collapse e      => "Co(" ++ e.key ++ ")"

abbrev EMPTY : Expr := Expr.empty
instance : Inhabited Expr := ⟨Expr.empty⟩

/-- Structural size (fuel budget). -/
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

/-- Boolean equality on lists using a provided element equality. -/
def beqListWith {α : Type} (be : α → α → Bool) : List α → List α → Bool
  | [], [] => true
  | x :: xs, y :: ys => be x y && beqListWith be xs ys
  | _, _ => false

/-- Fuelled structural equality for Expr (always terminates). -/
def Expr.beqFuel : Nat → Expr → Expr → Bool
  | 0, _, _ => false
  | (Nat.succ fuel), x, y =>
    match x, y with
    | Expr.atom a,       Expr.atom b       => decide (a = b)
    | Expr.empty,        Expr.empty        => true
    | Expr.plus xs,      Expr.plus ys      =>
        beqListWith (fun a b => Expr.beqFuel fuel a b) xs ys
    | Expr.times xs,     Expr.times ys     =>
        beqListWith (fun a b => Expr.beqFuel fuel a b) xs ys
    | Expr.entangle a b, Expr.entangle c d =>
        Expr.beqFuel fuel a c && Expr.beqFuel fuel b d
    | Expr.neg a,        Expr.neg b        =>
        Expr.beqFuel fuel a b
    | Expr.cancel a b,   Expr.cancel c d   =>
        Expr.beqFuel fuel a c && Expr.beqFuel fuel b d
    | Expr.project a,    Expr.project b    =>
        Expr.beqFuel fuel a b
    | Expr.collapse a,   Expr.collapse b   =>
        Expr.beqFuel fuel a b
    | _, _ => false

/-- Default BEq for Expr uses size-based fuel. -/
def Expr.beq (x y : Expr) : Bool :=
  Expr.beqFuel (x.size + y.size + 1) x y

instance : BEq Expr := ⟨Expr.beq⟩

/-- Your original helper name. -/
def beqList (xs ys : List Expr) : Bool :=
  beqListWith (fun x y => x == y) xs ys

end PhotonAlgebra