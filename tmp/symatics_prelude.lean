/-
Symatics Prelude
----------------
This file extends Lean with glyph-based operators used in Symatics algebra.
By importing this, all Symatics theorems can be written directly in glyph form.
-/

open classical   -- allow excluded middle, choice, etc.
universe u
variables {A B C D : Prop}

-- Core logical connectives (already built-in, but we re-alias for clarity)
infixr ` ∧ `:35 := and        -- logical AND
infixr ` ∨ `:30 := or         -- logical OR
infixr ` ↔ `:25 := iff        -- logical equivalence
infixr ` → `:20 := implies    -- logical implication (Lean already uses →)

-- Exclusive OR (xor)
def xor (p q : Prop) : Prop := (p ∨ q) ∧ ¬(p ∧ q)
infixr ` ⊕ `:28 := xor

-- NAND / NOR as glyphs
def nand (p q : Prop) : Prop := ¬(p ∧ q)
def nor  (p q : Prop) : Prop := ¬(p ∨ q)
infixr ` ↑ `:27 := nand
infixr ` ↓ `:27 := nor

-- Alternative notations (aliases for readability)
notation p ` ⇒ ` q := p → q
notation p ` ≡ ` q := p ↔ q

-- Example axiom to test system
axiom symatics_transitivity : (A ↔ B) ∧ (B ↔ C) → (A ↔ C)

-- 🔹 Some basic theorems for validation
theorem xor_comm (p q : Prop) : p ⊕ q ↔ q ⊕ p :=
begin unfold xor, tauto end

theorem nand_comm (p q : Prop) : p ↑ q ↔ q ↑ p :=
begin unfold nand, tauto end

theorem nor_comm (p q : Prop) : p ↓ q ↔ q ↓ p :=
begin unfold nor, tauto end


/-
Symatics carriers (skeletal definitions)
----------------------------------------
These are *not* semantically complete; they just allow `⋈[φ]` and `⊥`
to parse and roundtrip in our Lean injection pipeline.
-/

-- reserve mixfix operator for symatic interference
reserve infix:55 " ⋈[" "] "

-- basic carrier types
constant Phase : Type := Real   -- phase parameter
constant SProp : Type           -- symatic propositions
constant sFalse : SProp         -- bottom / false in symatics

-- symatic interference operator (phase-modulated conjunction)
constant sInterf : Phase → SProp → SProp → SProp

-- notation for readability
notation A " ⋈[" φ "] " B => sInterf φ A B
notation "⊥" => sFalse