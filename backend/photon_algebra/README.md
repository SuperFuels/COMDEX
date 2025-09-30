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



README (short invariant blurb)

Normalization invariant. After normalize:
	1.	⊕ is flattened, order-canonical, ∅-free, idempotent, and absorption-reduced (if a is present, drop a⊗b).
	2.	⊗ is order-canonical and distributes over ⊕. We do not factor a ⊕ (b ⊗ c) in the ⊕ branch; doing so would ping-pong with ⊗ distribution.
	3.	Local collapses: a ⊖ a = ∅, a ⊖ ∅ = a, ∅ ⊖ a = a, ¬(¬a) = a, and a ⊗ a = a (to align with distributed forms like a ⊗ (a ⊕ a)).


  Sanity checklist (quick)
	•	REWRITE_RULES: T14 entry removed and commented “handled structurally.”
	•	normalize(⊗): after commutativity, apply if key(a)==key(b): return normalize(a).
	•	Tests: test_normalize_regressions.py, test_edges_and_ordering.py, and fuzz suite pass.

  README / docs snippet

Why ⊗ idempotence is in normalize() (not in REWRITE_RULES)

We deliberately implement a ⊗ a → a inside the normalize() op == "⊗" branch rather than as a general rewrite rule. Two reasons:
	1.	Termination & ping-pong control.
The ⊗ branch already distributes over ⊕. If we also had a global ⊗-idempotence rule in REWRITE_RULES, it could be triggered at non-canonical times and interact poorly with distribution and any (guarded) T14-style transformations, creating search “ping-pong”. Keeping it local and ordered (after commutativity canonicalization, before distribution) guarantees a stable reduction strategy.
	2.	Canonicalization locality.
In Photon NF, ⊗ pairs are order-canonical and should collapse only when the two operands are the same under the same keying that we use for ordering. Doing this adjacent to the commutativity step ensures we compare like with like (_string_key(a) == _string_key(b)), preventing accidental collapses that a pattern rule might catch too early or too late.

Practical effect.
Expressions like a ⊗ (a ⊕ a) normalize to a, matching the distributed/absorbed NF of (a ⊗ a) ⊕ (a ⊗ a) without adding a global rule that could over-fire.

Related invariant.
	•	We do not factor a ⊕ (b ⊗ c) in the ⊕ branch; distribution is handled structurally in the ⊗ branch to avoid ⊗↔⊕ ping-pong.
	•	Absorption is applied before any optional distributive reshaping.
	•	Post-normalize: no ⊕ directly under a ⊗.

⸻

### Normalization Invariant (No Ping-Pong)

We **do not** include a T14 factoring rule in `REWRITE_RULES`:

a ⊕ (b ⊗ c)  ↛  (a ⊕ b) ⊗ (a ⊕ c)

Reason: the `⊗` branch in `normalize()` already distributes over `⊕`. If we also factor in the `⊕` branch, we can create a rewrite **ping-pong** between ⊕-factoring and ⊗-distribution.  
Instead, `normalize()` does:

1. Normalize children + rule passes (`rewrite_fixed`),  
2. For `⊕`: flatten, drop `∅`, **absorption**, then idempotence + commutativity,  
3. For `⊗`: canonicalize order, annihilator, **dual absorption** (`a ⊗ (a ⊕ b) = a`), then distribute over `⊕`.

This guarantees termination and a stable normal form where **no `⊕` appears directly under a `⊗`** and `normalize(normalize(e)) == normalize(e)`.

5) (If you need it) One-line test command
PYTHONPATH=. pytest -q backend/photon_algebra/tests/test_edges_and_ordering.py \
                    backend/photon_algebra/tests/test_normalize_regressions.py \
                    backend/photon_algebra/tests
                    