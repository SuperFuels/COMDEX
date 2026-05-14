import PhotonAlgebra.Normalizer
import PhotonAlgebra.NormalizerWF

namespace PhotonAlgebra
open PhotonAlgebra

/-
  Structural DecidableEq for Expr and List Expr.

  Key rule: we DO NOT use a single catch-all mismatch branch like `| _, _ => ...`,
  because Lean can still produce `refl` goals through dependent match refinement.

  Instead we enumerate constructor mismatches explicitly; every mismatch proof is
  `by intro h; cases h`, which is now safe because the constructors are already
  different.
-/
mutual

  private def decEqExpr : (a b : Expr) → Decidable (a = b)
    | Expr.atom s, Expr.atom t =>
        match decEq s t with
        | isTrue h  => isTrue (by cases h; rfl)
        | isFalse h => isFalse (by intro he; cases he; exact h rfl)
    | Expr.atom _, Expr.empty        => isFalse (by intro he; cases he)
    | Expr.atom _, Expr.plus _       => isFalse (by intro he; cases he)
    | Expr.atom _, Expr.times _      => isFalse (by intro he; cases he)
    | Expr.atom _, Expr.entangle _ _ => isFalse (by intro he; cases he)
    | Expr.atom _, Expr.neg _        => isFalse (by intro he; cases he)
    | Expr.atom _, Expr.cancel _ _   => isFalse (by intro he; cases he)
    | Expr.atom _, Expr.project _    => isFalse (by intro he; cases he)
    | Expr.atom _, Expr.collapse _   => isFalse (by intro he; cases he)

    | Expr.empty, Expr.empty         => isTrue rfl
    | Expr.empty, Expr.atom _        => isFalse (by intro he; cases he)
    | Expr.empty, Expr.plus _        => isFalse (by intro he; cases he)
    | Expr.empty, Expr.times _       => isFalse (by intro he; cases he)
    | Expr.empty, Expr.entangle _ _  => isFalse (by intro he; cases he)
    | Expr.empty, Expr.neg _         => isFalse (by intro he; cases he)
    | Expr.empty, Expr.cancel _ _    => isFalse (by intro he; cases he)
    | Expr.empty, Expr.project _     => isFalse (by intro he; cases he)
    | Expr.empty, Expr.collapse _    => isFalse (by intro he; cases he)

    | Expr.plus xs, Expr.plus ys =>
        match decEqList xs ys with
        | isTrue h  => isTrue (by cases h; rfl)
        | isFalse h => isFalse (by intro he; cases he; exact h rfl)
    | Expr.plus _, Expr.atom _       => isFalse (by intro he; cases he)
    | Expr.plus _, Expr.empty        => isFalse (by intro he; cases he)
    | Expr.plus _, Expr.times _      => isFalse (by intro he; cases he)
    | Expr.plus _, Expr.entangle _ _ => isFalse (by intro he; cases he)
    | Expr.plus _, Expr.neg _        => isFalse (by intro he; cases he)
    | Expr.plus _, Expr.cancel _ _   => isFalse (by intro he; cases he)
    | Expr.plus _, Expr.project _    => isFalse (by intro he; cases he)
    | Expr.plus _, Expr.collapse _   => isFalse (by intro he; cases he)

    | Expr.times xs, Expr.times ys =>
        match decEqList xs ys with
        | isTrue h  => isTrue (by cases h; rfl)
        | isFalse h => isFalse (by intro he; cases he; exact h rfl)
    | Expr.times _, Expr.atom _      => isFalse (by intro he; cases he)
    | Expr.times _, Expr.empty       => isFalse (by intro he; cases he)
    | Expr.times _, Expr.plus _      => isFalse (by intro he; cases he)
    | Expr.times _, Expr.entangle _ _=> isFalse (by intro he; cases he)
    | Expr.times _, Expr.neg _       => isFalse (by intro he; cases he)
    | Expr.times _, Expr.cancel _ _  => isFalse (by intro he; cases he)
    | Expr.times _, Expr.project _   => isFalse (by intro he; cases he)
    | Expr.times _, Expr.collapse _  => isFalse (by intro he; cases he)

    | Expr.entangle a1 b1, Expr.entangle a2 b2 =>
        match decEqExpr a1 a2 with
        | isTrue ha =>
            match decEqExpr b1 b2 with
            | isTrue hb  => isTrue (by cases ha; cases hb; rfl)
            | isFalse hb => isFalse (by intro he; cases he; exact hb rfl)
        | isFalse ha =>
            isFalse (by intro he; cases he; exact ha rfl)
    | Expr.entangle _ _, Expr.atom _     => isFalse (by intro he; cases he)
    | Expr.entangle _ _, Expr.empty      => isFalse (by intro he; cases he)
    | Expr.entangle _ _, Expr.plus _     => isFalse (by intro he; cases he)
    | Expr.entangle _ _, Expr.times _    => isFalse (by intro he; cases he)
    | Expr.entangle _ _, Expr.neg _      => isFalse (by intro he; cases he)
    | Expr.entangle _ _, Expr.cancel _ _ => isFalse (by intro he; cases he)
    | Expr.entangle _ _, Expr.project _  => isFalse (by intro he; cases he)
    | Expr.entangle _ _, Expr.collapse _ => isFalse (by intro he; cases he)

    | Expr.neg e1, Expr.neg e2 =>
        match decEqExpr e1 e2 with
        | isTrue h  => isTrue (by cases h; rfl)
        | isFalse h => isFalse (by intro he; cases he; exact h rfl)
    | Expr.neg _, Expr.atom _       => isFalse (by intro he; cases he)
    | Expr.neg _, Expr.empty        => isFalse (by intro he; cases he)
    | Expr.neg _, Expr.plus _       => isFalse (by intro he; cases he)
    | Expr.neg _, Expr.times _      => isFalse (by intro he; cases he)
    | Expr.neg _, Expr.entangle _ _ => isFalse (by intro he; cases he)
    | Expr.neg _, Expr.cancel _ _   => isFalse (by intro he; cases he)
    | Expr.neg _, Expr.project _    => isFalse (by intro he; cases he)
    | Expr.neg _, Expr.collapse _   => isFalse (by intro he; cases he)

    | Expr.cancel a1 b1, Expr.cancel a2 b2 =>
        match decEqExpr a1 a2 with
        | isTrue ha =>
            match decEqExpr b1 b2 with
            | isTrue hb  => isTrue (by cases ha; cases hb; rfl)
            | isFalse hb => isFalse (by intro he; cases he; exact hb rfl)
        | isFalse ha =>
            isFalse (by intro he; cases he; exact ha rfl)
    | Expr.cancel _ _, Expr.atom _       => isFalse (by intro he; cases he)
    | Expr.cancel _ _, Expr.empty        => isFalse (by intro he; cases he)
    | Expr.cancel _ _, Expr.plus _       => isFalse (by intro he; cases he)
    | Expr.cancel _ _, Expr.times _      => isFalse (by intro he; cases he)
    | Expr.cancel _ _, Expr.entangle _ _ => isFalse (by intro he; cases he)
    | Expr.cancel _ _, Expr.neg _        => isFalse (by intro he; cases he)
    | Expr.cancel _ _, Expr.project _    => isFalse (by intro he; cases he)
    | Expr.cancel _ _, Expr.collapse _   => isFalse (by intro he; cases he)

    | Expr.project e1, Expr.project e2 =>
        match decEqExpr e1 e2 with
        | isTrue h  => isTrue (by cases h; rfl)
        | isFalse h => isFalse (by intro he; cases he; exact h rfl)
    | Expr.project _, Expr.atom _       => isFalse (by intro he; cases he)
    | Expr.project _, Expr.empty        => isFalse (by intro he; cases he)
    | Expr.project _, Expr.plus _       => isFalse (by intro he; cases he)
    | Expr.project _, Expr.times _      => isFalse (by intro he; cases he)
    | Expr.project _, Expr.entangle _ _ => isFalse (by intro he; cases he)
    | Expr.project _, Expr.neg _        => isFalse (by intro he; cases he)
    | Expr.project _, Expr.cancel _ _   => isFalse (by intro he; cases he)
    | Expr.project _, Expr.collapse _   => isFalse (by intro he; cases he)

    | Expr.collapse e1, Expr.collapse e2 =>
        match decEqExpr e1 e2 with
        | isTrue h  => isTrue (by cases h; rfl)
        | isFalse h => isFalse (by intro he; cases he; exact h rfl)
    | Expr.collapse _, Expr.atom _       => isFalse (by intro he; cases he)
    | Expr.collapse _, Expr.empty        => isFalse (by intro he; cases he)
    | Expr.collapse _, Expr.plus _       => isFalse (by intro he; cases he)
    | Expr.collapse _, Expr.times _      => isFalse (by intro he; cases he)
    | Expr.collapse _, Expr.entangle _ _ => isFalse (by intro he; cases he)
    | Expr.collapse _, Expr.neg _        => isFalse (by intro he; cases he)
    | Expr.collapse _, Expr.cancel _ _   => isFalse (by intro he; cases he)
    | Expr.collapse _, Expr.project _    => isFalse (by intro he; cases he)

  private def decEqList : (xs ys : List Expr) → Decidable (xs = ys)
    | [], [] => isTrue rfl
    | [], _ :: _ => isFalse (by intro h; cases h)
    | _ :: _, [] => isFalse (by intro h; cases h)
    | x :: xs, y :: ys =>
        match decEqExpr x y with
        | isTrue hxy =>
            match decEqList xs ys with
            | isTrue hrest => isTrue (by cases hxy; cases hrest; rfl)
            | isFalse hrest => isFalse (by intro h; cases h; exact hrest rfl)
        | isFalse hxy =>
            isFalse (by intro h; cases h; exact hxy rfl)

end

instance : DecidableEq Expr := decEqExpr

/-- Bool equality derived from `DecidableEq` (no LawfulBEq needed). -/
def eqExprb (x y : Expr) : Bool :=
  match decEq x y with
  | isTrue _  => true
  | isFalse _ => false

/-- Executable check: fuel normalizer agrees with WF normalizer on this input. -/
def agrees (e : Expr) : Bool :=
  eqExprb (normalize e) (normalizeWF e)

/-- Collapse wrapper consistency for WF normalizer. -/
theorem wf_collapse (a : Expr) :
  normalizeWF (Expr.collapse a) = Expr.collapse (normalizeWF a) := by
  simp [PhotonAlgebra.normalizeWF]

/-- If the boolean check says true, we get actual equality. -/
theorem agrees_sound (e : Expr) :
  agrees e = true → normalize e = normalizeWF e := by
  intro h
  cases hdec : decEq (normalize e) (normalizeWF e) with
  | isTrue heq =>
      exact heq
  | isFalse hneq =>
      -- under hdec, eqExprb reduces to false, contradicting h
      have : False := by
        simpa [agrees, eqExprb, hdec] using h
      cases this

end PhotonAlgebra