# Phase 46 — Large Continual-Learning Arena V1

**Date:** 30 July 2026

**Status:** Procedural V1 passed and all three generations were promoted.

## Research question

Can AION accumulate verified experience across different reasoning families, use that memory to choose better procedures, preserve older competence while learning new skills, abstain on unknown operators and retain the improvement after restart?

## Arena composition

The official run contained 2,040 tasks:

| Cohort | Tasks |
|---|---:|
| Development | 1,200 |
| Sealed | 480 |
| External-source phrasing | 240 |
| Unknown-operator OOD | 120 |

Twelve executable procedure families were distributed across:

- mathematics;
- formal logic;
- evidence support and contradiction;
- causal state transitions;
- sequential and branching planning;
- numeric and Photon tool routing.

Every accepted output was checked by an executable authority. The learned router could propose a procedure, but could not accept its own proposal. Rejected or low-confidence proposals fell back to exhaustive governed search.

## Continual-learning architecture

The router learns associations between source-disjoint instruction language and verified procedures. Training occurs in three private challenger generations.

Generation 1 adds mathematics and logic. Generation 2 adds evidence and causal reasoning while replaying Generation 1. Generation 3 adds planning and tool routing while replaying all previous families.

Promotion requires:

- unchanged mean and weakest-family accuracy;
- improvement in real procedure attempts;
- at least 95% first-choice transfer on learned families;
- at least 98% backward retention;
- zero unsafe accepted proposals;
- source-disjoint sealed evaluation;
- CAU authorization.

Unknown operators have no executable compatibility contract. They must therefore abstain irrespective of router confidence.

## Generation results

| Generation | New capabilities | Cumulative training tasks | Attempt reduction | Retention floor |
|---|---|---:|---:|---:|
| 1 | Mathematics and logic | 400 | 17.72% | 100% |
| 2 | Evidence and causal reasoning | 800 | 51.42% | 100% |
| 3 | Planning and tool routing | 1,200 | 84.46% | 100% |

Every generation retained 100% mean and weakest-family outcome accuracy. No unsafe proposal was accepted.

## Final result

| Measure | Result |
|---|---:|
| Final accuracy | 100% |
| Final weakest-family accuracy | 100% |
| Final first-choice procedure accuracy | 100% |
| Final reasoning-attempt reduction | 84.46% |
| Latest-generation-only reduction | 17.49% |
| Continual-memory advantage | +66.97 points |
| Maximum measured forgetting | 0% |
| OOD safe abstention | 100% |
| OOD unsafe acceptances | 0 |
| Restart retention | 100% |

The latest-generation-only control demonstrates that the result depends on cumulative replay and retained experience, not simply the final training block.

Final promoted procedure:

`procedure_continual_arena_g3_ed42d407dc17`

## Interpretation

This is the first AION arena exceeding two thousand mixed tasks. Experience from earlier generations materially changes which reasoning procedure is attempted first on later tasks, reducing real candidate evaluation while preserving verification and safe fallback.

The result is evidence of bounded continual learning, not general intelligence.

## Boundary

All V1 tasks, language templates, solver families and executable authorities are procedurally engineered. Creative work, social judgment and broad human-authored language are absent. The arena therefore does not establish unrestricted domain-general reasoning or frontier-level intelligence.

Phase 46 V2 must introduce contamination-controlled human-authored reading, code, science and preference-evaluated creative tasks. The next numbered phase is Phase 47: integrate a stronger replaceable pretrained 500M--3B cognitive substrate behind HexCore without transferring authority to it.
