import PhotonAlgebra.NormalizerWF

namespace PhotonAlgebra
open PhotonAlgebra

def SUM  (a b : Expr) : Expr := Expr.plus [a, b]
def PROD (a b : Expr) : Expr := Expr.times [a, b]

def EqNF (x y : Expr) : Prop := normalizeWF x = normalizeWF y
def EqNFb (x y : Expr) : Bool := (normalizeWF x) == (normalizeWF y)

/-- Collapse wrapper safety (this was mislabeled as T11). -/
theorem CollapseWF (a : Expr) :
  normalizeWF (Expr.collapse a) = Expr.collapse (normalizeWF a) := by
  simp [PhotonAlgebra.normalizeWF]

/- Boolean checks (NOT theorems). Keep distinct names to avoid snapshot confusion. -/
def T8_check (a b c : Expr) : Bool :=
  EqNFb (PROD a (SUM b c)) (SUM (PROD a b) (PROD a c))

def T10_check (a b c : Expr) : Bool :=
  EqNFb (SUM (Expr.entangle a b) (Expr.entangle a c))
        (Expr.entangle a (SUM b c))

def T13_check (a b : Expr) : Bool :=
  EqNFb (SUM a (PROD a b)) a

def T14_check (a b c : Expr) : Bool :=
  (normalizeWF (SUM a (PROD b c))) == (normalizeWF (PROD (SUM a b) (SUM a c)))

end PhotonAlgebra