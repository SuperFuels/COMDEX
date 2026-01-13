# Photon Algebra Runtime (PA-runtime)

This document describes **PA-runtime**: evaluation/sampling/scoring behaviors that are **not** pure rewriting.

**PA-core** (AST + `rewriter.normalize`) is symbolic and terminating.  
**PA-runtime** interprets (or executes) certain nodes (e.g., `∇`, `★`) using external signals such as SQI, numeric amplitude extensions, or domain-specific evaluators.

> **Key separation:** PA-core normalization never performs measurement/sampling.  
> Runtime behaviors do **not** affect termination/confluence arguments for the normalizer.

---

## 1) Core vs runtime responsibilities

### PA-core (normative)
- JSON-like AST for expressions
- Directed normal form computation:
  - canonical *sum-of-products* shape
  - deterministic ordering and dedup
  - distribution only in the `⊗` branch
  - no factoring in the `⊕` branch
- Proof obligations:
  - termination (e.g., `bad(e)` measure)
  - idempotence (`normalize(normalize(e)) == normalize(e)`)
  - stability under the directed strategy

### PA-runtime (non-normative)
- Evaluation or interpretation that depends on:
  - probabilistic sampling (collapse)
  - SQI-weighted selection
  - numeric amplitudes / phases / scoring models
  - any domain-specific “Eval(·)” semantics

Runtime MAY call `normalize()` internally as a preprocessing step, but runtime evaluation is not part of the rewriter’s proof story.

---

## 2) Collapse (`∇`) and SQI sampling

### 2.1 Symbolic form (PA-core)
The collapse operator is represented structurally:

```json
{"op":"∇","state": <Expr>}
PA-core behavior:
	•	normalize() MAY normalize the child state, but keeps the outer ∇ node.
	•	No sampling occurs in PA-core.

2.2 Runtime behavior (PA-runtime)

At runtime, collapse can mean:
	•	If sqi is None: return a symbolic wrapper / unresolved collapse (no sampling).
	•	If sqi is provided: perform a probabilistic selection among branches of a superposition.

Typical intent:
	•	For ∇(a ⊕ b ⊕ c), interpret as “choose one branch” with weights derived from SQI.

Important: collapse semantics are intentionally excluded from PA-core equivalence and normal-form proofs, because sampling is non-deterministic unless SQI is fixed and deterministic.

⸻

3) Scoring / projection (★)

3.1 Symbolic form (PA-core)

★ is represented as:

{"op":"★","state": <Expr>}
PA-core treats ★(e) as a node that can be normalized structurally (normalize child, preserve operator).

3.2 Runtime interpretation

Runtime may interpret ★(e) as:
	•	a score / measurement / projection value,
	•	a numeric evaluation of e under a model,
	•	a “fitness” or “energy” function.

If the runtime uses SQI (or other signals), that is part of PA-runtime only.

Non-goal: PA-core does not attempt to prove anything about the numeric meaning of ★; it only preserves stable structure.

⸻

4) Numeric amplitude extensions (optional runtime layer)

Some runtime implementations extend the symbolic algebra with numeric “amplitudes”, weights, or phases, e.g.:
	•	superpose(states, weights, phases)
	•	vector-like amplitude accumulation
	•	complex phases / interference-like scoring

These extensions MUST remain runtime concerns:
	•	PA-core normalization should not depend on numeric precision, randomness, or external state.
	•	If numeric terms exist in the AST, they must be treated as atoms/values for ordering and dedup (or normalized in a purely structural way).

Recommended rule:
	•	Keep numeric arithmetic out of rewriter.normalize().
	•	Normalize structure first; interpret numerics second.

⸻

5) What runtime must never do inside normalization

To keep the proof narrative clean:
	•	normalization must not read SQI
	•	normalization must not sample
	•	normalization must not call probabilistic collapse
	•	normalization must not “evaluate” ★

Normalization is allowed to:
	•	reorder commutative children deterministically
	•	distribute ⊗ over ⊕ in the single chosen direction
	•	perform local syntactic simplifications (double negation, cancellation, identity elimination, absorption)

⸻

6) Practical usage pattern

Recommended pipeline:
	1.	Build AST (core.* constructors).
	2.	Call rewriter.normalize(expr) for canonical form and equivalence checking.
	3.	If executing behavior:
	•	call runtime collapse / scoring with explicit SQI and any models.
	•	treat results as runtime outputs, not as rewrite-normal forms.

This ensures:
	•	stable equality semantics via NF
	•	clear separation of deterministic algebra vs probabilistic interpretation