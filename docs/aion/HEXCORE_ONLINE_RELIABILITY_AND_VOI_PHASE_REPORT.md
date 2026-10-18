# HexCore Online Reliability and Value-of-Information Learning — Phases 11–12

Date: 28 July 2026

## Claim boundary

These phases test causal investigation when the structure of the hidden-factor
graph is supplied but the reliability of each observation channel is not. AION
does not receive the simulator's true reliability values. It must estimate
them during an episode and decide whether another observation is worth its
cost. This is not open graph discovery or unrestricted self-modification.

## Architecture

The Phase 9 goal-relevant controller was extended with:

1. a discrete posterior over possible reliability values for every probe;
2. reliability updates computed from the pre-observation causal belief, so an
   observation cannot certify itself;
3. a separate learned reliability estimate for every channel;
4. belief updates using the current channel-reliability posterior mean;
5. experiment ranking by expected information gain per action-cost unit;
6. one reserve observation for three-factor worlds identified by the failure
   ledger;
7. a value-of-information stopping rule that ends investigation when the best
   remaining probe falls below a predeclared marginal-value threshold;
8. full charging of probes, state interventions, terminal actions and retries.

True channel reliabilities in the benchmark range from 0.62 to 0.97 and may
differ inside the same world. The planner begins from an uncertain prior.

## Evaluation discipline

The development system was progressively strengthened after each independently
sealed result:

- Phase 11A rejected a repeated-reading agreement heuristic.
- Phase 11B introduced the corrected reliability posterior.
- Phase 11C reduced the probe ceiling.
- Phase 11D introduced a bounded three-factor reserve.
- Phase 11E introduced three immutable development folds.
- Phase 12 introduced explicit value-of-information stopping.
- Phase 12B required the cost ceiling to pass on every development fold.

Each architectural revision used new development and sealed seeds. An opened
sealed cohort was never reused to authorize promotion.

## Strongest sealed signals

| Cycle | Mean goal change | Weakest-family change | Calibration change | Cost change | Decision |
|---|---:|---:|---:|---:|---|
| 11B | +2.78 points | 0.00 points | -2.06 points | +0.281 | rejected: cost |
| 11C | +1.88 points | -1.11 points | -4.10 points | +0.194 | rejected: weakest family |
| 11E | +3.47 points | +6.67 points | -1.22 points | +0.347 | rejected: cost and absolute gate |
| 12 | +4.24 points | +6.67 points | -3.11 points | +0.268 | rejected: cost by 0.018 |
| 12B | +4.65 points | -4.17 points | -3.38 points | +0.157 | rejected: weakest family and absolute gate |

Phase 12 is the strongest balanced capability result: it raised mean verified
goal success from 79.79% to 84.03%, raised the weakest family from 61.39% to
68.06%, improved calibration, and improved channel-reliability estimation. It
missed the fixed total-cost ceiling by 0.0175 units, so CAU rejected it.

Phase 12B met the cost ceiling and produced the largest mean improvement, but
the weakest family regressed. It was also rejected.

## Interpretation

Online evidence-quality learning is a real capability advance. Across multiple
fresh cohorts it repeatedly improves mean goal success, relevant-factor
accuracy, calibration, and effective-intelligence utility. Value-of-information
stopping converts much of that gain into a near-equal-cost procedure.

It is not yet reproducibly safe across every distribution. The remaining
bottleneck is no longer whether AION can learn sensor trustworthiness. It is
whether a single policy can preserve the hardest family while exploiting the
learned reliability signal elsewhere.

No challenger was promoted. The retained champion remains:

`procedure_efficient_causal_34e0b23ffd0f`

All failure ledgers, mutation records and the champion survive restart with
zero relearning.

## Next architecture

The next step should replace a single global stopping rule with a governed
worst-group policy bank:

- a low-reliability multi-factor investigator;
- a normal-reliability efficiency investigator;
- a confidence-and-agreement router trained only on development folds;
- a fallback to the Phase 9 champion on router uncertainty;
- source-family-disjoint sealed evaluation;
- promotion only when both mean and weakest-family gates pass.

Graph-construction and structural-change failures should then be incorporated
as separate specialist queues rather than mixed into the sensor-reliability
learner.
