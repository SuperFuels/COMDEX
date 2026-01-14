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

/-- If *all* terms are `entangle a _` with the same `a`, factor into `a ↔ (⊕ ...)`. -/
def factorEntangleIfPossible (terms : List Expr) : Option Expr :=
  match terms with
  | [] => none
  | (Expr.entangle a b) :: rest =>
      if rest.all (fun t =>
        match t with
        | Expr.entangle a' _ => a' == a
        | _ => false
      ) then
        let rights :=
          (b :: (rest.map (fun t => match t with | Expr.entangle _ r => r | _ => Expr.empty)))
        some (Expr.entangle a (Expr.plus rights))
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
        -- keep product only if it is NOT subsumed by any base factor
        !(bases.any (fun b => timesHasFactor t b))
    | _ => true
  )

/-- Pick the first factor that is a ⊕, returning (prefix, sumStates, suffix). -/
def pickFirstPlusFactor : List Expr → Option (List Expr × List Expr × List Expr)
  | [] => none
  | x :: xs =>
      match x with
      | Expr.plus ys => some ([], ys, xs)
      | _ =>
          match pickFirstPlusFactor xs with
          | none => none
          | some (pre, ys, suf) => some (x :: pre, ys, suf)

/-- One normalization step (may perform one distribution at the top `times` it sees). -/
def normStep : Expr → Expr
  | Expr.atom s => Expr.atom s
  | Expr.empty  => Expr.empty

  | Expr.neg e =>
      let ne := normStep e
      match ne with
      | Expr.neg x => x
      | _ => Expr.neg ne

  | Expr.cancel a b =>
      let na := normStep a
      let nb := normStep b
      if na == nb then
        Expr.empty
      else if nb == Expr.empty then
        na
      else if na == Expr.empty then
        nb
      else
        Expr.cancel na nb

  | Expr.project e =>
      let ne := normStep e
      match ne with
      | Expr.entangle a b =>
          -- ★(a↔b)  →  (★a) ⊕ (★b)
          Expr.plus [Expr.project a, Expr.project b]
      | _ =>
          Expr.project ne

  | Expr.collapse e =>
      Expr.collapse (normStep e)

  | Expr.entangle a b =>
      Expr.entangle (normStep a) (normStep b)

  | Expr.plus xs =>
      let xs1 := xs.map normStep
      let xs2 := flattenPlus xs1
      let xs3 := xs2.filter (fun t => !(t == Expr.empty))
      let xs4 := dedupSortedByKey (sortByKey xs3)
      let xs5 := absorb xs4
      match factorEntangleIfPossible xs5 with
      | some e => e
      | none =>
          match xs5 with
          | [] => Expr.empty
          | [t] => t
          | _ => Expr.plus xs5

  | Expr.times xs =>
      let xs1 := xs.map normStep
      let xs2 := flattenTimes xs1
      if xs2.any (fun t => t == Expr.empty) then
        Expr.empty
      else
        -- distribute once if any factor is ⊕
        match pickFirstPlusFactor xs2 with
        | some (pre, ys, suf) =>
            let terms := ys.map (fun y => Expr.times (pre.reverse ++ [y] ++ suf))
            Expr.plus terms
        | none =>
            let xs3 := dedupSortedByKey (sortByKey xs2)
            match xs3 with
            | [] => Expr.empty
            | [t] => t
            | _ => Expr.times xs3

/-- Fuel-bounded normalization to a fixpoint. -/
def normalizeFuel : Nat → Expr → Expr
  | 0, e => e
  | Nat.succ k, e =>
      let e' := normStep e
      if e' == e then
        e
      else
        normalizeFuel k e'

/-- Public normalizer (PA-core). -/
def normalize (e : Expr) : Expr :=
  -- generous fuel: quadratic in size to allow distribution growth but still terminate
  normalizeFuel (e.size * e.size + 50) e

end PhotonAlgebra