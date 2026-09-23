# HexCore Continuous World-Model Maintenance — Phases 15–16

Date: 28 July 2026

## Claim boundary

These phases remove the labelled early/late observation periods used by Phase
14. AION receives one continuous stream and must infer whether, when and for how
long its causal structure changed. The graph family remains a bounded set of
binary-factor permutations. The system does not rewrite source code, CAU or
arbitrary world-model operators.

## Phase 15 architecture

### Continuous graph posterior

At every stream block AION performs intervention-response experiments and
maintains a posterior over all bounded graph assignments. It retains the full
hypothesis distribution rather than only the current winner.

### Dual-speed causal memory

Two graph states are maintained:

- **operational graph:** may change after two consistent high-confidence
  blocks, allowing fast action;
- **durable graph:** changes only after four consistent blocks and CAU
  authorization.

This separates fast working belief from long-term causal knowledge. Temporary
or stochastic changes can affect immediate action without corrupting durable
memory.

The estimated change point is the first block at which the eventual graph
candidate began its stable run, rather than the later consolidation block.

### Stream families

The sealed generator included:

- permanent structural changes;
- recurring changes from graph A to B and back to A;
- one- or two-block temporary disturbances;
- isolated stochastic graph flickers.

No change boundaries or family labels were supplied to the learner.

## Phase 15 sealed results

Thirty-two new sealed streams, eight per family, produced:

| Measure | Result |
|---|---:|
| Durable-change recall | **100.00%** |
| False durable revisions | **0.00%** |
| Change-point mean absolute error | **0.00 blocks** |
| Operational graph accuracy | **92.97%** |
| Static-model goal success | 75.26% |
| Adaptive goal success | **92.71%** |
| Adaptive gain | **+17.45 points** |

By stream family:

| Family | Graph accuracy | Adaptive goal |
|---|---:|---:|
| Permanent change | 95.83% | 94.27% |
| Recurring change | 91.67% | 91.67% |
| Temporary disturbance | 95.83% | 94.79% |
| Stochastic flicker | 88.54% | 90.10% |

All gates passed. CAU promoted:

`procedure_continuous_world_maintenance_56d6520b131c`

The complete graph lineage, competing-hypothesis history, 32 environment-change
sessions and champion survived restart with zero relearning.

## Phase 16: adaptive diagnostic effort

The Phase 15 champion used five diagnostic trials at every stream block. Phase
16 evolved the experiment schedule:

1. run a two-trial low-cost stability monitor;
2. calculate the active graph's posterior probability;
3. if a competing graph wins or active confidence falls below 0.80, add five
   diagnostic trials;
4. otherwise retain the inexpensive observation;
5. keep the Phase 15 provisional and durable consolidation gates unchanged.

The selected policy therefore spends compute in response to epistemic surprise
rather than at a constant rate.

## Phase 16 sealed results

| Measure | Fixed diagnostics | Adaptive diagnostics | Change |
|---|---:|---:|---:|
| Change recall | 100.00% | **100.00%** | 0 |
| False revisions | 0.00% | **0.00%** | 0 |
| Operational graph accuracy | 92.84% | **92.84%** | 0 |
| Goal success | 93.49% | 93.36% | -0.13 points |
| Mean diagnostic actions | 4,680 | **2,748.56** | **-41.27%** |

The 0.13-point goal movement remained inside the one-point protection band.
All gates passed. CAU promoted:

`procedure_adaptive_change_diagnostics_62bd6071e44c`

## Interpretation

Phase 15 gives AION continuous, restart-persistent world-model maintenance. It
can react quickly without immediately rewriting long-term beliefs, distinguish
durable change from temporary disturbance, recognize recurring regimes and
recover exact change points.

Phase 16 adds metacognitive resource allocation: AION monitors cheaply when its
model remains predictive and increases experiment effort only when uncertainty
or contradiction justifies it. This is a direct efficiency improvement of a
previously promoted cognitive skill.

## Next development

The next major step should be anticipatory temporal abstraction:

- learn recurring regime-transition motifs and duration distributions;
- predict likely changes before a full contradiction accumulates;
- pre-activate the most probable alternate graph without prematurely
  consolidating it;
- evaluate whether anticipation reduces transition loss without creating false
  operational switches;
- propagate authorized temporal rules into skill and knowledge memory with
  provenance;
- test non-periodic, partially observable and multi-graph regime sequences.
