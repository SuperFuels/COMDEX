import PhotonAlgebra.Normalizer

namespace PhotonAlgebra

open PhotonAlgebra

/-- Local list bind (no Std/List.bind dependency). -/
def bindList {α β : Type} (xs : List α) (f : α → List β) : List β :=
  match xs with
  | []      => []
  | x :: xs => f x ++ bindList xs f

/-- Canonicalize a ⊕ list (reuses Normalizer.lean helpers). -/
def canonPlus (terms : List Expr) : Expr :=
  let xs2 := flattenPlus terms
  let xs3 := xs2.filter (fun t => !(t == Expr.empty))
  let xs4 := dedupSortedByKey (sortByKey xs3)
  let xs5 := absorb xs4
  match factorEntangleIfPossible xs5 with
  | some e => e
  | none   =>
    match xs5 with
    | []    => Expr.empty
    | [t]   => t
    | _     => Expr.plus xs5

/-- Canonicalize a ⊗ list *without* doing any distribution. -/
def canonTimesNoDistrib (factors : List Expr) : Expr :=
  let xs2 := flattenTimes factors
  if xs2.any (fun t => t == Expr.empty) then
    Expr.empty
  else
    let xs3 := dedupSortedByKey (sortByKey xs2)
    match xs3 with
    | []   => Expr.empty
    | [t]  => t
    | _    => Expr.times xs3

/-- Expand a product over any plus-factors (full distribution). -/
def expandTimes (factors : List Expr) : List (List Expr) :=
  let rec go (acc : List (List Expr)) (rest : List Expr) : List (List Expr) :=
    match rest with
    | [] => acc
    | f :: rs =>
      match f with
      | Expr.plus ys =>
          let acc' := bindList acc (fun pre => ys.map (fun y => pre ++ [y]))
          go acc' rs
      | _ =>
          go (acc.map (fun pre => pre ++ [f])) rs
  go [[]] factors

/-- Canonicalize a ⊗ list with full distribution over ⊕ factors. -/
def canonTimes (factors : List Expr) : Expr :=
  let xs2 := flattenTimes factors
  if xs2.any (fun t => t == Expr.empty) then
    Expr.empty
  else
    let expanded : List (List Expr) := expandTimes xs2
    let terms    : List Expr        := expanded.map canonTimesNoDistrib
    canonPlus terms

/-
  Total, terminating Phase-1 reference normalizer (no fuel).

  IMPORTANT: keep recursion structurally obvious.
  In particular, handle ★(a↔b) with a *nested pattern* so Lean sees subterm recursion.
-/
def normalizeWF : Expr → Expr
  | Expr.atom s => Expr.atom s
  | Expr.empty  => Expr.empty

  | Expr.neg e =>
      let ne := normalizeWF e
      match ne with
      | Expr.neg x => x
      | _          => Expr.neg ne

  | Expr.cancel a b =>
      let na := normalizeWF a
      let nb := normalizeWF b
      if na == nb then
        Expr.empty
      else if nb == Expr.empty then
        na
      else if na == Expr.empty then
        nb
      else
        Expr.cancel na nb

  | Expr.collapse e =>
      Expr.collapse (normalizeWF e)

  | Expr.entangle a b =>
      Expr.entangle (normalizeWF a) (normalizeWF b)

  | Expr.project (Expr.entangle a b) =>
      canonPlus [Expr.project (normalizeWF a), Expr.project (normalizeWF b)]

  | Expr.project e =>
      Expr.project (normalizeWF e)

  | Expr.plus xs =>
      canonPlus (xs.map normalizeWF)

  | Expr.times xs =>
      canonTimes (xs.map normalizeWF)

end PhotonAlgebra