import Tessaris.Symatics.Prelude

namespace Tessaris.Symatics.Bridge

/-!
Bridge: DNF blowup vs canonical tree size.

Monotone Boolean formulas with constructors:
  top (⊤), var, band (∧), bor (∨)

Counting model (monotone DNF term count):
  dnfTerms(top)  = 1
  dnfTerms(var)  = 1
  dnfTerms(bor)  = +
  dnfTerms(band) = *

Blowup family:
  F(n) = (x0 ∨ y0) ∧ (x1 ∨ y1) ∧ ... ∧ (x(n-1) ∨ y(n-1))
(with F(0) = ⊤).

We prove:
  dnfTerms(F(n)) = 2^n     (exponential)
  nodes(F(n))    = 1 + 4n  (linear)

This file is Mathlib-free (core Nat lemmas only).
-/

inductive BForm where
  | top  : BForm
  | var  : Nat → BForm
  | band : BForm → BForm → BForm
  | bor  : BForm → BForm → BForm
deriving Repr, DecidableEq

open BForm

/-- Syntactic node count of the expression tree. -/
def nodes : BForm → Nat
  | top       => 1
  | var _     => 1
  | band a b  => 1 + nodes a + nodes b
  | bor  a b  => 1 + nodes a + nodes b

/-- Number of DNF terms after full distributive expansion (monotone counting model). -/
def dnfTerms : BForm → Nat
  | top       => 1
  | var _     => 1
  | bor  a b  => dnfTerms a + dnfTerms b
  | band a b  => dnfTerms a * dnfTerms b

/-- One (xi ∨ yi) "choice pair". -/
def pair (i : Nat) : BForm :=
  bor (var (2*i)) (var (2*i + 1))

/-- Blowup family: F(0)=⊤, F(n+1)=F(n) ∧ pair(n). -/
def family : Nat → BForm
  | 0     => top
  | n + 1 => band (family n) (pair n)

@[simp] theorem dnfTerms_top : dnfTerms top = 1 := rfl
@[simp] theorem dnfTerms_var (k : Nat) : dnfTerms (var k) = 1 := rfl

@[simp] theorem dnfTerms_pair (i : Nat) : dnfTerms (pair i) = 2 := by
  simp [pair, dnfTerms]

@[simp] theorem nodes_top : nodes top = 1 := rfl

@[simp] theorem nodes_pair (i : Nat) : nodes (pair i) = 3 := by
  simp [pair, nodes]

/-- Exponential DNF blowup: dnfTerms(F(n)) = 2^n. -/
theorem dnfTerms_family : ∀ n : Nat, dnfTerms (family n) = 2^n := by
  intro n
  induction n with
  | zero =>
      simp [family]
  | succ n ih =>
      -- dnfTerms(F(n+1)) = dnfTerms(F(n)) * 2 = 2^n * 2 = 2^(n+1)
      simp [family, dnfTerms, ih, Nat.pow_succ]

/-- A tiny arithmetic lemma: 1 + t + 3 = t + 4. -/
theorem one_add_t_add_three (t : Nat) : 1 + t + 3 = t + 4 := by
  -- re-associate, commute, and normalize numerals
  simp [Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]

/-- One-step recurrence: nodes(F(n+1)) = nodes(F(n)) + 4. -/
theorem nodes_family_succ (n : Nat) :
    nodes (family (n + 1)) = nodes (family n) + 4 := by
  calc
    nodes (family (n + 1))
        = 1 + nodes (family n) + nodes (pair n) := by
            simp [family, nodes]
    _   = 1 + nodes (family n) + 3 := by
            simp [nodes_pair]
    _   = nodes (family n) + 4 := by
            -- 1 + t + 3 = t + 4
            simpa [Nat.add_assoc] using one_add_t_add_three (nodes (family n))

/-- Canonical tree size is linear: nodes(F(n)) = 1 + 4n. -/
theorem nodes_family : ∀ n : Nat, nodes (family n) = 1 + 4*n := by
  intro n
  induction n with
  | zero =>
      simp [family, nodes]
  | succ n ih =>
      calc
        nodes (family (n + 1))
            = nodes (family n) + 4 := by
                simpa using nodes_family_succ n
        _   = (1 + 4 * n) + 4 := by
                simp [ih]
        _   = 1 + 4 * (n + 1) := by
                -- 4*(n+1) = 4*n + 4
                simp [Nat.mul_succ, Nat.add_assoc]

/-- Combined bridge statement used by the benchmark narrative. -/
theorem bridge_blowup (n : Nat) :
    dnfTerms (family n) = 2^n ∧ nodes (family n) = 1 + 4*n := by
  exact ⟨dnfTerms_family n, nodes_family n⟩

end Tessaris.Symatics.Bridge
