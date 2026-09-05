# ADR: AION Sovereign Brain Boundary v1

Status: accepted — 3 September 2026

## Decision

AION, not any model or cloud provider, is the canonical owner of customer identity, memory,
business map, policy, capability authority and execution receipts. Models, retrieval systems,
harnesses and compute targets are replaceable processors operating under declared contracts.

AION Flow encloses every intelligence graph with one AION ingress and one AION receipt boundary.
Provider output is always a proposal. An external side effect requires a capability node preceded
by policy evaluation and, when consequential, an explicit approval node. Execution and
verification remain separate stages.

## Consequences

- Removing every provider must not remove or corrupt customer state.
- A provider may return proposed structured data but may not write canonical stores directly.
- Every external route declares disclosure destination, data classification, residency and
  encryption before compilation.
- Consensus/refinement is bounded by iterations, time/cost budget and explicit exit criteria.
- Model agreement is not treated as truth; evidence and deterministic validation remain separate.
- Portable receipts store hashes and route facts, not unnecessary prompts, results or secrets.

## Migration policy

1. Existing routers and workflow engines remain operational during migration.
2. New provider adapters must pass the sovereign adapter boundary test.
3. New visual intelligence flows compile through `SovereignFlowCompiler` before entering the
   existing Workflow Capsule compiler.
4. Existing workflows are grandfathered for read-only review, then upgraded with disclosure,
   policy and verification metadata before new external writes are enabled.
5. Schema versions are additive within v1. Breaking changes require a new schema version and a
   deterministic migration that preserves the previous content hash and provenance.
6. Provider credentials are never included in Brain Export; bindings are re-authorized after import.

## Rejected alternatives

- Making AION merely the first node: this cannot verify final execution or protect learning.
- Making AION merely the final node: this permits excess context disclosure before governance.
- Giving each model its own memory: replacement would fragment or destroy customer knowledge.
- Unbounded multi-model debate: it increases cost and latency without proving correctness.
