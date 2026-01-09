import Std

open Nat

namespace SymaticsBridge

/-- Minimal Boolean formula syntax. -/
inductive BForm where
  | top : BForm
  | bot : BForm
  | var : Nat → BForm
  | and : BForm → BForm → BForm
  | or  : BForm → BForm → BForm
deriving Repr, DecidableEq

/-- Node-count size of the syntax tree (a proxy for "canonical tree size"). -/
def rawSize : BForm → Nat
  | .top      => 1
  | .bot      => 1
  | .var _    => 1
  | .and a b  => rawSize a + rawSize b + 1
  | .or  a b  => rawSize a + rawSize b + 1

/-- DNF represented as list of conjunction-terms (each term is a list of vars).
    We only need enough structure to count blow-up; negation is irrelevant here. -/
def andDNF : List (List Nat) → List (List Nat) → List (List Nat)
  | [], _ => []
  | x :: xs, ys =>
      (ys.map (fun y => x ++ y)) ++ andDNF xs ys

def dnf : BForm → List (List Nat)
  | .top      => [[]]     -- one empty term
  | .bot      => []       -- no terms
  | .var v    => [[v]]    -- one singleton term
  | .or  a b  => dnf a ++ dnf b
  | .and a b  => andDNF (dnf a) (dnf b)

/-- Pair family: (x_{2i} ∨ x_{2i+1}) -/
def pair (i : Nat) : BForm :=
  .or (.var (2*i)) (.var (2*i + 1))

/-- Family F(n) = ∧_{i=0..n-1} (x_{2i} ∨ x_{2i+1}) with base Top. -/
def fam : Nat → BForm
  | 0     => .top
  | n+1   => .and (fam n) (pair n)

/-- Length of `andDNF` multiplies (cartesian product). -/
theorem length_andDNF (xs ys : List (List Nat)) :
    (andDNF xs ys).length = xs.length * ys.length := by
  induction xs with
  | nil =>
      simp [andDNF]
  | cons x xs ih =>
      simp [andDNF, ih, Nat.left_distrib, Nat.add_comm, Nat.add_left_comm, Nat.add_assoc]

/-- Main blow-up theorem: DNF term count doubles at each step, so it is exactly 2^n. -/
theorem dnf_len_fam (n : Nat) :
    (dnf (fam n)).length = 2^n := by
  induction n with
  | zero =>
      simp [fam, dnf]
  | succ n ih =>
      -- fam (n+1) = fam n ∧ pair n; dnf length multiplies by 2
      have hp : (dnf (pair n)).length = 2 := by
        simp [pair, dnf]
      simp [fam, dnf, length_andDNF, ih, hp, Nat.pow_succ]

/-- Canonical tree size is linear: rawSize(fam n) = 1 + 4n. -/
theorem rawSize_fam (n : Nat) :
    rawSize (fam n) = 1 + 4*n := by
  induction n with
  | zero =>
      simp [fam, rawSize]
  | succ n ih =>
      -- each step adds: And-node (+1) plus pair size (Or + 2 vars = 3)
      -- total increment per step is 4.
      have pairSize : rawSize (pair n) = 3 := by
        simp [pair, rawSize]
      -- rawSize (and (fam n) (pair n)) = rawSize(fam n) + rawSize(pair n) + 1
      simp [fam, rawSize, ih, pairSize, Nat.mul_succ, Nat.add_assoc, Nat.add_left_comm, Nat.add_comm]

/-- Bridge statement: exponential expansion vs linear canonical tree. -/
theorem bridge_dnf_blowup (n : Nat) :
    (dnf (fam n)).length = 2^n ∧ rawSize (fam n) = 1 + 4*n := by
  exact ⟨dnf_len_fam n, rawSize_fam n⟩

end SymaticsBridge
