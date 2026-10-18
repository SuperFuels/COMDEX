# HexCore Open Causal Graph Construction — Phase 4 Report

Date: 28 July 2026

## Claim boundary

This phase demonstrates bounded construction and revision of inspectable
Boolean causal graphs. AION receives the state-variable vocabulary, available
actions, and a complexity-limited rule grammar. It does not receive a finite
list of candidate causal graphs. This is not unrestricted open-world causal
invention.

## New capability

The world learner now:

- begins with an explicit, inadequate persistence model;
- chooses interventions using prediction disagreement, exploration value, and
  experiment cost;
- records state, action, next-state, and evidence provenance;
- explicitly emits `NONE_ADEQUATE` when the current model fails its held-out
  accuracy gate;
- constructs a new graph by bounded symbolic rule search;
- scores the graph on observations excluded from construction;
- requires a minimum held-out gain and a novel edge;
- rejects graphs above the configured complexity cap;
- submits all retained mutations through CAU;
- persists accepted graphs atomically and restores them after restart.

The expression grammar includes constants, state persistence, negation,
action-conditioned effects, Boolean relations, and action-gated
multi-variable relations. Simpler rules win ties through an explicit
complexity penalty.

## Benchmark

The audit environment exposes three observable binary state variables:
`signal`, `gate`, and `output`. Four interventions are available:
`flip_signal`, `flip_gate`, `pulse`, and `idle`. The true transition graph is
not supplied to the learner.

The initial persistence model achieved 72.9167% held-out field accuracy and
was explicitly rejected. AION constructed an eight-complexity graph containing:

- `signal(t) -> signal(t+1)` conditioned by `flip_signal`;
- `gate(t) -> gate(t+1)` conditioned by `flip_gate`;
- `signal(t), gate(t), output(t) -> output(t+1)` conditioned by `pulse`.

The constructed graph achieved 100% held-out transition-field accuracy, a
27.0833-point improvement. It also achieved 100% accuracy across an exhaustive
restart audit covering four initial states and all four actions, with zero
relearning experiments.

Active discovery used 64 experiments:

- 26 `flip_signal`;
- 25 `flip_gate`;
- 8 `pulse`;
- 5 `idle`.

All operational gates passed: inadequate-model rejection, novel-structure
construction, at least 95% held-out accuracy, at least ten points of held-out
gain, bounded complexity, CAU-governed persistence, and restart retention.

## Governance and failure handling

Model criticism and expansion decisions are retained even when a graph is
rejected. A second audit forced the maximum graph complexity below the
complexity needed by the environment. The learner correctly refused to retain
the otherwise accurate graph, proving that predictive gain cannot bypass the
complexity authority.

The persistent HexCore schema now includes causal graphs, model criticisms,
and hypothesis-expansion records. Runtime status exposes counts for all three.

## What remains

The next world-learning increments are:

1. introduce stochastic graph consequences and confidence intervals;
2. construct latent state when observable graphs remain inadequate;
3. revise a retained graph after a genuine structural change;
4. support continuous and categorical state variables;
5. test graph transfer across independently generated environments;
6. connect accepted graph rules to planning and skill challengers.

Language models remain optional candidate parsers. They do not determine
causal correctness or approve retained knowledge.

