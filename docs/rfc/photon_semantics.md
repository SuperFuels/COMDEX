# Photon Semantics — Meta-Operators Extension (E3)

This document specifies **Photon Algebra semantics (Phase 1)** as implemented by:

- `backend/photon_algebra/rewriter.py` (AST normalizer; source of truth)
- `backend/photon_algebra/core.py` (constants: ∅, ⊤, ⊥)

**Scope:** This is **not** the SymPy calculus rewriter. In this spec, `∇` is **not** a Photon Algebra operator.

---

## 0. Phase Model

### Phase 1 (current)
- Defines the **core operator set** and **normal-form (NF) behavior**.
- Meta-operators exist and round-trip, but have **minimal semantics** (see §3).
- Normalization is deterministic and idempotent:
  - `normalize(normalize(e)) == normalize(e)`.

### Phase 2 (future)
- Adds richer semantics for meta-operators (≈ as SQI-weighted similarity, ⊂ as ordering/subsumption).
- May introduce explicit measurement/collapse operator **μ** if/when needed.
  - Until then, “collapse/selection” semantics remain **out of scope** for Photon Algebra Phase 1.

---

# 1. Core Operators (Phase 1)

Photon expressions are AST nodes:
- Atoms: `"a"`, `"x"`, `"TOKEN"`, …
- Unary: `{"op": "¬", "state": e}`, `{"op":"★","state": e}`
- N-ary: `{"op":"⊕","states":[...]}`, `{"op":"⊗","states":[...]}`, `{"op":"↔","states":[...]}`, `{"op":"⊖","states":[...]}`

Constants:
- `∅` (empty / neutral)
- `⊤` (top)
- `⊥` (bottom)

Operator set:
- `⊕` Superposition
- `⊗` Fusion / Amplification
- `⊖` Cancellation / Difference
- `↔` Entanglement / Equivalence-grouping
- `¬` Negation
- `★` Projection
- `∅` Empty

---

## 1.1 ⊕ Superposition (Sum)

**Intuition:** A nondeterministic “sum-like” set of candidate states.

**Normalization invariants:**
- **Flattening:** `⊕(…, ⊕(…), …)` is flattened to one ⊕ list.
- **Identity removal:** `∅` is removed from ⊕.
- **Commutative canonical order:** operands are deterministically ordered.
- **Idempotence:** duplicates are removed (`a ⊕ a → a`).
- **Absorption:** if `a` is present, drop any product containing `a`:
  - `a ⊕ (a ⊗ b) → a` (and symmetric forms).
- **Top absorption:** if any operand is `⊤`, result is `⊤`.
- **Duality shortcut (Phase 1):** if both `a` and `¬a` occur in a ⊕, result is `⊤`.

**Non-goal (termination guard):**
- Photon Algebra does **not** factor products out of sums (no “T14 factoring”):
  - `a ⊕ (b ⊗ c)` is **not** rewritten into `(a ⊕ b) ⊗ (a ⊕ c)`.

---

## 1.2 ⊗ Fusion / Amplification (Product)

**Intuition:** A “product-like” conjunction / resonance operator.

**Normalization invariants:**
- **Flattening:** nested ⊗ is flattened.
- **Annihilator:** if any factor is `∅`, whole product collapses to `∅`.
- **Commutative canonical order:** factors are deterministically ordered.
- **Idempotence:** duplicates removed (`a ⊗ a → a`).
- **Bottom absorption:** if any factor is `⊥`, result is `⊥`.
- **Negation absorption:** if both `a` and `¬a` appear, result is `⊥`.
- **Distribution (one-way):** ⊗ distributes over ⊕ and never reverses:
  - `a ⊗ (b ⊕ c) → (a ⊗ b) ⊕ (a ⊗ c)`

**NF invariant:** After normalization, **no `⊕` may appear directly under a `⊗`**.

---

## 1.3 ⊖ Cancellation / Difference (Directional)

**Intuition:** A directional subtraction/cancellation operator.

**Normalization invariants:**
- **Non-commutative:** operand order is preserved.
- **Basic cancellation:**
  - `a ⊖ a → ∅`
  - `a ⊖ ∅ → a`
  - `∅ ⊖ a → a`
- Optional chained/nested cancellation rules may apply (implementation-defined),
  but must preserve termination and avoid commutativity assumptions.

---

## 1.4 ¬ Negation

**Normalization invariants:**
- `¬(¬a) → a`
- `¬∅ → ∅`
- **De Morgan (guarded):**
  - `¬(a ⊕ b ⊕ …) → (¬a) ⊗ (¬b) ⊗ …`
  - `¬(a ⊗ b ⊗ …) → (¬a) ⊕ (¬b) ⊕ …`
- Special-case interaction with `★` is allowed (see §1.6).

