/-
SymaticsBridge v22 — Template+Delta cost bound (mutations not depth)

Mathlib-free (core Lean only), to match your current lake/toolchain setup.

What this file gives you:
  • Template / Delta / Msg
  • apply : Template → Delta → Msg
  • Cost model:
      naiveBytes   = n * |apply T Δ|
      amortBytes   = |T| + n * |Δ|
      deltaBytes   = base + mutations * refBytes   (⇒ O(#mutations))
  • Stream theorems (clean, n+1 form to avoid the n=0 “do we send T?” corner):
      (1) amortBytes(T,Δ,n+1) ≤ naiveBytes(T,Δ,n+1)
      (2) naiveBytes(T,Δ,n+1) = amortBytes(T,Δ,n+1) + n * |T|
-/

namespace SymaticsBridge

structure Template where
  bytes : Nat

structure Delta where
  mutations : Nat
  refBytes : Nat
  baseBytes : Nat := 0

structure Msg where
  bytes : Nat

def deltaBytes (d : Delta) : Nat :=
  d.baseBytes + d.mutations * d.refBytes

/-- Semantics hook: applying a delta to a template yields a message.
    In this size model: |apply T Δ| = |T| + |Δ|. -/
def apply (t : Template) (d : Delta) : Msg :=
  { bytes := t.bytes + deltaBytes d }

/-- Naive stream cost: send full message every time. -/
def naiveBytes (t : Template) (d : Delta) (n : Nat) : Nat :=
  n * (apply t d).bytes

/-- Amortized cost: send template once, then only deltas per message. -/
def amortBytes (t : Template) (d : Delta) (n : Nat) : Nat :=
  t.bytes + n * deltaBytes d

/-
Delta is O(#mutations): deltaBytes = base + mutations * refBytes (exactly).
-/
theorem deltaBytes_linear (d : Delta) :
    deltaBytes d = d.baseBytes + d.mutations * d.refBytes := by
  rfl

theorem deltaBytes_eq_mul_of_base_zero (d : Delta) (h0 : d.baseBytes = 0) :
    deltaBytes d = d.mutations * d.refBytes := by
  simp [deltaBytes, h0]

/-
Helper lemma: for any a,n : Nat, a ≤ (n+1)*a.
Uses succ_mul: (n+1)*a = n*a + a, and le_add_left: a ≤ n*a + a.
-/
theorem le_succ_mul (a n : Nat) : a ≤ (n + 1) * a := by
  have h : a ≤ n * a + a := Nat.le_add_left a (n * a)
  -- (n+1)*a = n*a + a
  simpa [Nat.succ_mul] using h

/-
Main v22 stream theorem (operational, no n=0 ambiguity):
  amortBytes(T,Δ,n+1) ≤ naiveBytes(T,Δ,n+1)
-/
theorem amort_le_naive_succ (t : Template) (d : Delta) (n : Nat) :
    amortBytes t d (n + 1) ≤ naiveBytes t d (n + 1) := by
  -- abbreviations
  let a : Nat := t.bytes
  let b : Nat := deltaBytes d

  -- reduce to arithmetic goal
  have ht : a ≤ (n + 1) * a := le_succ_mul a n

  -- add (n+1)*b to both sides: a + (n+1)*b ≤ (n+1)*a + (n+1)*b
  have h1 : a + (n + 1) * b ≤ (n + 1) * a + (n + 1) * b :=
    Nat.add_le_add_right ht ((n + 1) * b)

  -- rewrite RHS to (n+1)*(a+b)
  have hmul : (n + 1) * a + (n + 1) * b = (n + 1) * (a + b) := by
    -- Nat.mul_add: (n+1)*(a+b) = (n+1)*a + (n+1)*b
    simpa using (Nat.mul_add (n + 1) a b).symm

  have : a + (n + 1) * b ≤ (n + 1) * (a + b) := by
    simpa [hmul] using h1

  simpa [amortBytes, naiveBytes, apply, a, b] using this

/-
Savings identity (nice for RFC text):
  naive(T,Δ,n+1) = amort(T,Δ,n+1) + n*|T|
-/
theorem naive_eq_amort_plus_n_templates (t : Template) (d : Delta) (n : Nat) :
    naiveBytes t d (n + 1) = amortBytes t d (n + 1) + n * t.bytes := by
  let a : Nat := t.bytes
  let b : Nat := deltaBytes d

  -- (n+1)*(a+b) = (n+1)*a + (n+1)*b
  have hmul : (n + 1) * (a + b) = (n + 1) * a + (n + 1) * b := by
    simpa using (Nat.mul_add (n + 1) a b)

  -- (n+1)*a = n*a + a
  have hsucc : (n + 1) * a = n * a + a := by
    simpa using (Nat.succ_mul n a)

  -- a little comm/assoc reshuffle lemma for Nat addition
  have hadd :
      (n * a + a) + (n + 1) * b = (a + (n + 1) * b) + n * a := by
    -- purely associativity/commutativity
    simp [Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]

  calc
    naiveBytes t d (n + 1)
        = (n + 1) * (a + b) := by
            simp [naiveBytes, apply, a, b]
    _   = (n + 1) * a + (n + 1) * b := by
            simpa using hmul
    _   = (n * a + a) + (n + 1) * b := by
            simp [hsucc, Nat.add_assoc]
    _   = (a + (n + 1) * b) + n * a := by
            simpa using hadd
    _   = amortBytes t d (n + 1) + n * t.bytes := by
            simp [amortBytes, a, b]

end SymaticsBridge