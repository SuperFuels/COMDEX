Photon Algebra: Core vs Runtime (updated + accurate)

PA-core vs PA-runtime

This package is intentionally split into two layers:
	•	PA-core (AST + normalization)
Builds Photon expressions as a JSON-like AST and computes a directed, terminating canonical normal form.
This layer is purely structural: it rewrites and canonicalizes syntax. It does not sample, measure, or consult SQI.
	•	PA-runtime (evaluation / sampling / scoring)
Implements behaviors that are not pure rewriting, e.g. probabilistic collapse using SQI, numeric amplitude extensions, and any domain-specific Eval(·) semantics.

Keep this distinction in mind: the normalizer never performs measurement/sampling. It only rewrites structure.

⸻

Symbol note (∇)
	•	In PA-core, ∇ is the collapse operator as an AST node shaped like:

	{"op": "∇", "state": ...}

	•	In some PAEV test files, ∇ may also appear in comments/strings as the math gradient/divergence symbol (e.g., ∇2, |∇ψ|, ∇*J). Those are not Photon AST operators.

⸻

Normalization invariants (PA-core normalizer)

PA-core normalization computes a canonical normal form intended to be stable under re-normalization:
	•	Lean WF normalizer (reference): normalizeWF : Expr → Expr
	•	Fuel normalizer (computational wrapper): normalize : Expr → Expr defined via normalizeFuel

Core stability property (proved as part of Canonicality/Idempotence):
	•	normalizeWF (normalizeWF e) = normalizeWF e

Practical/bridge statement:
	•	normalizeWF (normalize e) = normalizeWF e (bridge theorem)

This stability is achieved by enforcing a single orientation for expansion (distribution from ⊗ over ⊕) and by canonical sorting/deduplication by structural key.

⸻

Normal form shape: canonical sum-of-products

After normalization, expressions are in a canonical “sum of products” shape.

⊕ (sum)

In normal form, sums are:
	•	Flattened: no ⊕ node appears directly under ⊕
	•	Identity removed: ∅ is dropped from sums
	•	Idempotent: duplicates removed (a ⊕ a = a)
	•	Commutative (canonical order): deterministically ordered by structural key
	•	Absorption-reduced: if a appears in a sum, drop any product term containing a as a factor
(a ⊕ (a ⊗ b) → a)

Important scope correction:
PA-core (Lean AST) does not include ⊤ or ⊥, so “absorbing top / duality” is not a Phase-1 invariant in the current formal system.

⊗ (product)

In normal form, products are:
	•	Flattened: no ⊗ node appears directly under ⊗
	•	Annihilator: a ⊗ ∅ = ∅ (via canonical product handling)
	•	Idempotent: duplicates removed (a ⊗ a = a)
	•	Commutative (canonical order): deterministically ordered by structural key
	•	Distributes over ⊕ (one-way):
a ⊗ (b ⊕ c) → (a ⊗ b) ⊕ (a ⊗ c)

Key invariant: no ⊕ directly under ⊗

Normalization enforces that in normal form, a ⊗ node never has a direct child that is ⊕.

Distribution is performed only from the ⊗ branch. This prevents ⊗↔⊕ rewrite ping-pong and supports termination.

⸻

Why T14 factoring is not a rewrite rule

We intentionally do not include dual distributivity factoring:
	•	a ⊕ (b ⊗ c)  ↛  (a ⊕ b) ⊗ (a ⊕ c)

Reason: the normalizer already distributes ⊗ over ⊕. If we also factor in the ⊕ branch (or as a global rewrite), we can create ping-pong between factoring and distribution.

We choose a single direction:
	•	expand products over sums
	•	never factor sums into products

⸻

Local simplifications enforced during normalization (PA-core)

These are the Phase-1 structural laws that are part of PA-core rewriting/normalization:

Difference / cancellation (⊖)
	•	a ⊖ a = ∅  (T15C)
	•	a ⊖ ∅ = a  (T15R)
	•	∅ ⊖ a = a  (T15L)

Double negation (¬)
	•	¬(¬a) = a  (T9)

Entanglement (↔)
	•	a ↔ a = a  (T11)
	•	Factoring behavior in sums when applicable (your Phase-1 T10 form):
(a↔b) ⊕ (a↔c)  ≈  a↔(b⊕c)

Projection fidelity (★)
	•	★(a ↔ b)  ≈  (★a) ⊕ (★b)  (T12)

Sum/Product canonicalization laws (canon layer)
	•	Flattening, drop identities, sort-by-key, dedup/idempotence
	•	Absorption reduction for sums
	•	One-way distribution (implemented in canonical product handling)

⸻

What is not part of PA-core Phase-1 (in the current Lean system)

