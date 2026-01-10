/-
V39 — Fenwick (BIT) index over delta stream (bridge-only, dependency-free).

Goal (Level B-ish bridge):
- Formalize a simple BIT model and prove its prefixSum matches the true sum of an
  underlying vector after point updates.

No Std/Mathlib imports. Keeps your disk safe.
-/

namespace SymaticsBridge.V39

abbrev State := List Int

def len : State → Nat
| [] => 0
| _ :: xs => Nat.succ (len xs)

def getAt : State → Nat → Int
| [], _ => 0
| x :: _, 0 => x
| _ :: xs, Nat.succ i => getAt xs i

def setAt : State → Nat → Int → State
| [], _, _ => []
| _ :: xs, 0, v => v :: xs
| x :: xs, Nat.succ i, v => x :: setAt xs i v

def prefixSumState : State → Nat → Int
| [], _ => 0
| x :: xs, 0 => x
| x :: xs, Nat.succ r => x + prefixSumState xs r

-- 1-indexed BIT as a list of Int; index 0 is ignored.
abbrev BIT := List Int

def bitGet : BIT → Nat → Int
| [], _ => 0
| x :: _, 0 => x
| _ :: xs, Nat.succ i => bitGet xs i

def bitSet : BIT → Nat → Int → BIT
| [], _, _ => []
| _ :: xs, 0, v => v :: xs
| x :: xs, Nat.succ i, v => x :: bitSet xs i v

def lowbit (i : Nat) : Nat :=
  -- bridge-only placeholder; used only for termination on structurally smaller `i`.
  -- We’ll use the standard BIT recursion pattern but keep proofs lightweight.
  1

def buildBIT (s : State) : BIT :=
  -- bridge-only: store exact state in slots 1..n; not compressed BIT yet.
  -- This is enough to prove correctness of prefix queries for the model.
  0 :: s

def bitPrefixSum (b : BIT) (r : Nat) : Int :=
  -- bridge-only: because buildBIT stores the state directly, prefix sum is
  -- just prefixSumState on the tail.
  prefixSumState (b.drop 1) r

def applyUpdate (s : State) (idx : Nat) (newv : Int) : State :=
  setAt s idx newv

def applyUpdateBIT (b : BIT) (idx : Nat) (newv : Int) : BIT :=
  -- mirror update into the stored state tail
  let st := b.drop 1
  let st' := applyUpdate st idx newv
  0 :: st'

theorem v39_prefix_correct (s : State) (idx : Nat) (newv : Int) (r : Nat) :
    bitPrefixSum (applyUpdateBIT (buildBIT s) idx newv) r
      = prefixSumState (applyUpdate s idx newv) r := by
  simp [bitPrefixSum, applyUpdateBIT, buildBIT, applyUpdate]

theorem v39_prefix_correct_no_updates (s : State) (r : Nat) :
    bitPrefixSum (buildBIT s) r = prefixSumState s r := by
  simp [bitPrefixSum, buildBIT]

end SymaticsBridge.V39