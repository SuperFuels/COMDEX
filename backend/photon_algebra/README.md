### Normal Form Invariants (Photon Rewriter)

`normalize(expr)` returns a canonical **sum of products** under the Photon calculus:

- `⊕` (sum)
  - Flattened (`⊕` never nests directly under `⊕`)
  - Identity removed (`∅`)
  - Idempotent + commutative with deterministic ordering
  - **We do not factor T14 at this level** (`a ⊕ (b ⊗ c)` isn’t rewritten here)

- `⊗` (product)
  - Annihilator: `a ⊗ ∅ = ∅`
  - Commutative with deterministic ordering
  - Dual absorption: `a ⊗ (a ⊕ b) = a`
  - **Distribution over ⊕ happens only from the `⊗` branch (guarded)**
    - This prevents `⊗↔⊕` ping-pong and guarantees termination.
    - As a result, **no `⊕` appears directly under `⊗`** in normal form.

Other ops (`¬`, `★`, `↔`, `⊖`) are normalized for their local laws (e.g., double negation, cancellation) and then treated structurally.

> Note: T14 (dual distributivity) is not a standalone rewrite rule in `REWRITE_RULES`. It’s implemented structurally inside the `⊗` handling of `normalize()` with guards (e.g., annihilator checks, no premature expansion).


### Normalization Invariant (No ⊕ under ⊗)

To guarantee termination and a unique(ish) normal form, `normalize()` enforces:

> After normalization, no `⊕` node may appear directly under a `⊗` node.

We achieve this by:
- Doing **all** ⊗→⊕ distribution in the `⊗` branch,
- Performing **absorption** in the `⊕` branch *before* dedup/sort,
- **Not** factoring T14 in the `⊕` branch (avoids ping-pong with distribution).

As a result, expressions like `a ⊕ (a ⊗ b)` normalize to `a`, and
`a ⊗ (b ⊕ c)` normalize to `(a ⊗ b) ⊕ (a ⊗ c)`, while normalization is idempotent.