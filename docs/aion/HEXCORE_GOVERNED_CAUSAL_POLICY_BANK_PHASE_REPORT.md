# HexCore Governed Causal Policy Bank — Phase 13 Report

Date: 28 July 2026

## Claim boundary

Phase 13 stabilizes the online evidence-quality capability demonstrated in
Phases 11 and 12. It routes among three allowlisted causal-investigation
procedures. The router cannot modify specialists, source code, causal grammar,
or Cognitive Authority Unit policy.

## Policy bank

The bank contains:

1. `conservative_evidence`: a ten-observation, low value-of-information
   threshold specialist for multi-factor, uncertain, or low-reliability
   conditions;
2. `efficient_evidence`: an eight-observation specialist with a stronger
   value-of-information stopping rule for reliable, low-entropy conditions;
3. `phase9_fallback`: the retained seven-observation Phase 9 behavior using
   the fixed reliability prior whenever routing evidence is incomplete or
   ambiguous.

Router inputs are restricted to information available during the episode:

- factor count;
- estimated channel reliabilities;
- goal-relevant belief entropy;
- relevant observation count;
- remaining investigation budget.

Every route decision is recorded.

## Evaluation contract

Three independent development folds were generated. A policy bank was eligible
only if every fold preserved mean success, weakest-family success and the fixed
total-cost ceiling. One eligible router was selected before the source-disjoint
sealed family was opened.

The sealed evaluation contained 28 new worlds and 1,680 paired episodes per
procedure. Promotion required:

- at least one point of mean verified-goal improvement;
- no weakest-family regression;
- total action-cost increase no greater than 0.25;
- calibration regression no greater than one point;
- positive effective-intelligence utility;
- at least 80% absolute goal success;
- bounded policy-bank complexity;
- independent CAU authorization;
- restart retention.

## Sealed results

| Measure | Phase 9 control | Governed policy bank | Change |
|---|---:|---:|---:|
| Verified goal success | 80.54% | **84.17%** | **+3.63 points** |
| Goal-relevant factor accuracy | 81.01% | **84.70%** | **+3.69 points** |
| Weakest-family success | 65.56% | **70.00%** | **+4.44 points** |
| Calibration error | 8.43% | **5.55%** | **-2.88 points** |
| Total action cost | 2.085 | 2.297 | +0.213 |
| Effective-intelligence utility | control | improved | +0.0284 |

All gates passed.

The router used:

- `conservative_evidence` in 1,340 episodes;
- `phase9_fallback` in 340 episodes;
- `efficient_evidence` in zero episodes on this sealed distribution.

The absence of efficient-specialist selections is retained as evidence rather
than hidden. This sealed cohort contained enough uncertainty that the router
correctly preferred either conservative investigation or fallback.

## Promotion

CAU promoted:

`procedure_governed_policy_bank_2d86cec8623a`

The exact champion, router decision record, mutation ledger and outcome memory
survived restart with zero world relearning.

## Interpretation

Phase 13 converts the repeated but unstable online-reliability gains into a
promotable capability. AION no longer forces one investigation strategy across
every distribution. It can recognize when evidence is difficult, spend a
bounded additional budget, and retreat to the proven procedure when routing
evidence is insufficient.

This is a genuine governed intelligence improvement: the system learned a
useful evidence-quality capability, discovered that one global policy was
unstable, assembled complementary procedures, selected among them from
observable state, and passed a source-disjoint sealed evaluation without
weakening its hardest family.

## Next development

The next stage should:

- train and validate the efficient specialist on a dedicated high-reliability
  source family so it becomes useful rather than dormant;
- add graph-construction and structural-change specialists with separate
  failure queues;
- require the router to distinguish sensor error, graph error and world change;
- run several fresh outcome-driven mutation generations starting from the
  promoted bank;
- measure whether the bank continues improving or reaches another plateau.
