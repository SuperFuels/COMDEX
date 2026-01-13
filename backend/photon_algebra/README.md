Photon Algebra: Core vs Runtime

This package is intentionally split into two layers:
	•	PA-core (AST + rewriting / normalization)
Builds Photon expressions as a JSON-like AST and computes a directed, terminating normal form.
	•	PA-runtime (evaluation / sampling / scoring)
Implements behaviors that are not pure rewriting (e.g., probabilistic collapse using SQI, numeric amplitude extensions, domain-specific “Eval(·)” interpretations).

Keep this distinction in mind: the rewriter never performs measurement/sampling. It only rewrites structure.

Symbol note (∇)
In PA-core, ∇ is the collapse operator (an AST node with {"op": "∇", "state": ...}).
In some PAEV test files, ∇ also appears in comments/strings as the math gradient/divergence symbol (e.g., ∇2, |∇ψ|, ∇*J). Those are not Photon AST operators.

Normalization invariants (Photon rewriter)

backend.photon_algebra.rewriter.normalize(expr) computes a directed, terminating normal form intended to be stable under re-normalization:

normalize(normalize(e)) == normalize(e)

Normal form shape: canonical sum-of-products

After normalization, expressions are in a canonical “sum of products” shape:

⊕ (sum)
	•	Flattened: no ⊕ node appears directly under ⊕
	•	Identity removed: ∅ is dropped from sums
	•	Idempotent: duplicates removed
	•	Commutative: deterministically ordered by structural key
	•	Absorption-reduced: if a is present in a sum, drop any a ⊗ b term in that same sum
(e.g., a ⊕ (a ⊗ b) → a)

⊗ (product)
	•	∅ is an annihilator: a ⊗ ∅ = ∅
	•	⊥ annihilates (only if your build defines ⊥): a ⊗ ⊥ = ⊥
	•	Locally idempotent: a ⊗ a = a (performed inside the ⊗ normalize branch)
	•	Commutative: deterministically ordered by structural key
	•	Distributes over ⊕ (one-way):
a ⊗ (b ⊕ c) → (a ⊗ b) ⊕ (a ⊗ c)

Key invariant: no ⊕ directly under ⊗

Normalization enforces that, in normal form, a ⊗ node never has a direct child that is ⊕.

Distribution is performed only from the ⊗ branch. This prevents ⊗↔⊕ rewrite ping-pong and ensures termination.

Why T14 factoring is not a rewrite rule

We intentionally do not include dual distributivity factoring:

a ⊕ (b ⊗ c)  ↛  (a ⊕ b) ⊗ (a ⊕ c)

Reason: the normalizer already distributes ⊗ over ⊕. If we also factor in the ⊕ branch (or as a global rewrite),
we can create rewrite ping-pong between factoring and distribution. We choose a single direction:
expand products over sums, but never factor sums into products.

Local simplifications (examples)

Structural/local laws enforced during normalization:
	•	Cancellation: a ⊖ a = ∅, a ⊖ ∅ = a, ∅ ⊖ a = a
	•	Double negation: ¬(¬a) = a
	•	Idempotence: a ⊕ a = a, a ⊗ a = a

Runtime: collapse and scoring (not part of rewriter NF)

“Collapse” is defined in backend.photon_algebra.core.collapse(...) and is runtime behavior:
	•	If the input is not a superposition (op != "⊕"), collapse(x, ...) returns x unchanged.
	•	If sqi is None, it returns a symbolic wrapper (no sampling occurs):
{"op": "∇", "state": expr}
	•	If sqi is provided, it performs a probabilistic selection from the ⊕ branches using SQI-derived weights.

This runtime behavior is intentionally not part of rewriter.normalize() and is not included in the normal-form invariants.

Sanity check

PYTHONPATH=. pytest -q backend/photon_algebra/tests/test_edges_and_ordering.py \
                    backend/photon_algebra/tests/test_normalize_regressions.py \
                    backend/photon_algebra/tests