---

## 1.5 ↔ Entanglement / Equivalence Grouping

**Intuition:** Groups states into a symmetric “linked” structure.

**Phase 1 semantics:**
- Treated structurally with local normalization:
  - flatten nested ↔
  - if only one member remains, collapse to that member.

**Note:** Any “physical nonlocal” entanglement semantics is **out of scope** here.
This operator is an algebraic container in Phase 1.

---

## 1.6 ★ Projection

**Intuition:** Marks a projected/scored view of a state.

**Phase 1 behavior (as implemented):**
- Normalizes the inner expression first.
- May apply **projection-fidelity distribution** over ↔:
  - `★(a ↔ b) → (★a) ⊕ (★b)`
- Supports a practical collapse shortcut used for stability:
  - If a sum contains both `a` and `★a`, it collapses to `★a`:
    - `★(a ⊕ ★a ⊕ b) → ★a`
    - and the equivalent flattened forms.

This is **projection behavior**, not “measurement/collapse” as a separate operator.

---

## 1.7 ∅ Empty

- Canonical empty/neutral element.
- Acts as:
  - ⊕ identity (removed)
  - ⊗ annihilator (kills product)
  - ⊖ cancellation identity rules (see §1.3)

---

# 2. Normal Form Guarantee (Phase 1)

The normal form enforced by `normalize()` is **sum-of-products**:

- ⊕ is flattened, ∅-free, commutative-canonical, idempotent, absorption-reduced.
- ⊗ is flattened, ∅-annihilated, commutative-canonical, idempotent, and **distributes over ⊕**.
- **Invariant:** no `⊕` appears directly under `⊗` after normalization.
- Factoring is intentionally excluded to prevent rewrite ping-pong.

---

# 3. Meta-Operators Extension (E3)

In addition to core operators, Photon supports:

- `⊤` Top
- `⊥` Bottom
- `≈` Similarity
- `⊂` Containment

These round-trip through parser/printer and are supported by normalization
with **minimal Phase 1 semantics** (not purely inert).

---

## 3.1 ⊤ (Top Element)

- **Definition:** universal truth / always-present element.
- **Analogy:** Boolean `True`.
- **Phase 1 normalization:**
  - `a ≈ a → ⊤`
  - `a ⊂ ⊤ → ⊤`
  - In ⊕, if any operand is `⊤`, entire ⊕ collapses to `⊤`.

---

## 3.2 ⊥ (Bottom Element)

- **Definition:** contradiction / impossible state.
- **Analogy:** Boolean `False`.
- **Phase 1 normalization:**
  - In ⊗, if any operand is `⊥`, entire ⊗ collapses to `⊥`.
  - Negation absorption: `a ⊗ ¬a → ⊥`.
  - Containment shortcut: `⊥ ⊂ b → ⊤` (vacuously true in Phase 1).

---

## 3.3 a ≈ b (Similarity)

- **Definition:** binary similarity relation between states.
- **Analogy:** fuzzy equivalence / approximate equality.
- **Phase 1 normalization:**
  - If `a` and `b` are structurally identical, normalize to `⊤`.
  - Otherwise preserved structurally:
    - `normalize(a ≈ b) = (normalize(a)) ≈ (normalize(b))` (with canonical ordering if enabled).

**Note:** No metric/SQI scoring semantics is attached yet in Phase 1.

---

## 3.4 a ⊂ b (Containment)

- **Definition:** binary containment / inclusion relation.
- **Analogy:** subset or subtyping.
- **Phase 1 normalization:**
  - If `a` and `b` are structurally identical, normalize to `⊤`.
  - Vacuity shortcuts:
    - `⊥ ⊂ b → ⊤`
    - `a ⊂ ⊤ → ⊤`
  - Otherwise preserved structurally:
    - `normalize(a ⊂ b) = (normalize(a)) ⊂ (normalize(b))`
- **Non-commutative:** operand order is preserved.

---

# 4. Summary

- This spec defines **Photon Algebra Phase 1** semantics and NF invariants as implemented in `backend/photon_algebra`.
- `∇` is **not** an operator here; calculus/Grad lives in a separate module/spec.
- Meta-operators are supported with **minimal semantics** (not purely inert):
  - equality-to-⊤ for ≈ and ⊂ when structurally identical
  - vacuity rules for ⊂
  - top/bottom absorption behavior in ⊕/⊗

---

# 5. Phase 2 Targets (Non-Normative)

- Define ≈ via SQI similarity (metric, cosine, embedding distance).
- Define ⊂ as a partial order / subsumption lattice with monotonic rewrites.
- Define explicit measurement/collapse operator **μ** if required by higher layers.
- Extend ★ semantics if projection needs probabilistic/scored behavior beyond Phase 1 shortcuts.