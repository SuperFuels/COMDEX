# PhotonAlgebra — Phase-1 Proof Snapshot (Lean)

This file records the **actual proved theorems** in the current PhotonAlgebra stack and the minimal notes needed to understand *why* they hold.

> Source modules (Lean):
> - `PhotonAlgebra/Basic.lean` (AST, BEq)
> - `PhotonAlgebra/Canon.lean` (canonicalization for ⊕ / ⊗)
> - `PhotonAlgebra/NormalizerWF.lean` (core reference normalizer)
> - `PhotonAlgebra/Normalizer.lean` (public normalizer; `normStep = normalizeWF`)
> - `PhotonAlgebra/CanonStability.lean` (canon stability lemmas, if split out)
> - `PhotonAlgebra/BridgeTheorem.lean` (bridge invariants)
> - `PhotonAlgebra/Phase1Theorems.lean` (Phase-1 laws)

---

## What “proved” means here

All theorems listed below are **Lean theorems** (not `axiom`, not `sorry`) and the current build passes:

- `lake build PhotonAlgebra.BridgeTheorem`
- `lake build PhotonAlgebra.Phase1Theorems`
- `lake build PhotonAlgebra.SnapshotGen`

If any theorem is reverted to `axiom`, the `#print axioms PhotonAlgebra.<Thm>` check will reveal it.

---

## Core Definitions

### Expr
`Expr` is the PA-core AST:

- `atom`, `empty`
- `plus : List Expr`   (⊕)
- `times : List Expr`  (⊗)
- `entangle a b`       (↔)
- `neg e`              (¬)
- `cancel a b`         (⊖)
- `project e`          (★)
- `collapse e`         (∇)

### Equality notion used by Phase-1
Phase-1 equality is *equality of normal forms*:

- `EqNF x y : Prop := normalizeWF x = normalizeWF y`
- Notation: `x ≈ y`

So **every theorem is a statement about `normalizeWF` producing the same normal form**.

---

## Canon + WF Normalizer Mechanics (key notes)

### 1) `normalizeWF` is the reference normalizer
`normalizeWF` defines the Phase-1 semantics:

- **T9**: `neg (neg a)` collapses
- **T11**: `entangle a a` collapses
- **T12**: `project (entangle a b)` rewrites into a canonical sum
- **T15***: cancellation laws via BEq checks
- **⊕/⊗**: delegated to `canonPlus` / `canonTimes` on already-normalized children
- **∇**: wrapper only (`collapse` normalizes inside)

### 2) `canonPlus` / `canonTimes` provide canonicalization and distribution
`canonTimes` performs **distribution of ⊗ over ⊕** when a factor contains a plus-list,
producing a canonical sum of products (one-way distribution).

`canonPlus` performs:
- flattening nested sums
- removing `empty`
- sorting by `Expr.key`
- dedup / idempotence by key
- absorption: if `a` is present then drop products containing `a`
- optional factor-entangle step when all terms share `entangle a _`

### 3) Stability lemmas (required for bridge/idempotence)
To make “normal form” behave like a fixpoint, we rely on canon stability:

- `canonPlus_stable`: `normalizeWF (canonPlus (map normalizeWF xs)) = canonPlus (map normalizeWF xs)`
- `canonTimes_stable`: `normalizeWF (canonTimes (map normalizeWF xs)) = canonTimes (map normalizeWF xs)`

These are what let us prove `normalizeWF` is idempotent.

### 4) `normStep = normalizeWF`
Public normalizer is defined so one step is WF normalization:

- `abbrev normStep : Expr → Expr := normalizeWF`
- `normalizeFuel` iterates to a fixpoint by BEq equality
- Bridge theorems show public `normalize` agrees with `normalizeWF`

---

## Bridge Theorems (proved)

### WF invariance of a step
**wf_invariant_normStep**
- Statement: `normalizeWF (normStep e) = normalizeWF e`
- Reason: because `normStep = normalizeWF` and `normalizeWF` is idempotent.

### WF invariance under fuel iteration
**wf_invariant_normalizeFuel**
- Statement: `normalizeWF (normalizeFuel k e) = normalizeWF e`
- Reason: iterate `normStep` doesn’t change WF normal form.

### Public normalizer agrees with WF normalizer
**normalize_bridge**
- Statement: `normalizeWF (normalize e) = normalizeWF e`
- Reason: `normalize` is `normalizeFuel` with a budget, and invariance holds for any `k`.

---

## Phase-1 Theorems (proved)

Below: ✅ = proved theorem in Lean.

### Collapse / wrapper safety
✅ **CollapseWF**
- `normalizeWF (∇a) = ∇(normalizeWF a)`
- (∇ is wrapper-only; normalization happens inside.)

### Distribution / algebraic laws
✅ **T8 (distribution, one-way)**
- `EqNF (a ⊗ (b ⊕ c)) ((a ⊗ b) ⊕ (a ⊗ c))`
- Holds because `canonTimes` distributes over any plus-factor and then canonicalizes.

✅ **T10 (entangle factoring via canonPlus)**
- `EqNF ((a↔b) ⊕ (a↔c)) (a↔(b⊕c))`
- Holds because `canonPlus` factors entangle when all terms share the same left `a`.

### Negation
✅ **T9 (double negation)**
- `EqNF (¬(¬a)) a`
- Built into `normalizeWF` neg-case.

### Entangle
✅ **T11 (idempotence)**
- `EqNF (a↔a) a`
- Built into `normalizeWF` entangle-case.

### Projection
✅ **T12 (projection fidelity)**
- `EqNF (★(a↔b)) ((★a) ⊕ (★b))`
- Built into `normalizeWF` project-case (uses `canonPlus` to keep RHS canonical).

### Absorption
✅ **T13 (absorption)**
- `EqNF (a ⊕ (a ⊗ b)) a`
- Holds because `canonPlus.absorb` drops any product containing a base already present.

### Factoring rule policy
ℹ️ **T14 (design note)**
- “NO RULE: factoring is excluded (one-way distribution only)”
- We intentionally do **distribution** but do not add a general reverse factoring rewrite.

### Cancellation
✅ **T15R**
- `EqNF (a ⊖ ∅) a`

✅ **T15L**
- `EqNF (∅ ⊖ a) a`

✅ **T15C**
- `EqNF (a ⊖ a) ∅`

All are direct from `normalizeWF` cancel-case with BEq branching.

---

## Operational “how to verify” commands

From:
`/workspaces/COMDEX/backend/modules/lean/workspace`

```bash
lake clean
lake build PhotonAlgebra.BridgeTheorem
lake build PhotonAlgebra.Phase1Theorems
lake build PhotonAlgebra.SnapshotGen


###TODO
✅ 1. Uniqueness/Characterization Theorem
Status: DONE ✅✅✅

uniqueness_nf proven
normalizeWF_idem proven
This was the big one - you did it!

⚠️ 2. A1-A8 Independence Proofs
Status: Still needed for Symatics

PA doesn't use A1-A8 (that's Symatics axioms)
For PA: operator independence would be nice but not essential
Priority: Medium

⚠️ 3. Comparison to Quantum Gate Algebras
Status: Needed for Symatics novelty claim

Separate from PA (PA is discrete, gates are continuous)
Priority: High for Symatics paper

⚠️ 4. Computational Advantage Demonstration
Status: Now much easier with canonicality proven

Can claim: "Equality via normalization is decidable"
Can prove: "Normalization is O(n log n)" (if true)
Priority: High for practical impactTODO