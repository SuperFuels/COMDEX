Photon Algebra: Core vs Runtime

This package is intentionally split into two layers:
	•	PA-core (AST + normalization)
Builds Photon expressions as a JSON-like AST and computes a directed, terminating canonical normal form.
This layer is purely structural: it rewrites and canonicalizes syntax. It does not sample, measure, or consult SQI.
	•	PA-runtime (evaluation / sampling / scoring)
Implements behaviors that are not pure rewriting, e.g. probabilistic collapse using SQI, numeric amplitude extensions, and any domain-specific Eval(·) semantics.

Keep this distinction in mind: the normalizer never performs measurement/sampling. It only rewrites structure.

⸻

Symbol note (∇)
	•	In PA-core, ∇ is the collapse operator: an AST node shaped like:

{"op": "∇", "state": ...}

	•	In some PAEV test files, ∇ may also appear in comments/strings as the math gradient/divergence symbol (e.g., ∇2, |∇ψ|, ∇*J). Those are not Photon AST operators.

⸻

Normalization invariants (Photon normalizer)

backend.photon_algebra.rewriter.normalize(expr) computes a canonical normal form intended to be stable under re-normalization:

normalize(normalize(e)) == normalize(e)

This stability is achieved by enforcing a single orientation for expansion (distribution from ⊗ over ⊕) and by canonical sorting/deduplication by structural key.

⸻

Normal form shape: canonical sum-of-products

After normalization, expressions are in a canonical “sum of products” shape.

⊕ (sum)

In normal form, sums are:
	•	Flattened: no ⊕ node appears directly under ⊕
	•	Identity removed: ∅ is dropped from sums
	•	Idempotent: duplicates removed (a ⊕ a = a)
	•	Commutative: deterministically ordered by structural key
	•	Absorption-reduced: if a appears in a sum, drop any product term containing a as a factor:
	•	a ⊕ (a ⊗ b) → a

Additionally, sums implement duality and absorbing top (if enabled in your build):
	•	a ⊕ ¬a → ⊤
	•	if any term is ⊤, the whole sum collapses to ⊤

⊗ (product)

In normal form, products are:
	•	Flattened: no ⊗ node appears directly under ⊗
	•	Annihilators:
	•	a ⊗ ∅ = ∅
	•	if ⊥ exists: a ⊗ ⊥ = ⊥
	•	Idempotent: duplicates removed (a ⊗ a = a)
	•	Commutative: deterministically ordered by structural key
	•	Distributes over ⊕ (one-way):
	•	a ⊗ (b ⊕ c) → (a ⊗ b) ⊕ (a ⊗ c)

Key invariant: no ⊕ directly under ⊗

Normalization enforces that in normal form, a ⊗ node never has a direct child that is ⊕.

Distribution is performed only from the ⊗ branch. This prevents ⊗↔⊕ rewrite ping-pong and ensures termination.

⸻

Why T14 factoring is not a rewrite rule

We intentionally do not include dual distributivity factoring:
	•	a ⊕ (b ⊗ c)  ↛  (a ⊕ b) ⊗ (a ⊕ c)

Reason: the normalizer already distributes ⊗ over ⊕. If we also factor in the ⊕ branch (or as a global rewrite), we can create rewrite ping-pong between factoring and distribution.

We choose a single direction:
	•	expand products over sums
	•	never factor sums into products

⸻

Local simplifications enforced during normalization

Structural/local laws enforced during normalization include:
	•	Difference / cancellation (⊖):
	•	a ⊖ a = ∅
	•	a ⊖ ∅ = a
	•	∅ ⊖ a = a
	•	Double negation:
	•	¬(¬a) = a
	•	Idempotence:
	•	a ⊕ a = a
	•	a ⊗ a = a
	•	Entanglement rules (↔):
	•	a ↔ a = a (idempotence)
	•	factoring behavior in sums when applicable (your T10 behavior)
	•	Projection fidelity (★):
	•	★(a ↔ b) → (★a) ⊕ (★b)
	•	additional ★-collapse stability rules (e.g., a ⊕ ★a ⊕ b → ★a-style collapse in the ★ path), used to keep roundtrips stable
	•	Meta-ops (≈, ⊂) (if present in your expression space):
	•	a ≈ a → ⊤
	•	a ⊂ b has “trivial true” cases (⊥ ⊂ _, _ ⊂ ⊤) and otherwise preserves structure

⸻

Runtime: collapse and scoring (not part of normal-form invariants)

“Collapse” is runtime behavior (not part of rewriter.normalize()):
	•	If the input is not a superposition (op != "⊕"), collapse returns the input unchanged.
	•	If sqi is None, it returns a symbolic wrapper (no sampling occurs):

{"op": "∇", "state": expr}

	•	If sqi is provided, it performs probabilistic selection from ⊕ branches using SQI-derived weights.

This runtime behavior is intentionally not part of normal-form invariants.

⸻

Sanity check

PYTHONPATH=. pytest -q \
  backend/photon_algebra/tests/test_edges_and_ordering.py \
  backend/photon_algebra/tests/test_normalize_regressions.py \
  backend/photon_algebra/tests

Scope for “absolute” proofs

When we say “absolute” / “undeniable” for Phase-1, we mean:
	•	The PA-core normal form function is fully specified (AST → AST) and
	•	Every structural transformation the Python normalizer performs is either:
	•	proved as a Lean theorem (preferred), or
	•	explicitly marked as out of Phase-1 scope (so it cannot be silently relied on).

Phase-1 (must be covered by Lean proofs for an “absolute” claim)

These are the rules/invariants that define the Phase-1 algebra and the canonical NF:
	•	⊕ / ⊗ canonicalization
	•	flattening, dropping identities, deterministic ordering, idempotence, absorption
	•	One-way distribution
	•	⊗ distributes over ⊕ (never factoring back)
	•	invariant: no ⊕ directly under ⊗ in NF
	•	⊖ cancellation / falsification
	•	a ⊖ a = ∅, a ⊖ ∅ = a, ∅ ⊖ a = a (your T15 family)
	•	¬ double negation
	•	¬(¬a) = a
	•	Core “law” theorems you publish as T-laws
	•	e.g. T8/T10/T11/T12/T13/T15 etc., as EqNF statements (normalizeWF x = normalizeWF y)

If any of these are not in Lean yet, then you’re still at “tested + documented”, not “absolute”.

Phase-2 / meta layer (optional, must be explicitly labeled if included)

These are valid behaviors, but they are not required to claim Phase-1 algebra completeness unless you explicitly include them in Phase-1:
	•	⊤ / ⊥ semantics (absorbing top, annihilating bottom)
If your algebra includes truth constants as first-class operators, then proving them is Phase-1; otherwise they’re Phase-2.
	•	≈ and ⊂ meta-ops
These are “meta” relations; if you use them only for tooling/queries, they’re Phase-2. If you use them as algebraic operators in proofs, they become Phase-1.
	•	De Morgan rules
If you treat ¬ as logical negation with full boolean-like behavior, include in Phase-1; otherwise keep Phase-2.
	•	★ projection / measurement-adjacent behavior
If ★ is part of Phase-1 syntax with algebraic laws (like your ★(a↔b) → ★a ⊕ ★b), then those laws must be proved for “absolute”.
Any ★ rules that exist purely to stabilize runtime roundtrips can be tagged Phase-2 unless you rely on them in published theorems.

Runtime is never Phase-1

Anything that depends on SQI, randomness, sampling, or evaluation (collapse, scoring, amplitude/numeric extensions) is PA-runtime and not part of the Phase-1 algebra proof claim.

