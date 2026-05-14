# Photon Algebra — Core Spec (PA-core)

This document specifies the **PA-core** layer of Photon Algebra: the **AST**, operator constructors, and the **directed normalizer** (`rewriter.normalize`) that produces a stable normal form.

PA-core is intentionally **symbolic**: it defines syntax + algebraic normalization for expressions. Runtime evaluation (sampling, amplitudes, SQI-weighted collapse, etc.) is handled elsewhere and is out of scope except where it intersects the AST (notably `∇` and `★`).

---

## 1. Scope and goals

PA-core MUST provide:

- A JSON-serializable AST for expressions over the Photon operators.
- Deterministic, terminating normalization to a canonical **sum-of-products** form.
- Stable idempotence: `normalize(normalize(e)) == normalize(e)`.

PA-core SHOULD provide:

- A single, shared ordering/keying function used for commutativity + dedup.
- A small rewrite set that is **directed** (no ping-pong between dual rules).

PA-core does **not** attempt to be a complete equational theorem prover. Instead, it provides a reliable normal form and a test suite that checks theorems as *normal-form equivalences*.

---

## 2. AST and JSON schema

### 2.1. Node types

An expression (`Expr`) is one of:

- **Atom**: a JSON string (e.g. `"a"`, `"ψ"`, `"foo/bar"`).
- **Operator node**: a JSON object with an `"op"` field and operator-specific payload.

Canonical empty/identity is `∅` (represented as a distinguished atom or object constant in code; see §2.3).

### 2.2. Operator node shape

Operator nodes are dictionaries with:

- `"op"`: required string (one of the operator symbols below)
- `"states"`: array payload for binary/n-ary operators
- `"state"`: unary payload for unary operators

Common shapes:

```json
{"op": "⊕", "states": [<Expr>, <Expr>, ...]}
{"op": "⊗", "states": [<Expr>, <Expr>, ...]}
{"op": "↔", "states": [<Expr>, <Expr>]}
{"op": "⊖", "states": [<Expr>, <Expr>]}
{"op": "¬", "state": <Expr>}
{"op": "★", "state": <Expr>}
{"op": "∇", "state": <Expr>}
```

### 2.3. Constants

PA-core uses these constants:

- `∅` : empty / identity of `⊕`, annihilator for `⊗` (see normalization laws)
- `⊤` : top (may appear in boolean conversion utilities)
- `⊥` : bottom (optional; if present, may annihilate under `⊗`)

If your codebase represents these as special atoms (e.g. `"∅"`) vs singleton objects, the **semantics remain identical**. The normalizer treats them structurally.

---

## 3. Operators (P-series core)

This section describes operator intent and AST constructors (mirroring `core.py`).

### P1. Superposition (`⊕`)

- Constructor: `superpose(*states)`
- AST: `{"op":"⊕","states":[...]}`
- Notes: `⊕` is associative/commutative/idempotent under normalization.

### P2. Projection (`★`)

- Constructor: `project(state, sqi=None)`
- AST (symbolic form): `{"op":"★","state": <Expr>}`
- Runtime: when `sqi` is provided, may return a numeric/score-like value (out of PA-core scope).

### P3. Entanglement (`↔`)

- Constructor: `entangle(a,b)`
- AST: `{"op":"↔","states":[a,b]}`

### P4. Fusion / product (`⊗`)

- Constructor: `fuse(a,b)` (sometimes called `product` / `tensor`)
- AST: `{"op":"⊗","states":[a,b]}`

### P5. Cancellation / difference (`⊖`)

- Constructor: `cancel(a,b)`
- AST: `{"op":"⊖","states":[a,b]}`
- Local law: `a ⊖ a = ∅` (enforced by construction and/or normalization).

### P6. Negation (`¬`)

- Constructor: `negate(a)`
- AST: `{"op":"¬","state":a}`
- Local law: `¬(¬a) = a` (enforced in normalization).

### P7. Collapse (`∇`)

- Constructor: `collapse(state, sqi=None)`
- AST (symbolic form): `{"op":"∇","state": <Expr>}`
- Runtime: when `sqi` is provided and `state` is a superposition, collapse may sample a branch; this is runtime behavior and is not part of the symbolic normal form.

**Important intersection with PA-core:** the normalizer treats `∇` structurally (normalize its child, then keep the node), so documentation MUST avoid implying that `∇(a ⊕ ∅)` is rewritten to `a` purely symbolically unless your theorem harness supplies deterministic SQI to force that outcome.

### P8. Boolean conversion / truthiness (utility)

Utilities may exist to map expressions to boolean values. This is outside the normal-form contract except for how constants are interpreted.

---

## 4. Normalization invariants (Photon rewriter)

`rewriter.normalize(expr)` computes a **directed, terminating** normal form intended to be stable under re-normalization.

