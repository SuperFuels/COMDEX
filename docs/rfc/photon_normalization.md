# Photon Normalization Spec (RFC)

This RFC defines the **normal form (NF) invariants** enforced by `backend/photon_algebra/rewriter.normalize`.

---

## Normal Form Invariants

After `normalize(expr)`:

### `⊕` (superposition / sum)
- Flattened (`⊕` never nests directly under `⊕`).
- Identity removed (`∅`).
- Idempotent and commutative with deterministic ordering.
- Absorption: if `a` is present, drop `a ⊗ b`.
- **We do not factor T14**:  
  `a ⊕ (b ⊗ c)` is **not** rewritten here (avoids ⊗↔⊕ ping-pong).

### `⊗` (fusion / product)
- Annihilator: `a ⊗ ∅ = ∅`.
- Commutative with deterministic ordering.
- Local idempotence: `a ⊗ a = a`.
- Dual absorption: `a ⊗ (a ⊕ b) = a`.
- **Distribution over ⊕ only happens here**:  
  `(a) ⊗ (b ⊕ c)` → `(a ⊗ b) ⊕ (a ⊗ c)`.

➡ **Invariant**:  
After normalization, **no `⊕` may appear directly under a `⊗`**.

### Other Ops
- Negation: `¬(¬a) = a`.
- Cancellation:  
  - `a ⊖ a = ∅`  
  - `a ⊖ ∅ = a`  
  - `∅ ⊖ a = a`.
- Projection fidelity (★), entanglement (↔), etc. are normalized locally and then treated structurally.

---

## Termination Guarantee

- No rewrite ping-pong:
  - T14 factoring is excluded from `REWRITE_RULES`.
  - ⊗ distributes over ⊕ *once*, never reversed.
- `normalize(normalize(e)) == normalize(e)` (idempotence).
- Structural canonicalization ensures deterministic results.

---

## Sanity Checklist

- `⊕`: flattened, ∅-free, idempotent, commutative, absorption-reduced.
- `⊗`: order-canonical, annihilator handled, distributes over ⊕.
- No `⊕` directly under `⊗`.
- Local collapses respected (`⊖`, `¬`, `⊗` idempotence).

---

## Example Reductions

- `a ⊕ (a ⊗ b)` → `a`  
- `a ⊗ (b ⊕ c)` → `(a ⊗ b) ⊕ (a ⊗ c)`  
- `a ⊗ (a ⊕ a)` → `a`  
- `¬(¬a)` → `a`  
- `a ⊖ ∅` → `a`  

---

## Why ⊗ Idempotence Lives in `normalize()`

We deliberately enforce `a ⊗ a → a` **inside** the `⊗` branch of `normalize()`, not in `REWRITE_RULES`.  
Reasons:
1. **Termination & ping-pong control** — avoids interaction with ⊗ distribution and excluded T14 factoring.
2. **Canonicalization locality** — collapse occurs adjacent to commutativity ordering, guaranteeing stable forms.

---

✅ If these invariants fail, it means Photon Algebra is no longer canonicalizing expressions correctly.