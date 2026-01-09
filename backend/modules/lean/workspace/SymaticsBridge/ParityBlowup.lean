import Tessaris.Symatics.Prelude

namespace Tessaris.Symatics.Bridge

/-!
Bridge v15: Parity (XOR) blowup vs canonical tree size (Mathlib-free).

Expr language:
  var, bxor

Counting model for Boolean minterm materialization:
  dnfTerms(var)      = 1
  dnfTerms(bxor a b) = 2 * dnfTerms(a) * dnfTerms(b)

Parity (XOR-chain):
  parity(0)   = x0
  parity(n+1) = parity(n) ⊕ x(n+1)

We prove:
  dnfTerms(parity n) = 2^n        (exponential)
  nodes  (parity n) = 1 + 2*n     (linear)
-/

inductive Expr where
  | var  : Nat → Expr
  | bxor : Expr → Expr → Expr
deriving Repr, DecidableEq

open Expr

/-- Syntactic node count of the expression tree. -/
def nodes : Expr → Nat
  | var _    => 1
  | bxor a b => 1 + nodes a + nodes b

/-- DNF term-count model for full XOR expansion. -/
def dnfTerms : Expr → Nat
  | var _    => 1
  | bxor a b => 2 * dnfTerms a * dnfTerms b

/-- XOR-chain parity over variables 0..n. -/
def parity : Nat → Expr
  | 0     => var 0
  | n + 1 => bxor (parity n) (var (n + 1))

@[simp] theorem nodes_var (k : Nat) : nodes (var k) = 1 := rfl
@[simp] theorem dnfTerms_var (k : Nat) : dnfTerms (var k) = 1 := rfl

/-- Tiny arithmetic lemma: 1 + (1 + t) = 2 + t. -/
theorem one_add_one_add (t : Nat) : 1 + (1 + t) = 2 + t := by
  calc
    1 + (1 + t) = (1 + 1) + t := (Nat.add_assoc 1 1 t).symm
    _ = 2 + t := rfl

/-- Tiny arithmetic lemma: (t + 1) = (1 + t). -/
theorem add_one_comm (t : Nat) : t + 1 = 1 + t := by
  exact Nat.add_comm t 1

/-- Exponential DNF blowup for parity: dnfTerms(parity n) = 2^n. -/
theorem dnfTerms_parity : ∀ n : Nat, dnfTerms (parity n) = 2^n := by
  intro n
  induction n with
  | zero =>
      simp [parity]
  | succ n ih =>
      calc
        dnfTerms (parity (n + 1))
            = 2 * dnfTerms (parity n) * dnfTerms (var (n + 1)) := by
                simp [parity, dnfTerms]
        _   = 2 * dnfTerms (parity n) * 1 := by
                simp
        _   = 2 * dnfTerms (parity n) := by
                simp [Nat.mul_one]
        _   = 2 * (2^n) := by
                simp [ih]
        _   = (2^n) * 2 := by
                simp [Nat.mul_comm]
        _   = 2^(n + 1) := by
                exact (Nat.pow_succ 2 n).symm

/-- Linear canonical tree size for parity: nodes(parity n) = 1 + 2*n. -/
theorem nodes_parity : ∀ n : Nat, nodes (parity n) = 1 + 2*n := by
  intro n
  induction n with
  | zero =>
      simp [parity]
  | succ n ih =>
      have hstep : nodes (parity (n + 1)) = 1 + nodes (parity n) + 1 := by
        simp [parity, nodes]

      have hnorm : 1 + nodes (parity n) + 1 = 2 + nodes (parity n) := by
        calc
          1 + nodes (parity n) + 1
              = 1 + (nodes (parity n) + 1) := (Nat.add_assoc 1 (nodes (parity n)) 1).symm
          _   = 1 + (1 + nodes (parity n)) := by
                  -- rewrite inner (nodes + 1) -> (1 + nodes)
                  simp [add_one_comm (nodes (parity n))]
          _   = 2 + nodes (parity n) := by
                  exact one_add_one_add (nodes (parity n))

      calc
        nodes (parity (n + 1))
            = 2 + nodes (parity n) := by
                exact Eq.trans hstep hnorm
        _   = 2 + (1 + 2*n) := by
                simp [ih]
        _   = 1 + 2*(n + 1) := by
                -- both sides reduce to 3 + 2*n
                have hL : 2 + (1 + 2*n) = 3 + 2*n := by
                  exact (Nat.add_assoc 2 1 (2*n)).symm
                have hR : 1 + 2*(n + 1) = 3 + 2*n := by
                  calc
                    1 + 2*(n + 1)
                        = 1 + (2*n + 2) := by
                            simp [Nat.mul_succ]
                    _   = 1 + (2 + 2*n) := by
                            simp [Nat.add_comm (2*n) 2]
                    _   = 1 + 2 + 2*n := by
                            -- fix associativity direction
                            exact (Nat.add_assoc 1 2 (2*n)).symm
                    _   = 3 + 2*n := rfl
                exact hL.trans hR.symm

/-- Combined bridge statement (v15). -/
theorem bridge_parity_blowup (n : Nat) :
    dnfTerms (parity n) = 2^n ∧ nodes (parity n) = 1 + 2*n := by
  exact ⟨dnfTerms_parity n, nodes_parity n⟩

end Tessaris.Symatics.Bridge