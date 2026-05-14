# Photon Algebra Theorems (T8–T15)

This document states the **derived theorems** T8–T15 for Photon Algebra and shows how they are validated in-repo.

**Important:** PA is split into two layers:

- **PA-core (rewriting / normalization):** `backend.photon_algebra.rewriter.normalize`
  - deterministic, terminating, idempotent canonicalization
  - does **not** perform sampling/measurement
- **PA-runtime (evaluation / sampling / scoring):** e.g. `core.collapse`, `★` scoring interpretations
  - may be probabilistic or domain-defined

Unless explicitly marked “runtime-conditional,” the theorems below are validated as **normal-form equivalences**:

> A theorem holds if `normalize(lhs) == normalize(rhs)`.

---

## Notation

We use AST operator symbols:

- `⊕` — sum / superposition
- `⊗` — product / fusion
- `↔` — entanglement
- `¬` — negation
- `⊖` — cancellation / difference
- `★` — projection / scoring wrapper
- `∇` — collapse wrapper (runtime)

`∅` is the empty constant.

---

## T8 — Distributivity of product over sum (directed expansion)

**Statement (core):**

\[
a ⊗ (b ⊕ c)\;\equiv\; (a ⊗ b) ⊕ (a ⊗ c)
\]

**Notes:**
- This is the *one allowed direction* of distributivity used by the normalizer to reach sum-of-products.
- Normal form forbids `⊕` directly under `⊗`, so expansion happens from the `⊗` branch.

**Validated by:**
- `backend/photon_algebra/theorems.py` (`theorem_T8`)
- `backend/photon_algebra/tests/test_theorems_extended.py` (T8)

---

## T9 — Double negation stability

**Statement (core):**

\[
¬(¬a)\;\equiv\; a
\]

**Validated by:**
- `backend/photon_algebra/theorems.py` (`theorem_T9`)
- `backend/photon_algebra/tests/test_theorems_extended.py` (T9)

---

## T10 — Entanglement distributivity over sum (factoring-like on ↔)

**Statement (core):**

\[
(a ↔ b) ⊕ (a ↔ c)\;\equiv\; a ↔ (b ⊕ c)
\]

**Notes:**
- This is not the dangerous `⊗/⊕` factoring (T14). It’s a domain theorem for `↔`.
- Normalization may implement this as a directed rewrite when the pattern matches.

**Validated by:**
- `backend/photon_algebra/theorems.py` (`theorem_T10`)
- `backend/photon_algebra/tests/test_properties_t10_and_mixed_invariant.py`
- (additional ordering/stability evidence) `backend/photon_algebra/tests/test_mixed_ops_ordering.py`

---

## T11 — Collapse wrapper consistency (runtime-conditional)

**Core-safe statement (wrapper stability):**

\[
∇(a ⊕ ∅)\;\equiv\; ∇(a)
\]

**What this means:**
- The rewriter may simplify the **child** of `∇` (e.g. remove `∅` in `⊕`) but does **not** “perform collapse.”
- `∇(x)` remains a wrapper unless runtime supplies SQI and chooses a branch.

**Not claimed (in PA-core):**
- We do **not** claim `∇(a) == a` as a rewriting theorem, because that would be a measurement step.

**Validated by:**
- `backend/photon_algebra/theorems.py` (`theorem_T11`)
- `backend/photon_algebra/tests/test_theorems_extended.py` (T11)

---

## T12 — Projection fidelity over entanglement (structural/semantic bridge)

**Statement (core-normalized shape):**

\[
★(a ↔ b)\;\equiv\; (★a) ⊕ (★b)
\]

**Notes:**
- This is written as an algebraic “fidelity” identity.
- In PA-core it is treated structurally (a rewrite/canonicalization of AST shape), not as numeric evaluation.

**Validated by:**
- `backend/photon_algebra/theorems.py` (`theorem_T12`)
- `backend/photon_algebra/tests/test_theorems_extended.py` (T12)
- `backend/photon_algebra/tests/test_mixed_ops_ordering.py` (notes + stability)

---

## T13 — Absorption

**Statement (core):**

\[
a ⊕ (a ⊗ b)\;\equiv\; a
\]

**Notes:**
- Enforced during `⊕` canonicalization to remove subsumed product terms.
- This is a key reducer that helps keep normal forms small.

**Validated by:**
- `backend/photon_algebra/theorems.py` (`theorem_T13`)
- `backend/photon_algebra/tests/test_theorems_calculus.py` (T13)
- `backend/photon_algebra/tests/test_properties_normalize.py` (absorption sanity property)

---

## T14 — Dual distributivity / factoring is NOT a rewrite rule (design theorem)

**Non-rule (intentional):**

\[
a ⊕ (b ⊗ c)\;\not\Rightarrow\; (a ⊕ b) ⊗ (a ⊕ c)
\]

**Why:**
- If both directions are allowed (expand and factor), rewrite ping-pong can occur:
  - `⊗`-side expansion creates sums-of-products
  - `⊕`-side factoring tries to rebuild products-of-sums
  - expansion fires again, etc.
- Photon normalization is a **directed strategy**: expand `⊗` over `⊕`, never factor `⊕` into `⊗`.

**In-repo evidence:**
- `backend/photon_algebra/rewriter.py` explicitly notes T14 is excluded from the rewrite table
- `backend/photon_algebra/tests/test_normalize_regressions.py` includes “T14-shaped input” regressions to ensure termination + stable NF

---

## T15 — Falsification / cancellation identities

**Statements (core):**

\[
a ⊖ ∅ \equiv a
\]
\[
∅ ⊖ a \equiv a
\]

**Validated by:**
- `backend/photon_algebra/theorems.py` (`theorem_T15`)
- `backend/photon_algebra/tests/test_theorems_calculus.py` (T15)

---

## How these theorems are enforced and tested

### Normal-form equivalence (primary)
Most theorems are enforced as:
- a directed rewrite during normalization, and/or
- a canonicalization invariant (ordering, dedup, absorption)

And then tested as:
- `normalize(lhs) == normalize(rhs)`.

### Property reinforcement (secondary)
The property suites add “undeniable” evidence:
- idempotence
- commutativity/associativity stability
- “no `⊕` directly under `⊗`”
- bounded one-step joinability checks

See:
- `backend/photon_algebra/tests/test_properties_normalize.py`
- `backend/photon_algebra/tests/test_bounded_confluence.py`