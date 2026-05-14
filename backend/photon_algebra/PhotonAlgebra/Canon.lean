import PhotonAlgebra.Basic

namespace PhotonAlgebra
open PhotonAlgebra

def leStr (a b : String) : Bool :=
  match compare a b with
  | Ordering.lt => true
  | Ordering.eq => true
  | Ordering.gt => false

def insertByKey (x : Expr) : List Expr → List Expr
  | [] => [x]
  | y :: ys =>
      if leStr x.key y.key then
        x :: y :: ys
      else
        y :: insertByKey x ys

def sortByKey (xs : List Expr) : List Expr :=
  xs.foldl (fun acc x => insertByKey x acc) []

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

def flattenPlus : List Expr → List Expr
  | [] => []
  | (Expr.plus ys) :: xs => ys ++ flattenPlus xs
  | x :: xs => x :: flattenPlus xs

def flattenTimes : List Expr → List Expr
  | [] => []
  | (Expr.times ys) :: xs => ys ++ flattenTimes xs
  | x :: xs => x :: flattenTimes xs

def timesHasFactor (p f : Expr) : Bool :=
  match p with
  | Expr.times fs => fs.any (fun x => x == f)
  | _ => false

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

def canonPlusNoFactor (terms : List Expr) : Expr :=
  let xs2 := flattenPlus terms
  let xs3 := xs2.filter (fun t => !(t == Expr.empty))
  let xs4 := dedupSortedByKey (sortByKey xs3)
  let xs5 := absorb xs4
  match xs5 with
  | [] => Expr.empty
  | [t] => t
  | _ => Expr.plus xs5

def canonPlus (terms : List Expr) : Expr :=
  let xs2 := flattenPlus terms
  let xs3 := xs2.filter (fun t => !(t == Expr.empty))
  let xs4 := dedupSortedByKey (sortByKey xs3)
  let xs5 := absorb xs4
  match factorEntangleIfPossible xs5 with
  | some (a, rights) =>
      Expr.entangle a (canonPlusNoFactor rights)
  | none =>
      match xs5 with
      | [] => Expr.empty
      | [t] => t
      | _ => Expr.plus xs5

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

def bindList {α β : Type} : List α → (α → List β) → List β
  | [], _ => []
  | x :: xs, f => f x ++ bindList xs f

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