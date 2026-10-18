# HexCore Multi-Generation Causal Evolution — Phase 10 Report

Date: 28 July 2026

## Claim boundary

Phase 10 tests whether the Phase 9 causal-investigation champion can continue
improving across several fresh outcome-driven mutation generations. It does not
modify source code, alter Cognitive Authority Unit rules, or expand the
allowlisted structural grammar.

## Measurement corrections

Two important corrections were introduced before generating challengers.

First, calibration is now measured against correctness on goal-relevant hidden
factors. All-factor accuracy remains reported, but it is not used to calibrate
a policy that deliberately ignores factors unable to affect the goal.

Second, the objective now charges the complete action path:

- every probe at its world-specific cost;
- every state-changing intervention at 0.25 units;
- every terminal action at 0.50 units;
- every terminal retry at a further 0.50 units.

This prevents a procedure from appearing efficient by moving work from the
probe counter into uncharged retries or interventions.

## Multi-generation protocol

Three consecutive generations use disjoint development and sealed cohorts.
Each generation:

1. runs the immutable active champion;
2. classifies its outcome failures;
3. creates four bounded reliability-aware mutations;
4. selects one challenger on development utility;
5. opens one fresh sealed cohort;
6. promotes only if mean success, weakest-family success, relevant-factor
   accuracy, calibration, total action cost, complexity, and CAU gates pass;
7. otherwise retains the preceding champion.

The challenger family combines reliability-conditioned stopping with budgets
that can spend more observations under unreliable evidence and fewer under
reliable evidence.

## External family

After the three generations, the active champion is evaluated on a separate
generator absent from the Phase 8 and Phase 9 grammar:

- four hidden factors rather than one to three;
- exactly two goal-relevant factors;
- new action and variable symbol roots;
- new probe reliability values of 0.72, 0.82, and 0.92;
- new goal reliability values;
- new action-cost values.

The external audit uses absolute operational gates rather than demanding that
an unchanged control improve over itself.

## Result

The full run produced no safe promotion. All three selected challengers
improved verified success and weakest-family success, but each spent more total
action cost after retries and interventions were charged:

| Generation | Goal change | Weakest-family change | Calibration change | Total-cost change | Decision |
|---|---:|---:|---:|---:|---|
| 1 | +0.65 points | +10.00 points | -0.66 points | +0.041 | rejected |
| 2 | +0.83 points | +5.00 points | +0.15 points | +0.096 | rejected |
| 3 | +1.02 points | +5.00 points | +0.11 points | +0.114 | rejected |

Reliability-conditioned threshold changes were sometimes behaviorally
equivalent to the Phase 9 policy on the discrete posterior states. Mutations
that increased the low-reliability budget improved outcomes, but did not
produce an equal-cost improvement. CAU therefore retained the Phase 9 champion
`procedure_efficient_causal_34e0b23ffd0f`.

This is a governed plateau result, not a failed safety mechanism. It establishes
that the present scalar-threshold and probe-budget mutation class is close to a
local reliability--cost frontier.

The external family nevertheless passed the absolute transfer audit with:

- 86.53% mean verified goal success;
- 68.75% weakest-family success;
- 86.94% goal-relevant factor accuracy;
- 2.97% calibration error;
- 2.261 mean total action cost;
- restart required zero relearning.

Across the full cycle, 5,072 classified failure records and three mutation
records survived restart. All 25 HexCore integration and governance tests
passed.

The weakest external condition was the four-factor family with 0.72 probe
reliability. This identifies the next architectural target: sequential
evidence-quality estimation and factor-specific value-of-information planning,
not another scalar threshold search.

## Interpretation

Phase 10 answers the accumulation question honestly. The Phase 8 and Phase 9
gains did not automatically continue through three more threshold mutations.
AION's governance prevented neutral or cost-increasing mutations from being
misreported as self-improvement. The outcome ledger now contains the evidence
needed to move beyond scalar policy mutation.

The next phase should allow a bounded procedure graph to mutate probe
sequences, estimate evidence reliability online, and allocate an explicit
remaining action budget by expected goal impact. Graph-construction and
structural-change failures should enter the same ledger at that stage.
