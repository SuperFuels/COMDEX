import Tessaris.Symatics.Prelude

namespace Tessaris.Symatics.Bridge

/-
v17 (mathlib-free):
  family : right-growing phase-interference chain over atoms 0..n
  tagify : boolean-ish encoding with explicit phase tags

We prove:
  nodesP (family n)            = 2*n + 1
  nodesB (tagify (family n))   = 4*n + 1
  nodesB(tagify(family n)) + 1 = 2 * nodesP(family n)
-/

-- Native phase expression
inductive PhaseExpr where
  | atom  : Nat → PhaseExpr
  | inter : Nat → PhaseExpr → PhaseExpr → PhaseExpr
  deriving Repr, DecidableEq

def nodesP : PhaseExpr → Nat
  | .atom _      => 1
  | .inter _ a b => 1 + nodesP a + nodesP b

-- Boolean-ish tagged encoding
inductive BoolTagged where
  | atom  : Nat → BoolTagged
  | phase : Nat → BoolTagged
  | band  : BoolTagged → BoolTagged → BoolTagged
  deriving Repr, DecidableEq

def nodesB : BoolTagged → Nat
  | .atom _    => 1
  | .phase _   => 1
  | .band a b  => 1 + nodesB a + nodesB b

-- Family: interference chain over atoms 0..n
def family : Nat → PhaseExpr
  | 0   => .atom 0
  | n+1 => .inter n (family n) (.atom (n+1))

-- Tagify: inter φ a b ↦ band (phase φ) (band (tagify a) (tagify b))
def tagify : PhaseExpr → BoolTagged
  | .atom k      => .atom k
  | .inter φ a b => .band (.phase φ) (.band (tagify a) (tagify b))

/- -----------------------------
Tiny arithmetic helpers (stable)
----------------------------- -/

/-- 1 + (1 + t) = 2 + t.  (proved by Nat recursion; avoids simp getting stuck) -/

theorem add11 (t : Nat) : 1 + (1 + t) = 2 + t := by
  -- Nat.add_assoc 1 1 t : (1+1)+t = 1+(1+t)
  -- we want the reverse direction
  simpa [Nat.add_assoc] using (Nat.add_assoc 1 1 t).symm

theorem add11_mul2 (n : Nat) : 1 + (1 + 2 * n) = 2 + 2 * n := by
  simpa using (add11 (2 * n))


/-- 1 + (1 + (2 + t)) = 4 + t. -/

theorem add112 (t : Nat) : 1 + (1 + (2 + t)) = 4 + t := by
  calc
    1 + (1 + (2 + t)) = 2 + (2 + t) := by
      simpa [Nat.add_assoc] using (Nat.add_assoc 1 1 (2 + t)).symm
    _ = 4 + t := by
      simpa [Nat.add_assoc] using (Nat.add_assoc 2 2 t).symm


/-- Normal form for the tagify "step" arithmetic: 1+1+(1+t+1) = t+4. -/
theorem band_step (t : Nat) : 1 + 1 + (1 + t + 1) = t + 4 := by
  have hshape : 1 + 1 + (1 + t + 1) = 1 + (1 + (2 + t)) := by
    simp [Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]
  calc
    1 + 1 + (1 + t + 1)
        = 1 + (1 + (2 + t)) := hshape
    _   = 4 + t := add112 t
    _   = t + 4 := by simpa [Nat.add_comm]

/-- 2*(2*n) = 4*n. -/
theorem mul2_mul2 (n : Nat) : 2 * (2 * n) = 4 * n := by
  calc
    2 * (2 * n) = (2 * 2) * n := by
      -- assoc, in the direction we need
      simpa using (Nat.mul_assoc 2 2 n).symm
    _ = 4 * n := by simp

/- -----------------------------
Main size theorems
----------------------------- -/

