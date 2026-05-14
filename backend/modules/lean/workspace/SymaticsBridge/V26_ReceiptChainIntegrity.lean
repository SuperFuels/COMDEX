import Mathlib

/-!
v26 — Receipt Chain Integrity (Authenticated Delta Receipt)

This module captures two buyer-facing trust properties for Template+Delta receipts:

1) Integrity (field binding):
   If a receipt’s authenticated digest verifies, then any change to any field changes the digest,
   so verification fails unless the attacker can produce a fresh valid authenticator.

2) Ancestry binding (chain integrity):
   Each receipt commits to the previous receipt digest via `parent`, preventing deletion,
   reordering, or splicing without detection (modulo digest collisions / auth breaks).

Notes:
- We model canonical bytes via `encodeVarint` (abstract but deterministic as a function).
- We model hashing as an abstract function `H`.
- Authentication is modeled as “signature commits to digest” (idealized, minimal).
  You can later replace `Sig/sign/verify` with your real Ed25519 or AEAD MAC model.
-/

namespace SymaticsBridge.V26

/-- Byte string model used for the structured preimage. -/
abbrev Bytes := List UInt8

/-- Abstract varint (or fixed) encoding for Nat fields. Deterministic by being a function. -/
constant encodeVarint : Nat → Bytes

/-- Abstract hash function (e.g., BLAKE3/SHA-256). -/
constant H : Bytes → Bytes

/-- Canonical “zero parent” (genesis). Adjust length to your digest size if desired. -/
def zeroDigest : Bytes := List.replicate 32 (0 : UInt8)

/-- Receipt fields from the spec. All hashes are over canonical bytes. -/
structure Receipt where
  algId        : Nat        -- hash/sign algorithm id (for rotation)
  templateHash : Bytes      -- H(template_bytes_canon)
  deltaHash    : Bytes      -- H(delta_bytes_canon)
  parent       : Bytes      -- previous receipt digest (or zeroDigest for genesis)
  phaseId      : Nat        -- phase id (varint or fixed)
  schemaVer    : Nat        -- schema version (varint)
deriving Repr

/-- Structured preimage (NOT “hash-of-hash soup”): a single concatenation in a fixed order. -/
def receiptPreimage (r : Receipt) : Bytes :=
  encodeVarint r.algId
  ++ r.templateHash
  ++ r.deltaHash
  ++ r.parent
  ++ encodeVarint r.phaseId
  ++ encodeVarint r.schemaVer

/-- Receipt digest commits to all receipt fields. -/
def receiptDigest (r : Receipt) : Bytes :=
  H (receiptPreimage r)

/-!
Authentication model (minimal, cheap):

We model a signature as carrying the digest it was produced for.
`verify pk d sig` holds iff the signature commits to the same digest `d`.

This captures the *binding* property cleanly; swapping to real Ed25519 later
means replacing these defs/lemmas with crypto assumptions.
-/

/-- Signature object (idealized). -/
structure Sig where
  d : Bytes
deriving Repr

/-- Sign a digest. (sk/pk types are abstracted as Nat for now.) -/
def sign (_sk : Nat) (d : Bytes) : Sig := ⟨d⟩

/-- Verify a signature against a digest. -/
def verify (_pk : Nat) (d : Bytes) (s : Sig) : Prop :=
  s.d = d

/-- Integrity: if the *same* authenticator verifies two receipts, their digests are equal. -/
theorem integrity_digest_eq {pk : Nat} {r r' : Receipt} {s : Sig} :
    verify pk (receiptDigest r) s →
    verify pk (receiptDigest r') s →
    receiptDigest r = receiptDigest r' := by
  intro h h'
  -- from s.d = digest(r) and s.d = digest(r'), deduce digests equal
  simpa [verify] using Eq.trans (Eq.symm h) h'

/-- Corollary: if digests differ, a fixed signature cannot verify both. -/
theorem integrity_detects_change {pk : Nat} {r r' : Receipt} {s : Sig} :
    receiptDigest r ≠ receiptDigest r' →
    verify pk (receiptDigest r) s →
    ¬ verify pk (receiptDigest r') s := by
  intro hne hv
  intro hv'
  exact hne (integrity_digest_eq (pk := pk) (r := r) (r' := r') (s := s) hv hv')

/-!
Receipt chain validity:

- Genesis receipt must have parent = zeroDigest.
- Each subsequent receipt’s parent must equal the previous receiptDigest.
-/

/-- Tail constraint: all receipts must point to the expected `prev` digest. -/
def ChainOkFrom (prev : Bytes) : List Receipt → Prop
  | []      => True
  | r :: rs => (r.parent = prev) ∧ ChainOkFrom (receiptDigest r) rs

/-- Full chain constraint: first receipt is genesis, then ChainOkFrom proceeds. -/
def ChainOk : List Receipt → Prop
  | []      => True
  | r :: rs => (r.parent = zeroDigest) ∧ ChainOkFrom (receiptDigest r) rs

/-- Ancestry binding (local step): if r₂ points to both digests, those digests must match. -/
theorem ancestry_binding_step {r1 r1' r2 : Receipt} {rs : List Receipt} :
    ChainOk (r1 :: r2 :: rs) →
    ChainOk (r1' :: r2 :: rs) →
    receiptDigest r1 = receiptDigest r1' := by
  intro h h'
  -- unpack ChainOk for both chains
  rcases h with ⟨hgen1, hfrom1⟩
  rcases h' with ⟨hgen1', hfrom1'⟩
  -- unpack the first step of ChainOkFrom: r2.parent = digest(r1)
  rcases hfrom1 with ⟨hparent2, _hrest⟩
  rcases hfrom1' with ⟨hparent2', _hrest'⟩
  -- same r2.parent in both implies digests equal
  exact by simpa [hparent2] using hparent2'

/-- Deletion detection (simple case):
If you drop the genesis receipt, the next receipt would need parent=zeroDigest,
but in a valid chain its parent is digest(genesis), so it fails unless that digest is zero.
-/
theorem deletion_detected {r1 r2 : Receipt} {rs : List Receipt} :
    ChainOk (r1 :: r2 :: rs) →
    receiptDigest r1 ≠ zeroDigest →
    ¬ ChainOk (r2 :: rs) := by
  intro hok hne
  intro hok'
  -- from hok, r2.parent = digest(r1)
  rcases hok with ⟨_hgen, hfrom⟩
  rcases hfrom with ⟨hparent2, _⟩
  -- from hok', r2.parent = zeroDigest
  rcases hok' with ⟨hparent2_zero, _⟩
  -- contradict digest(r1) ≠ zeroDigest
  have : receiptDigest r1 = zeroDigest := by
    -- r2.parent equals both; rewrite
    calc
      receiptDigest r1 = r2.parent := by simpa [hparent2]
      _ = zeroDigest := by simpa [hparent2_zero]
  exact hne this

end SymaticsBridge.V26