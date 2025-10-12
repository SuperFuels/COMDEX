import Init
open Nat

namespace Test

constant X : Type

theorem add_comm (a b : Nat) : a + b = b + a :=
  Nat.add_comm a b

theorem zero_add (n : Nat) : 0 + n = n :=
  Nat.zero_add n

theorem mul_self_nonneg (n : Nat) : n * n ≥ 0 :=
  Nat.zero_le _

end Test