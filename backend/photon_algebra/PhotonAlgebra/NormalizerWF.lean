import PhotonAlgebra.Canon

namespace PhotonAlgebra
open PhotonAlgebra

/--
`normalizeWF` is the reference *core* normalizer (PA-core).

Phase-1 aligned (Python-sense):
- T9   : ¬(¬a) = a
- T11  : a ↔ a = a
- T12  : ★(a↔b) = (★a) ⊕ (★b)
- T15  : a ⊖ a = ∅ ; a ⊖ ∅ = a ; ∅ ⊖ a = a
- ∇    : wrapper-only (normalize inside)

Canonicalization is delegated to `canonPlus` / `canonTimes`:
- flatten, drop ∅ identity, dedup/idempotence, sort-by-key, absorption, and any
  entangle factoring behavior you’ve implemented in Canon.
-/
def normalizeWF : Expr → Expr
  | Expr.atom s => Expr.atom s
  | Expr.empty  => Expr.empty

  -- T9: ¬(¬a) = a
  | Expr.neg e =>
      let ne := normalizeWF e
      match ne with
      | Expr.neg x => x
      | _ => Expr.neg ne

  -- T15 + cancellation core:
  --   a ⊖ a = ∅
  --   a ⊖ ∅ = a
  --   ∅ ⊖ a = a
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

  -- T12: ★(a↔b) = (★a) ⊕ (★b)
  | Expr.project e =>
      let ne := normalizeWF e
      match ne with
      | Expr.entangle a b =>
          -- `a` and `b` are already normalized (because `ne` came from normalizeWF e).
          -- Keep the resulting sum in canonical form via canonPlus.
          canonPlus [Expr.project a, Expr.project b]
      | _ =>
          Expr.project ne

  -- Collapse (∇) is a wrapper in PA-core: normalize inside only.
  | Expr.collapse e =>
      Expr.collapse (normalizeWF e)

  -- T11 (Python): ↔ idempotence: a ↔ a = a
  | Expr.entangle a b =>
      let na := normalizeWF a
      let nb := normalizeWF b
      if na == nb then
        na
      else
        Expr.entangle na nb

  -- Canonical ⊕ / ⊗
  | Expr.plus xs =>
      canonPlus (xs.map normalizeWF)
  | Expr.times xs =>
      canonTimes (xs.map normalizeWF)

end PhotonAlgebra