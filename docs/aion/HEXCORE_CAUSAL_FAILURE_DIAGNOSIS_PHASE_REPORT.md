# HexCore Causal Failure Diagnosis and Repair — Phase 14 Report

Date: 28 July 2026

## Claim boundary

Phase 14 teaches HexCore to distinguish three bounded causes of reasoning
failure:

1. an unreliable observation source;
2. an incorrect causal graph;
3. a world whose causal structure changed over time.

The failure vocabulary and graph-permutation grammar are supplied. AION does
not modify source code, CAU rules or arbitrary graph operators.

## Cognitive diagnostic architecture

The diagnostic layer compares early and late intervention-response signatures.
For every hidden factor it:

- obtains repeated observations from each channel;
- measures within-channel disagreement;
- intervenes on one factor at a time;
- measures which visible signal changes;
- constructs an early response graph;
- constructs a late response graph;
- compares both graphs with the retained causal model.

The signatures are interpreted as:

- high repeated disagreement without a stable structural mismatch:
  `sensor_error`;
- a stable early and late mapping that disagrees with the retained graph:
  `graph_error`;
- an early mapping that agrees with the retained graph followed by a different
  late mapping: `world_change`;
- insufficient evidence: explicit fallback/abstention.

## Repair specialists

Each diagnosis invokes a separate bounded response:

- sensor error: conservative majority evidence, where three physical readings
  form one charged logical observation under a six-observation ceiling;
- graph error: construct a revised signal-to-factor mapping and validate it;
- world change: supersede the obsolete mapping with the late response graph;
- uncertainty: retain the proven Phase 13/Phase 9 fallback.

The three outcomes are written to distinct persistent failure queues.

## Evaluation

Three diagnostic configurations were compared on development worlds. One was
selected before 30 source-disjoint sealed worlds were opened:

- 10 sensor-error worlds;
- 10 wrong-graph worlds;
- 10 structural-change worlds.

Every repaired and control graph was then audited through governed planning and
verified hidden-state outcomes.

## Sealed results

| Measure | Result |
|---|---:|
| Overall diagnosis accuracy | **100.00%** |
| Weakest-mode diagnosis accuracy | **100.00%** |
| Graph repair accuracy | **100.00%** |
| Control verified goal success | 53.89% |
| Repaired verified goal success | **91.11%** |
| Goal-success improvement | **+37.22 points** |
| Weakest-mode repaired success | **75.33%** |

By failure type:

| Failure type | Diagnosis | Control goal | Repaired goal |
|---|---:|---:|---:|
| Sensor unreliability | 100.00% | 74.67% | **75.33%** |
| Incorrect causal graph | 100.00% | 43.67% | **99.00%** |
| Changed world structure | 100.00% | 43.33% | **99.00%** |

All predeclared gates passed.

## Promotion and persistence

CAU promoted:

`procedure_causal_failure_diagnosis_49800d432f47`

After restart:

- the diagnostic champion remained active;
- all three failure queues remained separate;
- 30 sealed diagnostic records remained available;
- no world required relearning.

## Interpretation

This phase adds a new kind of intelligence to AION. It no longer treats every
failed prediction as the same problem. It can determine whether to gather
better evidence, revise its internal model, or recognize that previously valid
knowledge became obsolete.

The graph-error and world-change gains are especially strong because the
unchanged policy bank cannot compensate for a systematically wrong model.
Correct diagnosis and structural repair raised both families to 99% verified
success.

Sensor improvement is deliberately modest and sits just above the absolute
gate. This remains the weakest branch and should receive further
cost--reliability optimization.

## Next development

The next phase should connect diagnostic outcomes to continuous world-model
revision:

- infer the change point rather than receiving early/late collection phases;
- retain multiple competing graph hypotheses during transition;
- measure when a repaired graph becomes stable enough to replace the old one;
- propagate graph revisions into knowledge and skill memory with provenance;
- test recurring, partially reversible and stochastic structural changes;
- run mutation cycles over diagnostic experiment design itself.
