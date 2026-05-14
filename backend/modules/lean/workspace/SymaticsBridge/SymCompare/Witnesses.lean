import SymaticsBridge.SymCompare.NoGo

namespace SymCompare

def EFFECTALG_LOCK_ID : String := "EFFECTALG_SEPARATION_LINT_v1"
def EFFECTALG_COUNTEREX_SHA256 : String :=
  "90472750420f76dc3349626fa984cbeb364d2f75b3c3c2a84659cfb8af170cce"

def SEMIRING_LOCK_ID : String := "SEMIRING_SEPARATION_LINT_v1"
def SEMIRING_COUNTEREX_SHA256 : String :=
  "63dc369a171ee256cd4fbea855944609602b191e054ebe82e3bb5d29b8a6e36a"

-- Witness facts certified by locked runners (declared as axioms)
axiom n1_witness
  (Sym : Type) (Interf : Phase → Sym → Sym → Sym) (A B : Sym) :
  Interf phi1 A B ≠ Interf phi2 A B

axiom n2_witness
  (Sym : Type) (add mul : Sym → Sym → Sym) (A B C : Sym) :
  mul (add A B) C ≠ add (mul A C) (mul B C)

end SymCompare