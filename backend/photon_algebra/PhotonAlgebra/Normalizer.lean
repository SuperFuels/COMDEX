import PhotonAlgebra.Basic

namespace PhotonAlgebra

/-- A monomial is a finite set of factors (order irrelevant, idempotent). -/
abbrev Mono : Type := Finset Expr

/-- A DNF is a finite set of monomials (order irrelevant, idempotent). -/
abbrev DNF : Type := Finset Mono

private def monoSingleton (e : Expr) : Mono := ({e} : Finset Expr)
private def dnfSingleton (m : Mono) : DNF := ({m} : Finset Mono)

/-- Deterministic structural key used only for sorting during reification. -/
def exprKey : Expr -> String
  | Expr.atom s => "A:" ++ s
  | Expr.empty => "E:∅"
  | Expr.plus xs =>
      let ks := xs.map exprKey
      "P:(" ++ String.intercalate "," ks ++ ")"
  | Expr.times xs =>
      let ks := xs.map exprKey
      "T:(" ++ String.intercalate "," ks ++ ")"
  | Expr.entangle a b => "R:(" ++ exprKey a ++ "," ++ exprKey b ++ ")"
  | Expr.neg a => "N:(" ++ exprKey a ++ ")"
  | Expr.cancel a b => "D:(" ++ exprKey a ++ "," ++ exprKey b ++ ")"
  | Expr.project a => "S:(" ++ exprKey a ++ ")"
  | Expr.collapse a => "C:(" ++ exprKey a ++ ")"

private def sortByKey (xs : List Expr) : List Expr :=
  xs.qsort (fun a b => exprKey a < exprKey b)

/-- DNF union (⊕ semantics). -/
def dnfUnion (a b : DNF) : DNF := a ∪ b

/-- DNF product (⊗ semantics): set-product of monomials, unioning factors. -/
def dnfProd (a b : DNF) : DNF :=
  a.bind (fun m => b.image (fun n => m ∪ n))

/-- Subsumption check: m is subsumed iff there exists m' in D with m' ⊂ m. -/
private def isStrictSubset (m' m : Mono) : Bool := decide (m' ⊆ m ∧ m' ≠ m)

private def subsumed (d : DNF) (m : Mono) : Bool :=
  d.any (fun m' => isStrictSubset m' m)

/-- Absorption-style reduction: drop any monomial that strictly contains another. -/
def reduceSubsumption (d : DNF) : DNF :=
  d.filter (fun m => !(subsumed d m))

/-- Convert a monomial to an Expr product (⊗ list), or the single factor. -/
def monoToExpr (m : Mono) : Expr :=
  let xs := sortByKey m.toList
  match xs with
  | [] => Expr.empty
  | [x] => x
  | _ => Expr.times xs

/-- Convert a DNF to an Expr sum-of-products (⊕ list). -/
def dnfToExpr (d : DNF) : Expr :=
  let terms := (d.toList.map monoToExpr).qsort (fun a b => exprKey a < exprKey b)
  match terms with
  | [] => Expr.empty
  | [t] => t
  | _ => Expr.plus terms

/-- Normalization (directed): compute a canonical SOP-like Expr.

This is an executable checker-level normalizer intended to match the repo’s story:
- distribute ⊗ over ⊕ (DNF product)
- never factor
- absorb subsumed terms
- preserve wrappers (∇, ★) structurally

This version is dependency-free and is designed for theorem *checkers*.
-/
mutual
  /-- Compute reduced DNF for any Expr, treating non-(⊕,⊗) nodes as atomic factors,
      except for specific distributivities used by T10/T12. -/
  def dnf : Expr -> DNF
    | Expr.atom s => dnfSingleton (monoSingleton (Expr.atom s))
    | Expr.empty => (∅ : DNF)

    | Expr.plus xs =>
        let d0 : DNF := ∅
        let u := xs.foldl (fun acc x => dnfUnion acc (dnf x)) d0
        reduceSubsumption u

    | Expr.times xs =>
        match xs with
        | [] => (∅ : DNF)
        | _ =>
          let one : DNF := dnfSingleton (∅ : Mono)
          let p := xs.foldl (fun acc x => dnfProd acc (dnf x)) one
          reduceSubsumption p

    | Expr.neg (Expr.neg a) => dnf a
    | Expr.neg a => dnfSingleton (monoSingleton (Expr.neg (norm a)))

    | Expr.cancel a b =>
        if b == Expr.empty then dnf a
        else if a == Expr.empty then dnf b
        else if a == b then (∅ : DNF)
        else dnfSingleton (monoSingleton (Expr.cancel (norm a) (norm b)))

    | Expr.entangle a (Expr.plus xs) =>
        let d0 : DNF := ∅
        let u := xs.foldl (fun acc x => dnfUnion acc (dnf (Expr.entangle a x))) d0
        reduceSubsumption u

    | Expr.entangle a b =>
        dnfSingleton (monoSingleton (Expr.entangle (norm a) (norm b)))

    | Expr.project (Expr.entangle a b) =>
        reduceSubsumption (dnfUnion (dnf (Expr.project a)) (dnf (Expr.project b)))

    | Expr.project a =>
        dnfSingleton (monoSingleton (Expr.project (norm a)))

    | Expr.collapse a =>
        dnfSingleton (monoSingleton (Expr.collapse (norm a)))

  /-- Reified normal form expression. -/
  def norm : Expr -> Expr
    | Expr.atom s => Expr.atom s
    | Expr.empty => Expr.empty

    | Expr.plus xs =>
        let d0 : DNF := ∅
        let u := xs.foldl (fun acc x => dnfUnion acc (dnf x)) d0
        dnfToExpr (reduceSubsumption u)

    | Expr.times xs =>
        match xs with
        | [] => Expr.empty
        | _ =>
          let one : DNF := dnfSingleton (∅ : Mono)
          let p := xs.foldl (fun acc x => dnfProd acc (dnf x)) one
          dnfToExpr (reduceSubsumption p)

    | Expr.neg (Expr.neg a) => norm a
    | Expr.neg a => Expr.neg (norm a)

    | Expr.cancel a b =>
        if b == Expr.empty then norm a
        else if a == Expr.empty then norm b
        else if a == b then Expr.empty
        else Expr.cancel (norm a) (norm b)

    | Expr.entangle a (Expr.plus xs) =>
        let d0 : DNF := ∅
        let u := xs.foldl (fun acc x => dnfUnion acc (dnf (Expr.entangle a x))) d0
        dnfToExpr (reduceSubsumption u)

    | Expr.entangle a b => Expr.entangle (norm a) (norm b)

    | Expr.project (Expr.entangle a b) =>
        let u := dnfUnion (dnf (Expr.project a)) (dnf (Expr.project b))
        dnfToExpr (reduceSubsumption u)

    | Expr.project a => Expr.project (norm a)

    | Expr.collapse a => Expr.collapse (norm a)

end

termination_by
  dnf e => Expr.size e
  norm e => Expr.size e

/-- Convenience alias matching the repo naming. -/
def normalize (e : Expr) : Expr := norm e

end PhotonAlgebra
