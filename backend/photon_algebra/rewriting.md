# Photon Algebra Rewriting: Termination and Canonicalization

This document explains **why** `backend.photon_algebra.rewriter.normalize(e)` terminates and **why** it produces a stable, canonical normal form under a directed strategy.

The goal is not “all possible rewrites from all directions”, but a **single normalization algorithm** that:

- always terminates,
- is idempotent (`normalize(normalize(e)) == normalize(e)`),
- and yields a canonical *sum-of-products* shape.

---

## 1) What normalize() is trying to compute

Photon expressions are represented as an AST (JSON-like) using operators such as:

- `⊕` (sum / superposition union-like)
- `⊗` (product / entanglement conjunction-like)
- `¬`, `★`, `↔`, `⊖`, `∇` (other structural/runtime-adjacent ops)

The normal form targeted by `normalize()` is a **canonical sum-of-products**:

- `⊕` is flattened, `∅` removed, duplicates removed, deterministically ordered, and **absorption-reduced**
- `⊗` is deterministically ordered, annihilator-reduced, locally idempotent, and **distributes over `⊕` in one direction only**
- **No `⊕` appears directly under `⊗` in normal form**

That last bullet (“no `⊕` under `⊗`”) is the key termination guardrail.

---

## 2) Directed strategy: distribute only in the ⊗ branch

The main “dangerous” algebraic interaction is distributivity / factorization:

- Expansion (distribution):  
  `a ⊗ (b ⊕ c)  →  (a ⊗ b) ⊕ (a ⊗ c)`

- Factoring (dual distributivity, sometimes called T14 factoring):  
  `a ⊕ (b ⊗ c)  ↛  (a ⊕ b) ⊗ (a ⊕ c)`

If you allow **both** directions (expand and factor), you get classic rewrite ping-pong:

- Expand creates larger sums-of-products.
- Factoring tries to rebuild products-of-sums.
- Then expansion fires again, etc.

### Photon rule: one-way distributivity only

Photon normalization chooses a single direction:

> **We expand products over sums, but never factor sums into products.**

Concretely:

- `normalize()` performs distribution **only inside the `⊗` case**
- The `⊕` case explicitly **does not** apply T14 factoring
- The algorithm is structured so that once distribution has happened, it is not undone

This is why `normalize()` is terminating in practice, and why the normal form is stable.

---

## 3) Termination measure: bad(e)

We formalize termination by defining a **well-founded measure** that strictly decreases over the steps that could otherwise loop.

### 3.1 Define “bad nodes”

The normalization invariant is:

> After normalization, no `⊕` node may appear directly under a `⊗` node.

So define the “badness” of an expression as the number of direct violations:

**Definition (bad(e)).**  
`bad(e)` is the number of edges in the AST of `e` where a `⊗` node has a direct child with operator `⊕`.

Equivalently:

- traverse all nodes,
- for each node `n` with op `⊗`,
- for each direct child `c` of `n`,
- if `c.op == ⊕`, count 1.

This measure is:

- **non-negative integer**
- **finite** for finite ASTs
- therefore **well-founded** under the strict ordering `>` on ℕ.

### 3.2 Why distribution decreases bad(e)

The only rewrite that targets “⊕ under ⊗” is expansion inside the `⊗` branch.

If we have a local shape:

`X = (… ⊗ (Y ⊕ Z) ⊗ …)`

then distribution replaces it with a sum of products:

`X  →  (… ⊗ Y ⊗ …) ⊕ (… ⊗ Z ⊗ …)`

Crucially:

- the `⊕` node that was a *direct child* of `⊗` is removed from that edge,
- after rewriting, the top-level becomes `⊕`,
- and each resulting `⊗` product term has `Y` or `Z` as a child instead of the `(Y ⊕ Z)` node.

So that specific “bad edge” is eliminated.

### 3.3 Why bad(e) cannot re-increase

The only way to create a “⊕ directly under ⊗” edge is to introduce a `⊕` as a direct child of `⊗`.

Photon normalization prevents this by design:

- **No factoring rule exists** that could rebuild a product-of-sums.
- The `⊕` normalization branch does not introduce new `⊗` parents above an existing `⊕`.
- Other local simplifications (`¬¬`, `⊖` cancellations, idempotence, etc.) do not introduce `⊕` under `⊗`.

Therefore:

- distribution steps strictly decrease `bad(e)` when they fire,
- no other step can increase `bad(e)`.

Since `bad(e)` is a non-negative integer, `bad(e)` can decrease only finitely many times.

That is the termination core.

---

## 4) Handling size growth: why expansion still terminates

A common concern: distribution can increase the AST size (e.g., `(a ⊕ b) ⊗ (c ⊕ d)` expands to 4 terms). Size growth is real.

Termination still holds because the termination argument does **not** rely on size decreasing. It relies on eliminating a specific forbidden pattern:

- every distribution eliminates at least one “⊕ under ⊗” violation,
- and no rule re-introduces such violations.

Even if the tree grows, the number of *direct* `⊕` children under `⊗` cannot decrease indefinitely without reaching 0.

Once `bad(e) == 0`, the expression satisfies the core shape invariant:
> no `⊕` occurs directly under any `⊗`.

At that point, distribution no longer applies, so normalization proceeds only with local reductions + canonical sorting/dedup, all of which terminate straightforwardly.

---

## 5) Termination of the remaining steps

After distribution has eliminated `bad(e)`, the remaining normalization is composed of terminating procedures:

### 5.1 Canonicalization steps
- Flattening associative nodes (`⊕`-flatten, possibly `⊗`-flatten if used)
- Removing identities (`∅`)
- Deduplication/idempotence (`a ⊕ a → a`, local `a ⊗ a → a`)
- Deterministic sorting by structural key

These are terminating because they operate by:
- traversing a finite tree,
- constructing finite lists of children,
- sorting/deduping finite lists.

### 5.2 Local simplifications
Examples:
- `¬(¬a) → a`
- `a ⊖ a → ∅`
- `a ⊖ ∅ → a`
- `∅ ⊖ a → a`

These are locally oriented reductions that do not generate larger redexes of the same kind indefinitely (and in implementation are applied in a fixed pass order), so they terminate over a finite tree.

### 5.3 Absorption is a reducer
Absorption:
- `a ⊕ (a ⊗ b) → a`
- `a ⊗ (a ⊕ b) → a` (dual absorption)

Absorption strictly reduces structure (removes terms), so it cannot loop.

---

## 6) Directed canonicalization: confluence story

### 6.1 What we claim (and what we don’t)

We are not claiming full confluence of an unconstrained rewrite system where rules may fire in arbitrary order.

Instead we claim:

> **normalize() is a deterministic canonicalization algorithm.**  
> For any input `e`, `normalize(e)` is uniquely determined (modulo deterministic ordering), and re-normalizing is a no-op.

This is enough to be “undeniable” in engineering terms because:
- every expression has a single computed normal form,
- equivalence is tested by comparing normal forms.

### 6.2 Why uniqueness holds under the algorithm

Uniqueness comes from:
1. **Directed strategy** (distribution only from `⊗`, no factoring from `⊕`)
2. **Deterministic ordering key** for commutative operators
3. **Idempotence and absorption** removing duplicates and subsumed terms consistently
4. A fixed structural pass order inside `normalize()`

Even if there exist multiple possible “micro-choices” in rewriting, `normalize()` does not expose them: it executes the same steps in the same order every time.

### 6.3 Bounded local joinability as empirical reinforcement

To strengthen the story, we include a **bounded joinability** check in tests:

- generate small expressions (size-limited),
- generate a bounded set of *one-step variants* (commute/reassociate where safe; optionally pre-distribute),
- normalize each variant and assert the same normal form.

**Important nuance (directed strategy awareness):** this is *not* a claim of full confluence for an unconstrained,
bidirectional rewrite system. It is evidence that the **directed** normalizer is stable under a reasonable set of
local “different choice / different order” perturbations.

In particular, the test intentionally **forbids ⊗ commutativity/associativity moves when they would change
distribution timing**, i.e. when any participating operand contains a `⊕`. Reassociating/commuting `⊗` across
`⊕`-containing operands can change *where/when* the normalizer’s one-way distribution fires, so those are not treated
as “equivalent one-step choices” for this directed canonicalization algorithm.

We also keep the optional “pre-distribution” probe in the **same direction** as normalization, and gate it to a
conservative safe subset (e.g., distributing an atomic factor), to avoid generating non-equivalent variants.

See: `backend/photon_algebra/tests/test_bounded_confluence.py`.

## 7) Summary

- Termination is enforced by a structural invariant: **no `⊕` directly under `⊗`.**
- Distribution occurs **only** in the `⊗` branch and is used to eliminate exactly those bad patterns.
- Factoring (T14 dual distributivity) is intentionally **not** a rewrite rule, preventing ping-pong.
- A well-founded measure `bad(e) ∈ ℕ` strictly decreases whenever distribution applies and cannot increase.
- The rest of normalization is a finite sequence of canonicalization and local reductions.
- The result is a deterministic canonical normal form suitable for equivalence checking via:
  `normalize(lhs) == normalize(rhs)`.

---

## Appendix A: Pseudocode for bad(e)

This is a conceptual definition (implementation language irrelevant):

```text
bad(e):
  if e is atom: return 0
  let count = 0
  if op(e) == "⊗":
    for child in children(e):
      if child is node and op(child) == "⊕":
        count += 1
  for child in children(e):
    count += bad(child)
  return count