### 4.1. Normal form shape: canonical sum-of-products

After normalization:

#### `⊕` (sum)

- Flattened (no `⊕` directly under `⊕`)
- `∅` removed (identity)
- Idempotent (duplicates removed)
- Commutative + deterministically ordered by a structural key
- Absorption-reduced: if `a` is present in a sum, drop any `a ⊗ b` term in that same sum

#### `⊗` (product)

- `∅` is an annihilator: `a ⊗ ∅ = ∅`
- Idempotent locally: `a ⊗ a = a` (performed in the `⊗` normalize branch)
- Commutative + deterministically ordered by a structural key
- Distributes over `⊕` (one-way): `a ⊗ (b ⊕ c) → (a ⊗ b) ⊕ (a ⊗ c)`

### 4.2. Key invariant: no `⊕` directly under `⊗`

Normalization enforces that, in normal form, a `⊗` node never has a direct child that is `⊕`.

Distribution is performed **only** from the `⊗` branch, which prevents `⊗↔⊕` “ping-pong” and ensures termination.

### 4.3. Why T14 factoring is not a rewrite rule

PA-core intentionally does **not** include the dual distributivity factoring rule:

`a ⊕ (b ⊗ c)  ↛  (a ⊕ b) ⊗ (a ⊕ c)`

Reason: the normalizer already distributes `⊗` over `⊕`. If we also factor in the `⊕` branch (or as a global rewrite), we can create rewrite ping-pong between factoring and distribution.

Instead, PA-core chooses a single direction:
expand products over sums, but never factor sums into products.

### 4.4. Local collapses (examples)

These are performed as local laws (either by construction or in `normalize`):

- Cancellation: `a ⊖ a = ∅`, `a ⊖ ∅ = a`, `∅ ⊖ a = a`
- Double negation: `¬(¬a) = a`
- Idempotence: `a ⊕ a = a`, `a ⊗ a = a`

---

## 5. Theorem checking strategy (how “proofs” work in-repo)

In this repo, most “proofs” are regression-style theorems:

> A theorem `T(a,b,...)` holds if `normalize(lhs(T)) == normalize(rhs(T))`.

This style is strong for:
- rewrite soundness regressions,
- ensuring normalization invariants,
- confirming that refactors don’t change the equational theory being implemented.

It is not a substitute for a machine-checked proof assistant, but it provides a pragmatic, automated safety net.

### 5.1. Recommended theorem test categories

You generally want three layers:

1. **Axiom/constructor laws** (unit tests)
   - `superpose` flattening, identity removal
   - `cancel` self-cancel and empty-cancel rules
   - `negate` double-negation

2. **Normalizer invariants** (property tests)
   - Idempotence: `normalize(normalize(e)) == normalize(e)`
   - Shape: “no `⊕` directly under `⊗`”
   - Determinism: canonical ordering stable across permutations

3. **Algebraic theorems** (equivalence tests)
   - Distributivity direction: `a ⊗ (b ⊕ c)` expands
   - Absorption: `a ⊕ (a ⊗ b) == a`
   - Dual absorption: `a ⊗ (a ⊕ b) == a`

### 5.2. Making it “undeniable” (next proof upgrades)

If you want to move from “strong tests” to “formal confidence,” the next upgrades are:

- **Semantics model**: define an interpretation of expressions into a simple algebra (e.g., sets / boolean algebra / semiring-like model) and prove each rewrite is semantics-preserving by executable checking across many random instantiations.
- **Termination measure**: implement an explicit well-founded measure (node count + sum-of-⊗-over-⊕ depth, etc.) and test that each normalization step strictly decreases it.
- **Confluence in practice**: randomize traversal orders and show they converge to the same normal form (i.e., normalize with different evaluation orders yields identical result).

These can be done with property-based tests (Hypothesis) and are typically enough to convince a skeptical engineering audience.

---

## 6. Sanity check commands

Run the targeted normalization tests:

```bash
PYTHONPATH=. pytest -q   backend/photon_algebra/tests/test_edges_and_ordering.py   backend/photon_algebra/tests/test_normalize_regressions.py   backend/photon_algebra/tests
```

---

## 7. Notes on documentation consistency (∇ vs “collapse”)

The symbol `∇` appears in two contexts:

1. **PA-core operator** `∇(expr)` (symbolic node `{"op":"∇","state":expr}`)
2. **Analytic / physics notation** in PAEV tests (e.g. `∇2`, `|∇θ|`, `∇*J`) where `∇` is a spatial gradient operator.

Docs SHOULD explicitly distinguish these to avoid confusion:
- Use “collapse operator `∇`” when referring to PA-core.
- Use “gradient `∇`” / “Laplacian `∇²`” when referring to analytic PDE notation.

