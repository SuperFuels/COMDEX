# HexCore Goal-Aware Causal Efficiency Evolution — Phase 9 Report

Date: 28 July 2026

## Claim boundary

This phase is one governed efficiency-mutation cycle over bounded procedurally
generated worlds. It does not perform source-code modification, alter CAU,
invent arbitrary operators, or demonstrate unbounded recursive
self-improvement.

The immutable control was the Phase 8 high-confidence champion: 0.98 posterior
confidence, ten investigations, and 0.05 experiment-cost weight.

## Architectural improvement

Phase 8 improved reliability by probing every hidden factor to one global
confidence threshold. Phase 9 separates epistemic completeness from
goal-relevant competence.

The new controller:

1. identifies which latent factors are connected to the current goal;
2. excludes ``do not care'' factors from the stopping condition;
3. stops probing each relevant factor independently once resolved;
4. excludes already resolved or irrelevant probes from information-gain
   selection;
5. distinguishes likely execution noise from unresolved causal belief;
6. retries the terminal goal action once instead of reopening investigation;
7. retains a seven-investigation hard ceiling.

This is an important semantic distinction: AION need not know everything about
a world before acting safely. It must know the variables that can change the
verified outcome.

## Challenger cohort

Four private procedures were evaluated on twelve development worlds:

- goal-relevance filtering with the full ten-investigation budget;
- goal-aware stopping plus one execution retry and eight investigations;
- goal-aware stopping at 0.97 confidence, one retry and seven investigations;
- a lean 0.95-confidence, six-investigation efficiency control.

The governed efficiency objective rewarded verified goal success and
goal-relevant factor accuracy while penalizing experiments and calibration
error. The seven-investigation challenger won development before the sixteen
sealed worlds were opened.

## Verification correction

Observed ``open'' events are no longer sufficient for success. A goal is
counted successful only when:

- the terminal action reports success; and
- the simulator verifies that the actual hidden factors satisfy the learned
  goal pattern.

This prevents stochastic false-positive execution from being mistaken for
intelligent planning.

## Sealed results

Both procedures were evaluated on the same sixteen generated worlds and 960
episodes.

| Measure | Phase 8 champion | Efficiency challenger | Change |
|---|---:|---:|---:|
| Verified goal success | 88.33% | **90.73%** | +2.40 points |
| Goal-relevant factor accuracy | 92.08% | 91.25% | -0.83 points |
| All-factor accuracy | 89.90% | 74.27% | -15.63 points |
| Average investigations | 7.35 | **5.45** | -1.90 |
| Worst-family goal success | 75.00% | **75.83%** | +0.83 points |
| Calibration error | 2.48% | 4.23% | +1.75 points |
| Average terminal attempts | 1.00 | 1.13 | +0.13 |

The reduction in all-factor accuracy is deliberate and is not hidden: the
challenger does not spend observations resolving factors proven irrelevant to
the current goal. Goal-relevant factor accuracy remained within the
predeclared two-point protection band, while verified outcomes improved.

The small 1.75-point calibration regression remained inside the three-point
cap. The new procedure used 1.90 fewer investigations and only 0.13 additional
terminal attempts on average.

## Promotion gates

Promotion required:

- no mean verified-goal regression;
- at least one fewer investigation on average;
- no worst-family goal regression;
- no more than two points of goal-relevant factor regression;
- no more than three points of calibration regression;
- procedure complexity no greater than ten;
- experiment budget no greater than ten;
- independent CAU authorization.

Every gate passed. The promoted champion is:

`procedure_efficient_causal_34e0b23ffd0f`

Its retained policy is:

1. probe only goal-relevant unresolved factors;
2. stop at 0.97 confidence or seven investigations;
3. use 0.05 experiment-cost weight;
4. retry the terminal action once when execution appears noisy;
5. intervene toward the learned goal pattern;
6. execute and verify.

## Persistence

After restart:

- the new champion remained active;
- 1,616 classified outcome records remained available;
- the mutation-cycle record remained available;
- no generated world required relearning.

## Interpretation

Phase 8 showed that AION could improve reliability by spending more bounded
compute. Phase 9 shows that outcome memory can then discover a better
reliability--efficiency trade-off. The new champion is both more successful and
less investigative because it reasons about relevance and failure type rather
than treating every uncertainty as equally important.

## Remaining development

The next cycle should address the remaining weaknesses:

- improve calibration without restoring unnecessary probes;
- learn per-factor thresholds from reliability and decision impact;
- charge terminal retries explicitly in the total action-cost objective;
- compare against policies with equal total action cost, not probe count alone;
- fold graph-construction and structural-change failures into the mutation
  ledger;
- run multiple successive generations to determine whether improvements
  accumulate or plateau;
- open a fresh external environment family not produced by the current
  generator.

