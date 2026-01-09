/-
v19: Context/token amortization (template+delta vs naive), Lean side.

This workspace has NO Mathlib, so stay in core Lean (Init/Std).
We phrase the key equalities over (k+1) messages to avoid the k=0 subtraction trap.

Naive bytes:    (k+1) * (T + Δ)
Glyph bytes:    T + (k+1) * Δ
Gap:            k * T
-/

namespace SymaticsBridge

structure Template where
  sz : Nat

structure Delta where
  sz : Nat

def naiveBytes (t : Template) (d : Delta) (k : Nat) : Nat :=
  k * (t.sz + d.sz)

def glyphBytes (t : Template) (d : Delta) (k : Nat) : Nat :=
  t.sz + k * d.sz

/-- Expand naive bytes: k*(T+Δ) = k*T + k*Δ. -/
theorem naiveBytes_expand (t : Template) (d : Delta) (k : Nat) :
    naiveBytes t d k = k * t.sz + k * d.sz := by
  simp [naiveBytes, Nat.mul_add]

/--
Key amortization identity (no subtraction):
(k+1)*(T+Δ) = (T + (k+1)*Δ) + k*T
i.e. naive = glyph + gap.
-/
theorem naive_eq_glyph_plus_gap_succ (t : Template) (d : Delta) (k : Nat) :
    naiveBytes t d (k + 1) = glyphBytes t d (k + 1) + k * t.sz := by
  -- Expand both sides to arithmetic on Nat, then normalize.
  -- (k+1)*(T+Δ) = (k+1)*T + (k+1)*Δ
  -- (k+1)*T = k*T + T  (Nat.succ_mul / Nat.mul_succ variants)
  simp [naiveBytes, glyphBytes, Nat.mul_add, Nat.succ_mul, Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]

/-- Therefore glyph ≤ naive for (k+1) messages (gap = k*T ≥ 0). -/
theorem glyph_le_naive_succ (t : Template) (d : Delta) (k : Nat) :
    glyphBytes t d (k + 1) ≤ naiveBytes t d (k + 1) := by
  -- Start from the identity: naive = glyph + gap
  have h := naive_eq_glyph_plus_gap_succ t d k
  -- h : naiveBytes ... = glyphBytes ... + (k * t.sz)
  -- Rewrite the goal's RHS using h, then finish by monotonicity of +.
  -- After rewrite, goal becomes: glyph ≤ glyph + gap
  simpa [h] using (Nat.le_add_right (glyphBytes t d (k + 1)) (k * t.sz))

theorem glyphBytes_zero (t : Template) (d : Delta) :
    glyphBytes t d 0 = t.sz := by
  simp [glyphBytes]

theorem naiveBytes_zero (t : Template) (d : Delta) :
    naiveBytes t d 0 = 0 := by
  simp [naiveBytes]

end SymaticsBridge