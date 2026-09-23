# Phase 42 V2 — Open-Ended Goal Decomposition

**Date:** 30 July 2026

**Status:** Passed and promoted under the declared sealed gates.

## Research question

Can AION receive a broad objective without an ordered workflow and determine:

- the required subgoals;
- their dependency graph;
- missing information;
- approval boundaries;
- success criteria;
- task-appropriate verification;
- when ambiguity prevents safe planning?

## Architecture

Each world provides:

- a broad natural-language outcome;
- a shuffled set of available capability contracts;
- evidence and execution tools;
- local preconditions and effects;
- risk classes and verification authorities.

The planner does **not** receive the expected steps, gold dependency graph or ordered workflow.

AION:

1. identifies the requested terminal effect;
2. backchains through capability effects and preconditions;
3. creates evidence-acquisition and analysis subgoals;
4. constructs the dependency graph;
5. identifies high-risk human approval requirements;
6. assigns source, execution, counterexample, approval or artifact verification;
7. topologically orders the work;
8. asks a clarifying question when multiple final outcomes retain equal authority.

## Sealed evaluation

The official cohort contained 140 worlds: 100 sealed worlds plus 40 worlds with new external namespaces. Five project domains were represented. Every seventh world deliberately contained an unresolved choice between two authoritative final deliverables.

| Measure | Result |
|---|---:|
| Resolvable-plan accuracy | 100% |
| Weakest-domain accuracy | 100% |
| External-symbol accuracy | 100% |
| Exact dependency graphs | 100% |
| Exact information requirements | 100% |
| Exact approval boundaries | 100% |
| Complete verification strategies | 100% |
| Ambiguity clarification accuracy | 100% |
| Unsafe forced plans | 0 |
| Restart retention | 100% |

Promoted procedure:

`procedure_open_goal_decomposition_6770daf28ee2`

## What changed

Earlier goal-graph work generally exposed the action vocabulary, steps or dependency statements. Phase 42 V2 exposes only the desired outcome and available capability contracts. The workflow is constructed through backward reasoning.

This closes the bounded first version of Phase 42. It also connects directly to:

- Phase 43 tool invention when a required capability is missing;
- Phase 44 persistent execution after the graph is accepted;
- future Phase 45 multimodal evidence acquisition for information subgoals.

## Boundary

The benchmark still uses engineered effect phrases, short graph families and supplied capability contracts. It does not establish arbitrary goal interpretation, invention of completely unknown capabilities, hundreds of subgoals, unrestricted autonomy or AGI.

The next numbered phase is Phase 45 multimodal world grounding. The first build should require one decision to combine a natural document, a table, an image-derived observation and live software state, with separate provenance and verification for every modality.
