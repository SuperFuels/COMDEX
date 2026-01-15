import PhotonAlgebra.NormalizerWF
import PhotonAlgebra.Canon

namespace PhotonAlgebra
open PhotonAlgebra

@[simp] axiom canonPlus_stable (xs : List Expr) :
  normalizeWF (canonPlus (xs.map normalizeWF)) = canonPlus (xs.map normalizeWF)

@[simp] axiom canonTimes_stable (xs : List Expr) :
  normalizeWF (canonTimes (xs.map normalizeWF)) = canonTimes (xs.map normalizeWF)

@[simp] axiom entangle_stable (a b : Expr) :
  normalizeWF
      (if (normalizeWF a == normalizeWF b) = true then normalizeWF a
       else (normalizeWF a).entangle (normalizeWF b)) =
    (if (normalizeWF a == normalizeWF b) = true then normalizeWF a
     else (normalizeWF a).entangle (normalizeWF b))

/-- not marked `[simp]` to avoid goal collapsing to `True` in Canonicality.lean -/
axiom neg_stable (a : Expr) :
  normalizeWF
      (match normalizeWF a with
       | Expr.neg x => x
       | x => (normalizeWF a).neg) =
    (match normalizeWF a with
     | Expr.neg x => x
     | x => (normalizeWF a).neg)

/-- not marked `[simp]` to avoid goal collapsing to `True` in Canonicality.lean -/
axiom project_stable (a : Expr) :
  normalizeWF
      (match normalizeWF a with
       | Expr.entangle x y => canonPlus [x.project, y.project]
       | x => (normalizeWF a).project) =
    (match normalizeWF a with
     | Expr.entangle x y => canonPlus [x.project, y.project]
     | x => (normalizeWF a).project)

@[simp] axiom cancel_stable (a b : Expr) :
  normalizeWF
      (if (normalizeWF a == normalizeWF b) = true then Expr.empty
       else
         if (normalizeWF b == Expr.empty) = true then normalizeWF a
         else
           if (normalizeWF a == Expr.empty) = true then normalizeWF b
           else (normalizeWF a).cancel (normalizeWF b)) =
    (if (normalizeWF a == normalizeWF b) = true then Expr.empty
     else
       if (normalizeWF b == Expr.empty) = true then normalizeWF a
       else
         if (normalizeWF a == Expr.empty) = true then normalizeWF b
         else (normalizeWF a).cancel (normalizeWF b))

end PhotonAlgebra