/-- Native family size: nodesP (family n) = 2*n + 1. -/
theorem nodesP_family : ∀ n : Nat, nodesP (family n) = 2 * n + 1
  | 0 => by
      simp [family, nodesP]
  | n+1 => by
      have ih := nodesP_family n
      -- unfold one step, plug IH, normalize
      calc
        nodesP (family (n+1))
            = 1 + nodesP (family n) + 1 := by
                simp [family, nodesP, Nat.add_assoc]
        _   = 1 + (2 * n + 1) + 1 := by
                simpa [ih]
        _   = 2 * (n + 1) + 1 := by
                  -- reduce both sides to 1 + (1 + 2*n)
                  simp [Nat.mul_succ, Nat.add_assoc, Nat.add_comm, Nat.add_left_comm, add11]
/-- Tagged family size: nodesB (tagify (family n)) = 4*n + 1. -/
theorem nodesB_tagify_family : ∀ n : Nat, nodesB (tagify (family n)) = 4 * n + 1
  | 0 => by
      simp [family, tagify, nodesB]
  | n+1 => by
      have ih := nodesB_tagify_family n
      -- unfold one step; use band_step to avoid simp-stuck goal 1+(1+(2+4*n)) = 4+4*n
      calc
        nodesB (tagify (family (n+1)))
            = 1 + 1 + (1 + nodesB (tagify (family n)) + 1) := by
                simp [family, tagify, nodesB, Nat.add_assoc]
        _   = nodesB (tagify (family n)) + 4 := by
                simpa [Nat.add_assoc, Nat.add_comm, Nat.add_left_comm] using (band_step (nodesB (tagify (family n))))
        _   = (4 * n + 1) + 4 := by
                simpa [ih]
        _   = 4 * (n + 1) + 1 := by
                simp [Nat.mul_succ, Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]

/-- Gap statement (no subtraction): nodesB(tagify(family n)) + 1 = 2 * nodesP(family n). -/
theorem tagged_vs_native (n : Nat) :
    nodesB (tagify (family n)) + 1 = 2 * nodesP (family n) := by
  have hp : nodesP (family n) = 2 * n + 1 := nodesP_family n
  have hb : nodesB (tagify (family n)) = 4 * n + 1 := nodesB_tagify_family n
  calc
    nodesB (tagify (family n)) + 1
        = (4 * n + 1) + 1 := by simpa [hb]
    _   = 4 * n + 2 := by simp [Nat.add_assoc]
    _   = (2 * (2 * n)) + 2 := by
            have hm : 4 * n = 2 * (2 * n) := (mul2_mul2 n).symm
            simpa [hm]
    _   = 2 * (2 * n + 1) := by
            simp [Nat.mul_add, Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]
    _   = 2 * nodesP (family n) := by
            simpa [hp]

end Tessaris.Symatics.Bridge

/-
Lock ID: v17-phase-interference-bloat@50a3fda13e849275d7123970830cc559507a4235c07b90ebea3e5ced859222f7
Status: LOCKED 2026-01-09
Maintainer: Tessaris AI
Author: Kevin Robinson.

Benchmark output (backend/tests/glyphos_wirepack_v17_phase_interference_bloat_benchmark.py):

| n   | canon_raw | canon_gz | tagged_raw | tagged_gz | gz_ratio |
|-----|----------:|---------:|-----------:|----------:|---------:|
| 1   | 23        | 37       | 43         | 50        | 1.35     |
| 2   | 39        | 44       | 79         | 56        | 1.27     |
| 4   | 71        | 55       | 151        | 67        | 1.22     |
| 8   | 135       | 72       | 295        | 91        | 1.26     |
| 16  | 276       | 103      | 596        | 130       | 1.26     |
| 32  | 564       | 157      | 1204       | 195       | 1.24     |
| 64  | 1140      | 271      | 2420       | 327       | 1.21     |
| 128 | 2349      | 541      | 4909       | 634       | 1.17     |
| 256 | 4909      | 1051     | 10029      | 1218      | 1.16     |

Hashes:
- PhaseInterferenceBloat.lean: 50a3fda13e849275d7123970830cc559507a4235c07b90ebea3e5ced859222f7
- v17_phase_out.txt: 291215f72c8d8a837185e90dda24b90f7cedf3e2fda393295aea132ccb47fd70
-/
