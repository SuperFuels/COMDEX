theorem add_comm (a b : Nat) : a + b = b + a :=
  Nat.add_comm a b

lemma zero_add (n : Nat) : 0 + n = n :=
  Nat.zero_add n