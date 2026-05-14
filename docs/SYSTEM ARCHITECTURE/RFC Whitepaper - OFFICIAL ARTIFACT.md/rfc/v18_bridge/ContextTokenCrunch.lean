import Tessaris.Symatics.Prelude

namespace Tessaris.Symatics.Bridge

/-
v18: Context/token crunch (mathlib-free).

Model (sizes only):
  - naiveBytes: resend full (template + delta) for every message
  - glyphBytes: send template once, then only deltas per message

We state results for (k+1) messages to avoid the k=0 corner that forces t.sz = 0.
-/

structure Template where
  sz : Nat
deriving Repr, DecidableEq

structure Delta where
  sz : Nat
deriving Repr, DecidableEq

def naiveBytes (t : Template) (d : Delta) (k : Nat) : Nat :=
  k * (t.sz + d.sz)

def glyphBytes (t : Template) (d : Delta) (k : Nat) : Nat :=
  t.sz + k * d.sz

/-- Distribute naiveBytes for (k+1) messages. -/
theorem naiveBytes_succ (t : Template) (d : Delta) (k : Nat) :
    naiveBytes t d (k + 1) = (k + 1) * t.sz + (k + 1) * d.sz := by
  -- (k+1) * (t+d) = (k+1)*t + (k+1)*d
  simp [naiveBytes, Nat.mul_add, Nat.add_assoc]

/--
Exact relation:
  naive(k+1) = glyph(k+1) + k * template
(the extra cost is resending the template k additional times).
-/
theorem naive_eq_glyph_plus_template (t : Template) (d : Delta) (k : Nat) :
    naiveBytes t d (k + 1) = glyphBytes t d (k + 1) + k * t.sz := by
  calc
    naiveBytes t d (k + 1)
        = (k + 1) * t.sz + (k + 1) * d.sz := by
            simpa using naiveBytes_succ t d k
    _   = (k * t.sz + t.sz) + (k + 1) * d.sz := by
            -- (k+1)*t = k*t + t
            simp [Nat.succ_mul, Nat.add_assoc]
    _   = t.sz + ((k + 1) * d.sz + k * t.sz) := by
            simp [Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]
    _   = (t.sz + (k + 1) * d.sz) + k * t.sz := by
            simp [Nat.add_assoc]
    _   = glyphBytes t d (k + 1) + k * t.sz := by
            rfl

/-- Corollary: glyphBytes is never larger than naiveBytes (for k+1 messages). -/
theorem glyph_le_naive (t : Template) (d : Delta) (k : Nat) :
    glyphBytes t d (k + 1) ≤ naiveBytes t d (k + 1) := by
  -- Provide the witness explicitly: naive = glyph + (k * t.sz)
  refine Nat.le.intro (k := k * t.sz) ?_
  simpa [Nat.add_assoc] using (naive_eq_glyph_plus_template t d k).symm

end Tessaris.Symatics.Bridge
