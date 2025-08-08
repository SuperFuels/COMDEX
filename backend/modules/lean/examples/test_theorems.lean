-- Basic mathematical theorems

theorem add_zero (n : ℕ) : n + 0 = n :=
nat.add_zero n

theorem zero_add (n : ℕ) : 0 + n = n :=
nat.zero_add n

lemma mul_one (n : ℕ) : n * 1 = n :=
nat.mul_one n

def square (n : ℕ) : ℕ := n * n

example (n : ℕ) : square n ≥ n :=
nat.le_mul_self n n