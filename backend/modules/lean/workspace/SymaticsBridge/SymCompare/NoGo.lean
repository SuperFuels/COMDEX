import Std

namespace SymCompare

abbrev Phase := String
def phi1 : Phase := "pi/3"
def phi2 : Phase := "pi/2"

section N1

theorem image_phi_invariant
    (Sym Eff : Type)
    (Interf : Phase → Sym → Sym → Sym)
    (h : Sym → Eff)
    (combine : Eff → Eff → Eff)
    (rep : ∀ (φ : Phase) (A B : Sym),
      h (Interf φ A B) = combine (h A) (h B))
    (φ₁ φ₂ : Phase) (A B : Sym) :
    h (Interf φ₁ A B) = h (Interf φ₂ A B) := by
  calc
    h (Interf φ₁ A B) = combine (h A) (h B) := rep φ₁ A B
    _                 = h (Interf φ₂ A B) := (rep φ₂ A B).symm

theorem N1_no_effectalg_representation
    (Sym Eff : Type)
    (Interf : Phase → Sym → Sym → Sym)
    (h : Sym → Eff)
    (combine : Eff → Eff → Eff)
    (rep : ∀ (φ : Phase) (A B : Sym),
      h (Interf φ A B) = combine (h A) (h B))
    (A B : Sym)
    (witness : Interf phi1 A B ≠ Interf phi2 A B)
    (hinj : Function.Injective h) :
    False := by
  have himg :
      h (Interf phi1 A B) = h (Interf phi2 A B) :=
    image_phi_invariant Sym Eff Interf h combine rep phi1 phi2 A B
  have : Interf phi1 A B = Interf phi2 A B := hinj himg
  exact witness this

end N1


section N2

theorem N2_no_semiring_extension
    (Sym : Type)
    (add mul : Sym → Sym → Sym)
    (distrib : ∀ (A B C : Sym),
      mul (add A B) C = add (mul A C) (mul B C))
    (A B C : Sym)
    (witness : mul (add A B) C ≠ add (mul A C) (mul B C)) :
    False := by
  have forced : mul (add A B) C = add (mul A C) (mul B C) := distrib A B C
  exact witness forced

end N2

end SymCompare
