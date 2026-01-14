import Lean.Data.Json
import PhotonAlgebra.Basic

namespace PhotonAlgebra
open Lean

def Expr.toJson : Expr → Json
  | Expr.atom s => Json.str s
  | Expr.empty  => Json.obj [("op", Json.str "∅")]
  | Expr.plus xs =>
      Json.obj [("op", Json.str "⊕"), ("states", Json.arr (xs.map Expr.toJson))]
  | Expr.times xs =>
      Json.obj [("op", Json.str "⊗"), ("states", Json.arr (xs.map Expr.toJson))]
  | Expr.entangle a b =>
      Json.obj [("op", Json.str "↔"), ("states", Json.arr [a.toJson, b.toJson])]
  | Expr.neg e =>
      Json.obj [("op", Json.str "¬"), ("state", e.toJson)]
  | Expr.cancel a b =>
      Json.obj [("op", Json.str "⊖"), ("states", Json.arr [a.toJson, b.toJson])]
  | Expr.project e =>
      Json.obj [("op", Json.str "★"), ("state", e.toJson)]
  | Expr.collapse e =>
      Json.obj [("op", Json.str "∇"), ("state", e.toJson)]

private def getStr (o : RBMap String Json compare) (k : String) : Except String String := do
  match o.find? k with
  | some (Json.str s) => pure s
  | some _ => throw s!"field '{k}' must be string"
  | none => throw s!"missing field '{k}'"

private def getArr (o : RBMap String Json compare) (k : String) : Except String (Array Json) := do
  match o.find? k with
  | some (Json.arr a) => pure a
  | some _ => throw s!"field '{k}' must be array"
  | none => throw s!"missing field '{k}'"

private def getObj (j : Json) : Except String (RBMap String Json compare) := do
  match j with
  | Json.obj kvs =>
      pure <| (kvs.foldl (fun m (p : String × Json) => m.insert p.1 p.2) (RBMap.empty))
  | _ => throw "expected JSON object"

partial def Expr.ofJson : Json → Except String Expr
  | Json.str s => pure (Expr.atom s)
  | j@(Json.obj _) => do
      let o ← getObj j
      let op ← getStr o "op"
      match op with
      | "∅" => pure Expr.empty
      | "⊕" =>
          let a ← getArr o "states"
          pure (Expr.plus (a.toList.map (fun x => (Expr.ofJson x).toOption.getD Expr.empty)))
      | "⊗" =>
          let a ← getArr o "states"
          pure (Expr.times (a.toList.map (fun x => (Expr.ofJson x).toOption.getD Expr.empty)))
      | "↔" =>
          let a ← getArr o "states"
          if a.size != 2 then throw "↔ expects 2 states"
          let e0 := (Expr.ofJson a[0]!).toOption.getD Expr.empty
          let e1 := (Expr.ofJson a[1]!).toOption.getD Expr.empty
          pure (Expr.entangle e0 e1)
      | "⊖" =>
          let a ← getArr o "states"
          if a.size != 2 then throw "⊖ expects 2 states"
          let e0 := (Expr.ofJson a[0]!).toOption.getD Expr.empty
          let e1 := (Expr.ofJson a[1]!).toOption.getD Expr.empty
          pure (Expr.cancel e0 e1)
      | "¬" =>
          match o.find? "state" with
          | some st => pure (Expr.neg ((Expr.ofJson st).toOption.getD Expr.empty))
          | none => throw "¬ expects state"
      | "★" =>
          match o.find? "state" with
          | some st => pure (Expr.project ((Expr.ofJson st).toOption.getD Expr.empty))
          | none => throw "★ expects state"
      | "∇" =>
          match o.find? "state" with
          | some st => pure (Expr.collapse ((Expr.ofJson st).toOption.getD Expr.empty))
          | none => throw "∇ expects state"
      | _ => throw s!"unknown op '{op}'"
  | _ => throw "expected JSON string or object"

end PhotonAlgebra