These items appear in some broader docs or Python branches in other stacks, but they are not in the Lean PA-core AST and therefore must not be stated as Phase-1 invariants unless you add them as constructors + prove them:
	•	Truth constants ⊤ / ⊥
	•	Meta-ops such as ≈ / ⊂
	•	De Morgan laws and boolean-style duality laws
	•	Any ★ rules beyond the proved algebraic law above (e.g. roundtrip stabilizers), unless you explicitly include and prove them

⸻

Runtime: collapse and scoring (not part of normal-form invariants)

“Collapse” is runtime behavior (not part of PA-core normalization):
	•	If sqi is None, collapse returns a symbolic wrapper (no sampling occurs):
{"op":"∇","state": expr}
	•	If sqi is provided, it performs probabilistic selection from ⊕ branches using SQI-derived weights.

This runtime behavior is intentionally not part of normal-form invariants.

⸻

Formal completeness (what you can now claim)

With the current Lean results:
	•	Phase-1 laws (T8–T13, T15 family, plus CollapseWF and Bridge) are proved as Lean theorems
	•	Canonicality tier is proved, including:
	•	normalizeWF_idem
	•	stability lemmas for canonicalization
	•	uniqueness/characterization theorem (uniqueness_nf)

So the correct “world-facing” claim is:
	•	PA-core defines a canonical normal form and proves uniqueness in Lean; therefore EqNF is well-defined and equality is decidable by normalization.

A separate (optional) claim is Python↔Lean correspondence, which is not implied unless you add a proof/bridge between implementations.

⸻

Sanity check (Lean build + snapshot)

From /workspaces/COMDEX/backend/modules/lean/workspace:

lake clean
lake build PhotonAlgebra.Canonicality
lake build PhotonAlgebra.Phase1Theorems
lake build PhotonAlgebra.SnapshotGen

Optional “no axioms/sorries” check:

grep -R --line-number -E '\baxiom\b|\bsorry\b' \
  /workspaces/COMDEX/backend/photon_algebra/PhotonAlgebra

Scope for “absolute” proofs (updated)

When we say “absolute / undeniable” for Phase-1, we mean:
	•	The PA-core normal form function is fully specified (AST → AST), and
	•	Every structural transformation it performs is proved in Lean, and
	•	Anything not in the Phase-1 AST or theorem set is explicitly out-of-scope.

Phase-1 (must be covered by Lean proofs)
	•	⊕ / ⊗ canonicalization: flattening, identity removal, ordering, idempotence, absorption
	•	One-way distribution and invariant “no ⊕ directly under ⊗”
	•	⊖ laws: T15R/T15L/T15C
	•	¬ double negation: T9
	•	↔ rules: T10/T11
	•	★ projection fidelity: T12
	•	Published T-laws as EqNF statements

Phase-2 / meta layer (optional; must be labeled if included)
	•	⊤ / ⊥ semantics
	•	≈ and ⊂ meta-ops
	•	De Morgan / boolean duality laws
	•	Extra ★ roundtrip stabilizers not part of published algebra

Runtime is never Phase-1

Anything dependent on SQI, randomness, sampling, or evaluation is PA-runtime.

⸻

NOTES>>

You only need those Phase-2/meta items if you want to publicly claim any of the following:
	•	“Photon Algebra includes truth constants ⊤/⊥ and satisfies duality / De Morgan laws”
	•	“Photon Algebra has meta-operators ≈ or ⊂ with algebraic simplification rules”
	•	“★ has extra stabilization heuristics as part of the formal algebra”
	•	“My Lean PA-core fully matches a richer Python/Runtime feature set that uses those operators”

What you can ship as complete today

You can ship and say (truthfully, strongly):
	•	PA-core Phase-1 is formally complete for the current operator set:
∅, ⊕, ⊗, ⊖, ¬, ↔, ★, ∇
	•	You have:
	•	Phase-1 EqNF law set (T8–T13, T15 family, CollapseWF, bridge)
	•	Canonicality + Idempotence
	•	Uniqueness/characterization theorem
	•	Therefore:
	•	canonical equality is decidable by normalization
	•	the published Phase-1 laws are “undeniable” (Lean-checked)

That is already enough to convince people it’s “real and complete” as a core algebra.

When to do Phase-2/meta (⊤/⊥, ≈/⊂, De Morgan, extra ★)

Do it later if one of these becomes your goal:
	1.	You want a logic-like layer (truth constants, negation laws, De Morgan, duality).
	2.	You want meta-query operators (≈, ⊂) inside the same formal system.
	3.	You want to formally bless extra ★ heuristics as algebraic laws (not just implementation tricks).
	4.	You want full equivalence with a broader Python runtime that already uses those concepts.

What you should do right now instead (small, high impact)
	•	In docs and snapshot: clearly label Phase-2/meta as out of scope for Phase-1.
	•	If your Python runtime mentions ⊤/⊥ or ≈/⊂ anywhere, label that as PA-runtime / Phase-2, not PA-core.

If your public messaging is “Photon Algebra Phase-1 core is complete,” you’re good to ship as is.