# HexCore Phases 17--19: Anticipation, Prospective Planning and Plan Repair

Date: 28 July 2026

## Outcome

Three governed capabilities were implemented and evaluated on fresh,
procedurally generated causal worlds without using a language model:

1. learned temporal motifs and anticipated regime changes;
2. prospective selection of delayed actions against predicted future regimes;
3. bounded multi-step counterfactual planning with outcome-driven plan repair.

All three challengers passed their sealed evaluation gates, were authorized by
the Cognitive Authority Unification (CAU) path, and survived a complete runtime
restart without relearning.

## Phase 17: anticipatory temporal reasoning

### Architecture

The Phase 17 learner consumes the confirmed operational-graph lineage produced
by continuous world-model maintenance. For each active causal graph it retains:

- observed successor graph;
- observed regime duration;
- transition support count;
- duration mean and dispersion;
- the provenance of the confirmed stream.

A transition is anticipated only when the current graph has sufficient support,
the successor is unambiguous, and the learned duration distribution is stable.
Anticipation pre-activates a candidate graph but cannot switch the operational
graph by itself. A current observation must independently support the predicted
graph. Durable memory still requires the slower four-block consolidation gate.

This preserves the Phase 15 distinction between fast working belief and slow
durable knowledge while allowing a supported temporal expectation to reduce
reaction latency.

### Sealed evaluation

The sealed cohort contained 28 previously unseen worlds across periodic
two-regime, periodic three-regime, jittered-duration and non-periodic families.
The last 40 blocks of each 80-block stream formed the evaluated tail.

| Measure | Reactive control | Anticipatory learner | Change |
|---|---:|---:|---:|
| Operational graph accuracy | 83.39% | 96.79% | +13.39 points |
| Goal success | 86.16% | 96.61% | +10.45 points |
| Confirmed prediction precision | -- | 100.00% | -- |
| False operational switches | -- | 0.00% | -- |

The challenger passed all mean, safety, non-periodic and complexity gates.
CAU promoted:

`procedure_anticipatory_temporal_39ad2cf55b17`

## Phase 18: prospective delayed-action planning

### Architecture

Phase 18 changes the use of the world model from ``predict what changes next''
to ``choose for the world in which the action will take effect.'' The learner:

1. constructs a probability distribution over future graphs for horizons of
   one to three blocks;
2. scores a delayed action against the predicted execution-time graph;
3. commits only above a calibrated temporal-confidence threshold;
4. falls back to the current reactive policy when duration or transition
   structure is unreliable;
5. records the prediction, decision, observed graph and outcome.

The first implementation was rejected during development because it attempted
too many predictions in non-periodic worlds. The accepted implementation added
an explicit duration-range gate as well as the variance gate. This is important:
the capability includes detecting when anticipation is unjustified.

### Sealed evaluation

The sealed cohort contained 32 unseen worlds. Actions executed one to three
blocks after selection.

| Measure | Reactive planning | Prospective planning | Change |
|---|---:|---:|---:|
| Goal success | 62.99% | 81.81% | +18.82 points |
| Prediction precision | -- | 97.92% | -- |
| Unsafe predictive commitment rate | -- | 0.56% | -- |
| Overall prediction coverage | -- | 73.40% | -- |
| Non-periodic prediction coverage | -- | 6.39% | -- |

The low non-periodic coverage is intentional abstention. It shows that the
learner used temporal predictions in learnable regimes and largely retained the
reactive fallback when temporal structure was not stable.

CAU promoted:

`procedure_prospective_temporal_70387bb93ebb`

## Phase 19: counterfactual multi-step planning and repair

### Architecture

Phase 19 introduces a bounded form of mental simulation. For each goal the
planner:

1. builds future graph scenarios from the retained temporal model;
2. enumerates action sequences, including no-op actions;
3. simulates the resulting state under each candidate sequence;
4. scores goal completion, action cost and forecast uncertainty;
5. executes only the first action of the selected plan;
6. compares the observed state transition with the predicted transition;
7. re-synthesizes the remaining plan when the observation invalidates it.

The reactive control uses the current graph for the entire imagined horizon.
Both systems receive the same initial states, goals and execution-noise draws.

An initial challenger improved mean exact success but was rejected because its
jittered-family performance regressed. The accepted design added
development-side worst-family arbitration and a more conservative temporal
confidence option. No sealed results were used to select the policy.

### Sealed evaluation

The sealed cohort contained 40 unseen worlds. The selected policy used a
three-step horizon.

| Measure | Reactive sequence control | Counterfactual planner | Change |
|---|---:|---:|---:|
| Exact goal success | 86.92% | 93.46% | +6.54 points |
| Final-state bit accuracy | 93.43% | 96.83% | +3.40 points |
| Mean actions per episode | 1.94 | 1.85 | -0.09 |
| Worst-family goal change | -- | -0.77 points | within 1-point guard |
| Recorded plan repairs | -- | 218 | -- |

The planner improved success while using slightly fewer actions. The
non-periodic family remained inside the one-point protection band rather than
being sacrificed for gains on predictable families.

CAU promoted:

`procedure_counterfactual_plan_2524af5f13ea`

## Persistent memory and authority

Each phase uses a private benchmark state and an immutable baseline procedure.
The challenger is promoted only after the unchanged sealed gate passes. Stored
records include:

- policy and complexity;
- development selection and sealed metrics;
- causal or temporal provenance;
- promotion decision and state hash;
- champion identifier;
- restart-retention result.

Predictions cannot rewrite durable world knowledge. Candidate plans cannot
approve their own promotion. A failed gate leaves the prior champion intact.

## What these results establish

Within bounded causal environments AION can now learn not only what the current
world model is, but when it is likely to change; use that expectation to choose
actions for their future execution context; simulate short sequences of
possible actions; and repair a plan when observed consequences differ from the
simulation.

This is a material expansion from reactive causal maintenance into
goal-directed prospective cognition. It is inspectable, restart-persistent and
governed.

## Boundaries

These results do not establish frontier-level general intelligence,
unrestricted future prediction, open-ended planning, or human-equivalent
understanding. Variables, action grammar, binary state representation and short
planning horizons remain bounded. The next research frontier is transfer of the
prospective planner across unfamiliar action/state grammars, longer hierarchical
goals, partial observability, resource competition and real AION knowledge
capsules.

## Reproducibility artifacts

- `backend/modules/hexcore/anticipatory_temporal_reasoning_benchmark.py`
- `backend/modules/hexcore/prospective_temporal_planning_benchmark.py`
- `backend/modules/hexcore/counterfactual_plan_repair_benchmark.py`
- `results/hexcore_anticipatory_temporal.json`
- `results/hexcore_prospective_temporal_planning.json`
- `results/hexcore_counterfactual_plan_repair.json`
- `backend/tests/test_hexcore_persistent_learning.py`
