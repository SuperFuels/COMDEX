namespace SymaticsBridge

/-
v20: “Semantic CDN / transatlantic” is v10/v18/v19 amortization framed as HTTP+JSON request shapes.

Abstract byte model:
  T = template bytes (headers + schema/tool/system scaffolding)
  Δ = delta bytes (per-request signal)
  k = number of requests
-/

structure Template where
  sz : Nat

structure Delta where
  sz : Nat

def naiveBytes (t : Template) (d : Delta) (k : Nat) : Nat :=
  k * (t.sz + d.sz)

def glyphBytes (t : Template) (d : Delta) (k : Nat) : Nat :=
  t.sz + k * d.sz

/-- For (k+1) requests: naive cost equals glyph cost plus k extra copies of the template. -/
theorem naive_eq_glyph_plus_k_templates (t : Template) (d : Delta) (k : Nat) :
    naiveBytes t d (k + 1) = glyphBytes t d (k + 1) + k * t.sz := by
  -- Expand `naiveBytes` and distribute multiplication over addition.
  simp [naiveBytes, glyphBytes, Nat.mul_add]
  -- Goal now looks like:
  -- (k+1)*t.sz + (k+1)*d.sz = (t.sz + (k+1)*d.sz) + k*t.sz
  -- Rewrite (k+1)*t.sz as t.sz + k*t.sz
  have ht : (k + 1) * t.sz = t.sz + k * t.sz := by
    -- (Nat.succ k) * n = n + k*n
    simpa [Nat.succ_mul, Nat.add_comm, Nat.add_left_comm, Nat.add_assoc]
  -- Use ht, then reassociate and swap the inner sum once.
  -- LHS: (t + k*t) + (k+1)*d  ->  (t + (k+1)*d) + k*t
  calc
    (k + 1) * t.sz + (k + 1) * d.sz
        = (t.sz + k * t.sz) + (k + 1) * d.sz := by
            simpa [ht]
    _   = t.sz + (k * t.sz + (k + 1) * d.sz) := by
            rw [Nat.add_assoc]
    _   = t.sz + ((k + 1) * d.sz + k * t.sz) := by
            rw [Nat.add_comm (k * t.sz) ((k + 1) * d.sz)]
    _   = (t.sz + (k + 1) * d.sz) + k * t.sz := by
            rw [Nat.add_assoc]

/-- Therefore, glyph transport is never larger than naive transport (for k+1 requests). -/
theorem glyph_le_naive_succ (t : Template) (d : Delta) (k : Nat) :
    glyphBytes t d (k + 1) ≤ naiveBytes t d (k + 1) := by
  have h : glyphBytes t d (k + 1) ≤ glyphBytes t d (k + 1) + k * t.sz :=
    Nat.le_add_right _ _
  -- Rewrite RHS using the equality (in the reverse direction).
  simpa [ (naive_eq_glyph_plus_k_templates t d k).symm ] using h

end SymaticsBridge
