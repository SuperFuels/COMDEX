import Mathlib

/-!
NatNorm: tiny, explicit arithmetic/normalization lemmas to avoid `simp` loops.

Policy:
- No global simp attributes.
- Use these lemmas explicitly in `calc` chains.
- Use `omega` only at the end for linear Nat goals when helpful.
-/

namespace SymaticsBridge.NatNorm

-- A small allowlist you can reference explicitly in simp/calc (but DO NOT mark simp globally).
theorem add_assoc' (a b c : Nat) : a + b + c = a + (b + c) := by
  simpa [Nat.add_assoc]

theorem add_comm' (a b : Nat) : a + b = b + a := by
  simpa [Nat.add_comm]

theorem add_left_comm' (a b c : Nat) : a + (b + c) = b + (a + c) := by
  simpa [Nat.add_left_comm, Nat.add_assoc]

theorem mul_assoc' (a b c : Nat) : a * b * c = a * (b * c) := by
  simpa [Nat.mul_assoc]

theorem mul_comm' (a b : Nat) : a * b = b * a := by
  simpa [Nat.mul_comm]

theorem left_distrib' (a b c : Nat) : a * (b + c) = a * b + a * c := by
  simpa [Nat.left_distrib]

theorem right_distrib' (a b c : Nat) : (a + b) * c = a * c + b * c := by
  simpa [Nat.right_distrib]

-- Common “factor 2” helpers, used a lot in constant-factor bounds.
theorem two_mul' (n : Nat) : 2 * n = n + n := by
  simpa [Nat.two_mul]

theorem mul_two' (n : Nat) : n * 2 = n + n := by
  simpa [Nat.mul_two]

theorem add_le_add_right' {a b : Nat} (h : a ≤ b) (c : Nat) : a + c ≤ b + c := by
  exact Nat.add_le_add_right h c

theorem add_le_add_left' {a b : Nat} (h : a ≤ b) (c : Nat) : c + a ≤ c + b := by
  exact Nat.add_le_add_left h c

theorem le_trans' {a b c : Nat} (h₁ : a ≤ b) (h₂ : b ≤ c) : a ≤ c := by
  exact Nat.le_trans h₁ h₂

end SymaticsBridge.NatNorm