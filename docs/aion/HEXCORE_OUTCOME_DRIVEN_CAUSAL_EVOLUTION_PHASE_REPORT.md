# HexCore Outcome-Driven Causal Procedure Evolution — Phase 8 Report

Date: 28 July 2026

## Claim boundary

This phase implements a governed discrete procedure-mutation loop over generated
bounded causal worlds. It does not modify source code, invent new causal
operators, alter its own authority system, or perform unrestricted autonomous
self-improvement.

The Phase 7 causal procedure remains an immutable control. Private challengers
may change only three declared controls: posterior confidence threshold,
experiment budget, and experiment-cost weight. CAU, sealed evaluation,
complexity limits, rollback, and independent promotion remain mandatory.

## Procedural world stream

The generator produced disjoint development and sealed cohorts with:

- one, two, or three binary hidden factors;
- generated variable and action vocabularies;
- probe reliabilities from 75% to 95%;
- goal reliabilities from 90% to 99%;
- varied experiment costs;
- full, mixed, and ``do not care'' goal patterns;
- goal graphs connected to different subsets of hidden factors.

Twelve development worlds used forty episodes each. Sixteen sealed worlds used
sixty episodes each. There was zero world-identity overlap.

The experiment isolates procedure evolution. Each generated world supplies a
verified causal graph representing the output of the world-learning layer.
The mutation arena improves how AION investigates and plans with that graph; it
does not claim to improve graph construction in the same cycle.

## Failure taxonomy and outcome memory

Every champion episode was assigned one or more explicit outcomes:

- `belief_error`;
- `calibration_error`;
- `planning_error`;
- `execution_noise`;
- `experiment_budget_exhausted`;
- `success`.

The development champion produced:

| Failure queue | Cases |
|---|---:|
| Belief error | 81 |
| Calibration error | 27 |
| Planning error | 71 |
| Execution noise | 21 |
| Experiment budget exhausted | 305 |

These records—not sealed evaluation results—generated the challenger cohort.
After all development evaluations, 1,985 detailed failure records were retained
across the champion and challengers.

## Generated challenger policies

The Phase 7 control used a 0.95 confidence gate, six-experiment maximum and 0.10
cost weight.

Four private mutations were created:

1. **High confidence:** 0.98 confidence, ten experiments, 0.05 cost weight.
2. **Balanced robust:** 0.97 confidence, eight experiments, 0.05 cost weight.
3. **Cost aware:** 0.97 confidence, nine experiments, 0.20 cost weight.
4. **Efficiency control:** 0.90 confidence, five experiments, 0.08 cost weight.

All procedures retained the same complexity score of eight. Ten experiments
was the hard operational maximum.

## Development arena

| Policy | Factor accuracy | Goal success | Calibration error | Mean experiments | Worst-family goal |
|---|---:|---:|---:|---:|---:|
| Phase 7 champion | 83.13% | 81.25% | 5.01% | 5.10 | 40.00% |
| High confidence | **92.92%** | **89.58%** | 2.90% | 7.80 | **60.00%** |
| Balanced robust | 89.17% | 87.29% | 3.41% | 7.04 | 45.00% |
| Cost aware | 92.50% | 88.75% | **1.52%** | 7.68 | 50.00% |
| Efficiency control | 77.92% | 78.13% | 8.71% | **4.00** | 37.50% |

The high-confidence challenger achieved the best governed development score and
worst-family goal result. It was selected before the sealed cohort was opened.

## Sealed evaluation

The selected challenger and immutable champion were evaluated using identical
seeds on sixteen new worlds and 960 total episodes each.

| Measure | Champion | Challenger | Change |
|---|---:|---:|---:|
| Hidden-state accuracy | 85.31% | 93.54% | +8.23 points |
| Goal success | 86.35% | 91.67% | +5.31 points |
| Calibration error | 4.57% | 1.33% | -3.23 points |
| Mean experiments | 4.49 | 7.13 | +2.64 |
| Worst-family factor accuracy | 70.00% | 76.67% | +6.67 points |
| Worst-family goal success | 70.00% | 73.33% | +3.33 points |

The challenger used additional experiments, but converted that bounded
additional cost into statistically separated mean and worst-family capability
gains. Its ten-experiment ceiling remained within the predeclared resource cap.

## Promotion decision

Promotion required:

- at least three points of mean goal improvement;
- no worst-family goal regression;
- no mean hidden-state regression;
- no more than two points of calibration regression;
- unchanged procedure complexity;
- at most ten experiments;
- CAU authorization independent of the challenger.

Every gate passed. The promoted champion is:

`procedure_evolved_causal_30ebdb2303ae`

Its retained operational procedure is:

1. probe by expected information gain;
2. stop at 0.98 confidence or ten experiments;
3. use a 0.05 experiment-cost weight;
4. intervene toward the learned goal pattern;
5. execute and verify.

After restart, the new champion, one mutation-cycle record, and all 1,985
failure-queue records remained available with zero world relearning.

## Interpretation

This is AION's first completed outcome-driven cognitive improvement cycle:

1. generate experience;
2. run an immutable champion;
3. attribute failures;
4. generate bounded mutations from those failures;
5. select on development worlds;
6. evaluate once on disjoint sealed worlds;
7. promote only mean and worst-family improvement;
8. retain the new procedure and outcome ledger across restart.

The mechanism is AlphaZero-inspired at the level of iterative experience,
challenger competition and retained improvement. It is not AlphaZero's neural
self-play algorithm and is not ungoverned recursive self-improvement.

## Next development

The next cycle should improve efficiency rather than simply increase the probe
budget:

- learn factor-specific stopping rather than one global confidence threshold;
- allocate probes according to marginal uncertainty and goal relevance;
- distinguish execution noise from belief error before spending more probes;
- mutate experiment sequences, not only scalar thresholds;
- require equal or lower experiments at equivalent goal success;
- add graph-construction failures to the same outcome loop;
- run several mutation generations over fresh sealed cohorts;
- monitor whether gains accumulate or plateau.

