/-
V41 — Provenance / receipt-gated queries (auth + ancestry bound)

Level-A target: no `sorry`.
Dependency-light (core Lean only).

This bridge is intentionally crypto-light:
- Hash is Nat (stand-in)
- Signature validity is equality to the message hash (stand-in)
The point is the *shape* of provenance gating: parent-link + signature over receipt hash.
-/

namespace SymaticsBridge.V41

abbrev Hash   := Nat
abbrev Delta  := Nat
abbrev Answer := Nat

/-- Minimal receipt model. -/
structure Receipt where
  parent : Hash
  delta  : Delta
  sig    : Hash
deriving Repr, DecidableEq

/-- Stand-in delta hash. (Identity; injective by definitional equality.) -/
def hashDelta (d : Delta) : Hash := d

/-- Hash of a receipt body (parent + delta hash). -/
def hashReceipt (r : Receipt) : Hash :=
  r.parent + hashDelta r.delta

/-- Stand-in signature validity. -/
def SigValid (s : Hash) (msg : Hash) : Prop := s = msg

/-- Receipt validity: signature must validate on the receipt hash. -/
def ReceiptOk (r : Receipt) : Prop :=
  SigValid r.sig (hashReceipt r)

/-- Chain validity: each next parent must equal previous receipt hash, and all receipts validate. -/
def ChainOk : List Receipt → Prop
| [] => True
| [r] => ReceiptOk r
| r1 :: r2 :: rs =>
    ReceiptOk r1 ∧ r2.parent = hashReceipt r1 ∧ ChainOk (r2 :: rs)

/-- Analytics fold (toy): sum deltas. -/
def foldQ (a : Answer) (d : Delta) : Answer := a + d
def runQ (ds : List Delta) : Answer := ds.foldl foldQ 0

/-- A gated answer: only accepted if computed over a ChainOk receipt stream. -/
def GatedAnswer (rs : List Receipt) (a : Answer) : Prop :=
  ChainOk rs ∧ a = runQ (rs.map (fun r => r.delta))

-- -------------------- tamper models --------------------

def tamperDelta (r : Receipt) (d' : Delta) : Receipt := { r with delta := d' }
def tamperParent (r : Receipt) (p' : Hash) : Receipt := { r with parent := p' }

-- -------------------- core tamper lemmas --------------------

theorem hashReceipt_tamperParent_ne (r : Receipt) (p' : Hash) (hne : p' ≠ r.parent) :
  hashReceipt (tamperParent r p') ≠ hashReceipt r := by
  intro h
  have h0 : p' + hashDelta r.delta = r.parent + hashDelta r.delta := by
    simpa [hashReceipt, tamperParent] using h
  have : p' = r.parent := Nat.add_right_cancel h0
  exact hne this

theorem hashReceipt_tamperDelta_ne (r : Receipt) (d' : Delta) (hne : d' ≠ r.delta) :
  hashReceipt (tamperDelta r d') ≠ hashReceipt r := by
  intro h
  have h0 : r.parent + hashDelta d' = r.parent + hashDelta r.delta := by
    simpa [hashReceipt, tamperDelta] using h
  have hd : hashDelta d' = hashDelta r.delta := Nat.add_left_cancel h0
  have : d' = r.delta := by simpa [hashDelta] using hd
  exact hne this

theorem tamperParent_breaks (r : Receipt) (p' : Hash) (hne : p' ≠ r.parent) :
  ReceiptOk r → ¬ ReceiptOk (tamperParent r p') := by
  intro hok hok'
  have hs  : r.sig = hashReceipt r := hok
  have hs' : r.sig = hashReceipt (tamperParent r p') := by
    simpa [ReceiptOk, SigValid] using hok'
  have : hashReceipt (tamperParent r p') = hashReceipt r := by
    calc
      hashReceipt (tamperParent r p') = r.sig := by simpa using hs'.symm
      _ = hashReceipt r := hs
  exact (hashReceipt_tamperParent_ne r p' hne) this

theorem tamperDelta_breaks (r : Receipt) (d' : Delta) (hne : d' ≠ r.delta) :
  ReceiptOk r → ¬ ReceiptOk (tamperDelta r d') := by
  intro hok hok'
  have hs  : r.sig = hashReceipt r := hok
  have hs' : r.sig = hashReceipt (tamperDelta r d') := by
    simpa [ReceiptOk, SigValid] using hok'
  have : hashReceipt (tamperDelta r d') = hashReceipt r := by
    calc
      hashReceipt (tamperDelta r d') = r.sig := by simpa using hs'.symm
      _ = hashReceipt r := hs
  exact (hashReceipt_tamperDelta_ne r d' hne) this

/-- Reordering breaks the parent-link unless the swapped link happens to match. -/
theorem reorder_breaks (r1 r2 : Receipt) (rs : List Receipt)
  (hneq : r1.parent ≠ hashReceipt r2) :
  ¬ ChainOk (r2 :: r1 :: rs) := by
  intro hswap
  have : r1.parent = hashReceipt r2 := by
    -- ChainOk (r2::r1::rs) gives: r1.parent = hashReceipt r2
    exact hswap.2.1
  exact hneq this

/-- Splicing out the head-link breaks unless the new head-parent is rewired. -/
theorem splice_breaks (r1 r2 r3 : Receipt) (rs : List Receipt)
  (hneq : r3.parent ≠ hashReceipt r1) :
  ¬ ChainOk (r1 :: r3 :: rs) := by
  intro hsp
  have : r3.parent = hashReceipt r1 := by
    exact hsp.2.1
  exact hneq this

end SymaticsBridge.V41
