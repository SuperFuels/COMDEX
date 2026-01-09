/-
SymaticsBridge v23 — Canonicalization invariance (determinism / safety)

Mathlib-free (core Lean only).

We model a tiny expression AST, a deterministic canonicalizer `canon`, and a
prefix-code encoder/decoder pair.

The two “trust anchors”:
  (1) canon(canon(x)) = canon(x)        (idempotence)
  (2) decodeFull(encode(canon(x))) = canon(x)   (roundtrip to canonical)

Decoder is fuel-bounded to satisfy Lean termination without Mathlib.
-/

namespace SymaticsBridge

/-- Tiny AST: literals + binary ops. -/
inductive Expr where
  | lit : Nat -> Expr
  | add : Expr -> Expr -> Expr
  | mul : Expr -> Expr -> Expr
deriving Repr, DecidableEq

/-- Canonicalizer: identity baseline (deterministic).
    Replace this with your real canonicalizer later; the invariance statements remain the same. -/
def canon : Expr -> Expr := fun e => e

theorem canon_idem (e : Expr) : canon (canon e) = canon e := by
  rfl

/--
Prefix encoding into Nat tokens:
  lit n  ↦ [0, n]
  add a b ↦ [1] ++ encode a ++ encode b
  mul a b ↦ [2] ++ encode a ++ encode b
-/
def encode : Expr -> List Nat
  | Expr.lit n   => [0, n]
  | Expr.add a b => 1 :: (encode a ++ encode b)
  | Expr.mul a b => 2 :: (encode a ++ encode b)

/--
Fuel-bounded decoder for termination:
`decodeAux fuel xs` tries to parse one Expr from the front of xs
and returns (expr, remainingTokens).
-/
def decodeAux : Nat -> List Nat -> Option (Expr × List Nat)
  | 0, _ => none
  | Nat.succ fuel, [] => none
  | Nat.succ fuel, tag :: rest =>
      match tag with
      | 0 =>
          match rest with
          | n :: rest2 => some (Expr.lit n, rest2)
          | _ => none
      | 1 =>
          match decodeAux fuel rest with
          | some (a, rest1) =>
              match decodeAux fuel rest1 with
              | some (b, rest2) => some (Expr.add a b, rest2)
              | none => none
          | none => none
      | 2 =>
          match decodeAux fuel rest with
          | some (a, rest1) =>
              match decodeAux fuel rest1 with
              | some (b, rest2) => some (Expr.mul a b, rest2)
              | none => none
          | none => none
      | _ => none

/-- Public decoder: give it as much fuel as the token length. -/
def decode (xs : List Nat) : Option (Expr × List Nat) :=
  decodeAux xs.length xs

/-- Full decode: succeeds iff the whole token stream is exactly one expression. -/
def decodeFull (xs : List Nat) : Option Expr :=
  match decode xs with
  | some (e, []) => some e
  | _ => none

/-
Key lemma: if fuel is at least the token length of (encode e ++ xs),
then decoding succeeds and returns (e, xs).
-/
theorem decodeAux_encode_append :
    ∀ (e : Expr) (xs : List Nat) (fuel : Nat),
      (encode e ++ xs).length ≤ fuel ->
      decodeAux fuel (encode e ++ xs) = some (e, xs) := by
  intro e
  induction e with
  | lit n =>
      intro xs fuel hlen
      cases fuel with
      | zero =>
          -- impossible: length ≥ 1
          cases (Nat.not_succ_le_zero _ hlen)
      | succ fuel' =>
          -- decodeAux (succ fuel') (0::n::xs) = some (lit n, xs)
          simp [encode, decodeAux]
  | add a b ihA ihB =>
      intro xs fuel hlen
      cases fuel with
      | zero =>
          cases (Nat.not_succ_le_zero _ hlen)
      | succ fuel' =>
          -- list shape: 1 :: (encode a ++ encode b ++ xs)
          have hrest : (encode a ++ encode b ++ xs).length ≤ fuel' := by
            -- from (1 :: rest).length ≤ succ fuel'  ⇒ rest.length ≤ fuel'
            simpa [encode, List.length_append] using (Nat.le_of_succ_le_succ hlen)

          -- First decode a from rest, leaving (encode b ++ xs)
          have hA :
              (encode a ++ (encode b ++ xs)).length ≤ fuel' := by
            -- (encode a ++ encode b ++ xs) = encode a ++ (encode b ++ xs)
            simpa [List.append_assoc] using hrest

          have decA :
              decodeAux fuel' (encode a ++ (encode b ++ xs)) =
                some (a, (encode b ++ xs)) := ihA _ _ hA

          -- Then decode b from (encode b ++ xs) with same fuel':
          have hB : (encode b ++ xs).length ≤ fuel' := by
            -- (encode b ++ xs).length ≤ (encode a).length + (encode b ++ xs).length
            -- and that equals (encode a ++ encode b ++ xs).length ≤ fuel'
            have : (encode b ++ xs).length ≤ (encode a).length + (encode b ++ xs).length :=
              Nat.le_add_left _ _
            -- rewrite RHS to length of append
            have : (encode b ++ xs).length ≤ (encode a ++ (encode b ++ xs)).length := by
              simpa [List.length_append] using this
            exact Nat.le_trans this hA

          have decB :
              decodeAux fuel' (encode b ++ xs) = some (b, xs) := ihB _ _ hB

          -- unfold decodeAux at tag=1 and plug in the two decodes
          simp [encode, decodeAux, decA, decB, List.append_assoc]
  | mul a b ihA ihB =>
      intro xs fuel hlen
      cases fuel with
      | zero =>
          cases (Nat.not_succ_le_zero _ hlen)
      | succ fuel' =>
          have hrest : (encode a ++ encode b ++ xs).length ≤ fuel' := by
            simpa [encode, List.length_append] using (Nat.le_of_succ_le_succ hlen)

          have hA :
              (encode a ++ (encode b ++ xs)).length ≤ fuel' := by
            simpa [List.append_assoc] using hrest

          have decA :
              decodeAux fuel' (encode a ++ (encode b ++ xs)) =
                some (a, (encode b ++ xs)) := ihA _ _ hA

          have hB : (encode b ++ xs).length ≤ fuel' := by
            have : (encode b ++ xs).length ≤ (encode a).length + (encode b ++ xs).length :=
              Nat.le_add_left _ _
            have : (encode b ++ xs).length ≤ (encode a ++ (encode b ++ xs)).length := by
              simpa [List.length_append] using this
            exact Nat.le_trans this hA

          have decB :
              decodeAux fuel' (encode b ++ xs) = some (b, xs) := ihB _ _ hB

          simp [encode, decodeAux, decA, decB, List.append_assoc]

/-- Decode after encode, leaving an arbitrary tail intact. -/
theorem decode_encode_append (e : Expr) (xs : List Nat) :
    decode (encode e ++ xs) = some (e, xs) := by
  -- decode uses fuel = length
  simp [decode, decodeAux_encode_append, Nat.le_refl]

/-- Full roundtrip: decodeFull(encode e) = some e. -/
theorem decodeFull_encode (e : Expr) :
    decodeFull (encode e) = some e := by
  -- decode (encode e) = some (e, [])
  have h : decode (encode e) = some (e, []) := by
    simpa using (decode_encode_append e [])
  simp [decodeFull, h]

/-- v23 “roundtrip to canonical”: decodeFull(encode(canon e)) = canon e. -/
theorem decodeFull_encode_canon (e : Expr) :
    decodeFull (encode (canon e)) = some (canon e) := by
  simpa [canon] using (decodeFull_encode e)

end SymaticsBridge
