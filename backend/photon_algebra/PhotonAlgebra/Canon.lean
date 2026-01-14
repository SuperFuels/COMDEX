import PhotonAlgebra.Basic

namespace PhotonAlgebra
open PhotonAlgebra

/-- String ≤ as Bool using `compare` (no extra imports). -/
def leStr (a b : String) : Bool :=
  match compare a b with
  | Ordering.lt => true
  | Ordering.eq => true
  | Ordering.gt => false

/-- Insert into a list sorted by Expr.key (insertion sort). -/
def insertByKey (x : Expr) : List Expr → List Expr
  | [] => [x]
  | y :: ys =>
      if leStr x.key y.key then
        x :: y :: ys
      else
        y :: insertByKey x ys

/-- Deterministic sort by key (insertion sort; small inputs). -/
def sortByKey (xs : List Expr) : List Expr :=
  xs.foldl (fun acc x => insertByKey x acc) []

/-- Dedup adjacent-by-key after sorting. -/
def dedupSortedByKey (xs : List Expr) : List Expr :=
  let rec go (prev? : Option String) (acc : List Expr) (rest : List Expr) :=
    match rest with
    | [] => acc.reverse
    | x :: rs =>
        let k := x.key
        match prev? with
        | some pk =>
            if k == pk then
              go prev? acc rs
            else
              go (some k) (x :: acc) rs
        | none =>
            go (some k) (x :: acc) rs
  go none [] xs

/-- Flatten nested ⊕. -/
def flattenPlus : List Expr → List Expr
  | [] => []
  | (Expr.plus ys) :: xs => ys ++ flattenPlus xs
  | x :: xs => x :: flattenPlus xs

/-- Flatten nested ⊗. -/
def flattenTimes : List Expr → List Expr
  | [] => []
  | (Expr.times ys) :: xs => ys ++ flattenTimes xs
  | x :: xs => x :: flattenTimes xs

/-- True iff `p` is a product containing factor `f` (syntactic). -/
def timesHasFactor (p f : Expr) : Bool :=
  match p with
  | Expr.times fs => fs.any (fun x => x == f)
  | _ => false

/--
If *all* terms are `entangle a _` with the same `a`, return `(a, rights)` so
the caller can build a *canonical* RHS (do **not** construct `Expr.plus` here).
-/
def factorEntangleIfPossible (terms : List Expr) : Option (Expr × List Expr) :=
  match terms with
  | [] => none
  | (Expr.entangle a b) :: rest =>
      if rest.all (fun t =>
        match t with
        | Expr.entangle a' _ => a' == a
        | _ => false
      ) then
        let rights :=
          b :: (rest.map (fun t =>
            match t with
            | Expr.entangle _ r => r
            | _ => Expr.empty))
        some (a, rights)
      else
        none
  | _ => none

/-- Absorption: if a term `t` appears in ⊕, drop any product term containing `t` as a factor. -/
def absorb (terms : List Expr) : List Expr :=
  let bases := terms.filter (fun t =>
    match t with
    | Expr.times _ => false
    | _ => true
  )
  terms.filter (fun t =>
    match t with
    | Expr.times _ =>
        !(bases.any (fun b => timesHasFactor t b))
    | _ => true
  )

/--
Canonicalize a sum **without** factor-entangle.
This is a single, non-recursive pipeline step used to keep termination simple,
and to ensure factor-entangle returns a WF (canonical) RHS.
-/
def canonPlusNoFactor (terms : List Expr) : Expr :=
  let xs2 := flattenPlus terms
  let xs3 := xs2.filter (fun t => !(t == Expr.empty))
  let xs4 := dedupSortedByKey (sortByKey xs3)
  let xs5 := absorb xs4
  match xs5 with
  | [] => Expr.empty
  | [t] => t
  | _ => Expr.plus xs5

/-- Canonicalize a sum given already-normalized terms. -/
def canonPlus (terms : List Expr) : Expr :=
  let xs2 := flattenPlus terms
  let xs3 := xs2.filter (fun t => !(t == Expr.empty))
  let xs4 := dedupSortedByKey (sortByKey xs3)
  let xs5 := absorb xs4
  match factorEntangleIfPossible xs5 with
  | some (a, rights) =>
      -- IMPORTANT: RHS is canonicalized, so this entangle result is already WF.
      Expr.entangle a (canonPlusNoFactor rights)
  | none =>
      match xs5 with
      | [] => Expr.empty
      | [t] => t
      | _ => Expr.plus xs5

/-- Canonicalize a product (no distribution). -/
def canonTimesNoDistrib (factors : List Expr) : Expr :=
  let xs2 := flattenTimes factors
  if xs2.any (fun t => t == Expr.empty) then
    Expr.empty
  else
    let xs3 := dedupSortedByKey (sortByKey xs2)
    match xs3 with
    | [] => Expr.empty
    | [t] => t
    | _ => Expr.times xs3

/-- Dependency-free `bind` for lists (Std-free). -/
def bindList {α β : Type} : List α → (α → List β) → List β
  | [], _ => []
  | x :: xs, f => f x ++ bindList xs f

/-- Fully distribute ⊗ over any ⊕ factors, producing a list of factor-lists. -/
def expandTimes (factors : List Expr) : List (List Expr) :=
  let rec go (acc : List (List Expr)) (rest : List Expr) : List (List Expr) :=
    match rest with
    | [] => acc
    | f :: fs =>
        match f with
        | Expr.plus ys =>
            let acc' := bindList acc (fun pref => ys.map (fun y => pref ++ [y]))
            go acc' fs
        | _ =>
            go (acc.map (fun pref => pref ++ [f])) fs
  go [[]] factors

/-- Canonicalize a product with full distribution into a canonical sum if needed. -/
def canonTimes (factors : List Expr) : Expr :=
  let xs2 := flattenTimes factors
  if xs2.any (fun t => t == Expr.empty) then
    Expr.empty
  else
    if xs2.any (fun t => match t with | Expr.plus _ => true | _ => false) then
      let prods := expandTimes xs2
      canonPlus (prods.map canonTimesNoDistrib)
    else
      canonTimesNoDistrib xs2

end PhotonAlgebra
