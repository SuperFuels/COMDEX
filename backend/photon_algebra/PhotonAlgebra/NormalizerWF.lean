import PhotonAlgebra.Canon

namespace PhotonAlgebra
open PhotonAlgebra

def normalizeWF : Expr → Expr
  | Expr.atom s => Expr.atom s
  | Expr.empty  => Expr.empty
  | Expr.neg e =>
      let ne := normalizeWF e
      match ne with
      | Expr.neg x => x
      | _ => Expr.neg ne
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
  | Expr.project e =>
      let ne := normalizeWF e
      match ne with
      | Expr.entangle a b =>
          canonPlus [Expr.project a, Expr.project b]
      | _ =>
          Expr.project ne
  | Expr.collapse e =>
      Expr.collapse (normalizeWF e)
  | Expr.entangle a b =>
      Expr.entangle (normalizeWF a) (normalizeWF b)
  | Expr.plus xs =>
      canonPlus (xs.map normalizeWF)
  | Expr.times xs =>
      canonTimes (xs.map normalizeWF)

end PhotonAlgebra
