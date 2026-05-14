/-!
  A tiny Mathlib slice for **GlyphChain / Tessaris AI** → glyph/DC export.

  Covers: `def`, `lemma`, `theorem`, `example` with → and ↔ in types.
-/

import Mathlib

/-- simple definition (Nat → Nat) -/
def double (n : Nat) : Nat := n + n

/-- commutativity of addition (Nat) -/
lemma add_comm_nat (a b : Nat) : a + b = b + a := by
  simpa using Nat.add_comm a b

/-- associativity of addition (Nat) -/
theorem add_assoc_nat (a b c : Nat) : a + b + c = a + (b + c) := by
  simpa using Nat.add_assoc a b c

/-- commutativity of multiplication (Nat) -/
lemma mul_comm_nat (a b : Nat) : a * b = b * a := by
  simpa using Nat.mul_comm a b

/-- a simple propositional implication transitivity -/
theorem imp_trans (p q r : Prop) :
    (p → q) → (q → r) → (p → r) := by
  intro h1 h2 hp
  exact h2 (h1 hp)

/-- symmetry of ↔ -/
theorem iff_symm' (p q : Prop) :
    (p ↔ q) → (q ↔ p) := by
  intro h
  exact Iff.symm h

/-- an example using ∧ swapping -/
example and_swap (p q : Prop) :
    p ∧ q → q ∧ p := by
  intro h
  exact And.intro h.right h.left

/-- a placeholder “statement” we can use for PDE/heat eq demos -/
def HeatEqStatement : Prop := True

/-- trivial “proof” of the placeholder statement -/
theorem heat_eq_linear : HeatEqStatement := by
  trivial

/-- `double` distributes over addition -/
theorem double_add (x y : Nat) :
    double (x + y) = double x + double y := by
  unfold double
  -- (x + y) + (x + y) = (x + x) + (y + y)
  simpa using (Nat.add_add_add_comm x y x y)