namespace SymaticsBridge

structure Dict where
  bytes : Nat

structure Ref where
  bytes : Nat

def naiveBytes (d : Dict) (n : Nat) : Nat :=
  n * d.bytes

def dictBytes (d : Dict) (r : Ref) (n : Nat) : Nat :=
  d.bytes + n * r.bytes

/-- core lemma in the direction Lean already has: (n+1)*a = n*a + a -/
theorem succ_mul (n a : Nat) : (n + 1) * a = n * a + a := by
  simpa [Nat.succ_eq_add_one] using (Nat.succ_mul n a)

/--
If reference tokens are no larger than the repeated header-block,
then sending dict once + n refs is never larger than resending the block (n+1) times.
-/
theorem dict_le_naive_succ (d : Dict) (r : Ref) (n : Nat) (h : r.bytes ≤ d.bytes) :
    dictBytes d r n ≤ naiveBytes d (n + 1) := by
  have hn : n * r.bytes ≤ n * d.bytes := Nat.mul_le_mul_left n h
  have h' : d.bytes + n * r.bytes ≤ d.bytes + n * d.bytes :=
    Nat.add_le_add_left hn d.bytes

  -- Goal RHS is (n+1)*d.bytes; rewrite as n*d.bytes + d.bytes (Lean's direction)
  -- Then use commutativity to match h'’s RHS shape d.bytes + n*d.bytes.
  simpa [dictBytes, naiveBytes, succ_mul, Nat.add_comm, Nat.add_left_comm, Nat.add_assoc] using h'

theorem naive_ge_n_mul_bytes (d : Dict) (n : Nat) :
    n * d.bytes ≤ naiveBytes d n := by
  simp [naiveBytes]

theorem dict_le_dict_plus_linear (d : Dict) (r : Ref) (n : Nat) :
    dictBytes d r n ≤ d.bytes + n * r.bytes := by
  simp [dictBytes]

end SymaticsBridge