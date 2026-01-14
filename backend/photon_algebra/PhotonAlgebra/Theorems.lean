import PhotonAlgebra.NormalizerWF

namespace PhotonAlgebra
open PhotonAlgebra

def SUM  (a b : Expr) : Expr := Expr.plus [a, b]
def PROD (a b : Expr) : Expr := Expr.times [a, b]

def EqNF (x y : Expr) : Prop := normalizeWF x = normalizeWF y
def EqNFb (x y : Expr) : Bool := (normalizeWF x) == (normalizeWF y)

theorem T11 (a : Expr) :
  normalizeWF (Expr.collapse a) = Expr.collapse (normalizeWF a) := by
  simp [PhotonAlgebra.normalizeWF]

def T8_guard (a b c : Expr) : Bool :=
  EqNFb (PROD a (SUM b c)) (SUM (PROD a b) (PROD a c))

def T10_guard (a b c : Expr) : Bool :=
  EqNFb (SUM (Expr.entangle a b) (Expr.entangle a c))
        (Expr.entangle a (SUM b c))

def T13_guard (a b : Expr) : Bool :=
  EqNFb (SUM a (PROD a b)) a

def T14_guard (a b c : Expr) : Bool :=
  (normalizeWF (SUM a (PROD b c))) == (normalizeWF (PROD (SUM a b) (SUM a c)))

end PhotonAlgebra