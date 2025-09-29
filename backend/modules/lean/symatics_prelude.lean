/-
Symatics Prelude (v0.9)
-----------------------
Glyph-based operators for Symatics algebra, aligned with Codex + Python rewriter.

Provides:
  • SProp : carrier type for symatic propositions
  • Phase : type of phase offsets
  • ⊥     : bottom / annihilation
  • ⋈[φ]  : interference operator
  • ⊕     : constructive interference (phase = 0)
  • ⊖     : destructive interference (phase = π)
-/

open classical
universe u

-- Core carriers
constant Phase : Type           -- abstract type of phase offsets
constant SProp : Type           -- symatic propositions
constant sFalse : SProp         -- bottom / annihilation

-- Interference connective
constant sInterf : Phase → SProp → SProp → SProp

-- Notations
notation "⊥" => sFalse
notation A " ⋈[" φ "] " B => sInterf φ A B

-- Derived notations for common phases
constant zero_phase : Phase
constant pi_phase   : Phase

notation A " ⊕ " B := sInterf zero_phase A B
notation A " ⊖ " B := sInterf pi_phase A B