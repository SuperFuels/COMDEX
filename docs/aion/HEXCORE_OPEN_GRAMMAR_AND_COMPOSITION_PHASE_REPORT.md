# HexCore Phases 20--21: Open-Grammar Transfer and Cognitive Composition

Date: 29 July 2026

## Executive outcome

Phases 20 and 21 extend AION from prospective cognition inside a supplied
grammar to governed transfer across opaque symbol systems and dynamic
composition of reusable cognitive skills.

Both phases passed development gates, previously unopened sealed domains,
restart tests and Cognitive Authority Unification promotion.

No language model was used to determine roles, causal structure, plans,
correctness or promotion.

## Phase 20: open-grammar hierarchical transfer

### Research question

Can one unchanged AION learner enter domains whose state names and action names
are unfamiliar, recover the relevant causal grammar, combine that grammar with
provenance-bearing operational knowledge, and solve a partially observable
hierarchical task under a resource budget?

### Environment families

Four domains were constructed with disjoint vocabularies:

- Obsidian Archive;
- Mycelial Relay;
- Polar Foundry;
- Tide Embassy.

The first two were development domains. Polar Foundry and Tide Embassy remained
sealed until the development contract passed. Domains varied in factor count,
probe reliability, goal pattern, resource names, credential names, action
names, state names and action budgets.

Each task required:

1. recovering opaque observe/intervene/terminal roles;
2. learning a multi-factor hidden causal graph;
3. retrieving verified resource and prerequisite facts;
4. acquiring a domain-specific credential;
5. investigating noisy hidden state;
6. aligning goal-relevant factors;
7. unlocking the intermediate goal;
8. delivering the terminal artifact;
9. remaining inside the action budget.

### Evidence-pruned grammar induction

The initial implementation used the prior exhaustive graph constructor. It was
stopped after 19 minutes of full-core computation and rejected. No sealed
capability result or promotion was produced.

The accepted learner first computes observable intervention signatures:

- which action changes the terminal field;
- which actions selectively affect individual signal fields;
- which actions produce no direct visible change and are therefore candidate
  latent interventions.

These signatures constrain, but do not determine, the causal graph. The
remaining compatible toggle ordering, signal-to-factor assignment and goal
pattern are evaluated by held-out likelihood.

The graph constructor was extended with optional minimum-factor and typed role
candidate constraints. The minimum factor count comes from independently
detected intervention roles; a one-factor graph remains the explicit held-out
control.

Targeted goal-discrimination experiments systematically vary inferred
intervention subsets, probe the resulting signals and test the inferred terminal
action. Correctness is still decided by observations and held-out prediction.

### Knowledge capsules

Every domain provides a verified evidence capsule containing domain-local
claims such as:

- resource action and resource field;
- credential action and credential field;
- delivery action and terminal field;
- resource capacity and yields;
- credential, unlock and delivery costs;
- prerequisite type.

The generic planner contains no domain symbol names. It retrieves role bindings
through HexCore knowledge claims and retains the supporting evidence capsule
identifiers with every plan.

### Partial observability and resources

Hidden causal factors are never exposed to the planner. Noisy probes are
repeated until the factor posterior passes the evidence gate. A rejected
development variant accepted a single probe per factor and failed on the
three-factor domain; redundant posterior-based evidence gathering replaced it.

Information gathering, intervention, credential acquisition, unlocking and
delivery all consume the same bounded resource. The planner explicitly
replenishes and allocates this resource across subgoals.

### Sealed results

The sealed evaluation contained 120 episodes across Polar Foundry and Tide
Embassy.

| Measure | Result |
|---|---:|
| Mean hierarchical goal success | 90.83% |
| Weakest-domain goal success | 88.33% |
| Flat causal-control success | 0.00% |
| Mean gain over flat control | +90.83 points |
| Minimum observation reduction versus cold contract | 59.58% |
| Minimum candidate-graph search reduction | 96.67% |
| Grammar recovery | 100% |
| Posterior calibration gate | 100% |
| Resource-budget compliance | 100% |
| Knowledge provenance completeness | 100% |

CAU promoted:

`procedure_open_grammar_hierarchy_7974380a908a`

## Phase 21: capsule-grounded goal-graph composition

### Remaining engineered assumption

Phase 20 still used one fixed order:

credential, investigate and align, unlock, deliver.

That is invalid in domains where a credential can only be created after causal
alignment. Phase 21 removes the fixed order.

### Typed skill contracts

The compositional planner exposes reusable skills as contracts:

| Skill | Preconditions | Postconditions |
|---|---|---|
| Acquire credential | constraints known; optionally aligned state | credential ready |
| Infer and align hidden state | grammar bound | aligned state |
| Unlock terminal | credential ready and aligned state | opened |
| Deliver verified artifact | opened | delivered |

The credential prerequisite is retrieved from the capsule. A forward
goal-graph planner repeatedly selects a skill whose preconditions are satisfied,
executes it, verifies its postconditions and adds those postconditions to the
available fact state. If no skill is eligible, the goal graph is explicitly
rejected as unsatisfiable.

Domain symbols remain in private bindings. The retained procedure contains only
abstract preconditions, postconditions and composition rules.

### Evaluation families

Four new symbol systems were used:

- Crystal Orchard: alignment before credential;
- Ink Weather: credential before alignment;
- Solar Crypt: sealed, alignment before credential;
- Lichen Court: sealed, credential before alignment.

The fixed-order Phase 20 procedure was the control. It succeeds in
credential-first worlds and fails frequently in alignment-first worlds.

### Sealed results

The sealed evaluation contained 120 episodes across Solar Crypt and Lichen
Court.

| Measure | Fixed order | Composed goal graph | Change |
|---|---:|---:|---:|
| Mean exact goal success | 57.50% | 95.83% | +38.33 points |
| Weakest-domain success | -- | 91.67% | -- |
| Goal-graph construction success | -- | 100% | -- |
| Capsule provenance completeness | -- | 100% | -- |
| Minimum observation reduction | -- | 59.58% | -- |
| Minimum candidate-search reduction | -- | 96.67% | -- |

The sealed planner generated opposite valid sequences:

- Solar Crypt: align, acquire credential, unlock, deliver;
- Lichen Court: acquire credential, align, unlock, deliver.

CAU promoted:

`procedure_compositional_goal_graph_444839f5eb15`

## Persistence and governance

For both phases, HexCore retained:

- verified capsules and active claims;
- contradiction and provenance records;
- domain-local grammar bindings;
- learned causal graphs;
- abstract skill contracts;
- development and sealed gates;
- promotion evidence and authority snapshots;
- champion procedures;
- restart results.

After a fresh runtime start, every domain graph, capsule, abstract composition
record and champion was present. Relearning experiments were zero.

## What this establishes

Within the tested bounded family, AION can now:

1. enter an unfamiliar symbol system;
2. reduce its hypothesis space from observed action signatures;
3. learn a hidden causal grammar;
4. retrieve explicit operational knowledge with provenance;
5. construct a dependency graph for a terminal goal;
6. assemble an appropriate sequence from reusable cognitive skills;
7. gather redundant evidence under partial observability;
8. allocate resources across information and action;
9. verify subgoal postconditions;
10. retain the abstract method separately from domain-specific bindings.

This is stronger evidence of reusable cognition than success within one supplied
action grammar.

## Boundaries

This is not unrestricted general intelligence. The following remain
engineered:

- the abstract skill vocabulary;
- binary latent factors;
- typed capsule predicates;
- simulator action interfaces;
- short dependency graphs;
- bounded resource domains;
- externally verified correctness.

The next frontier is open-ended ontology and skill invention: AION must propose
new predicates, new state abstractions and new skill contracts when the current
vocabulary cannot explain or solve a task. Those inventions must be grounded by
execution, compressed when equivalent, rejected when unnecessary, and promoted
only after cross-domain sealed transfer.

## Reproducibility artifacts

- `backend/modules/hexcore/open_grammar_hierarchical_transfer_benchmark.py`
- `backend/modules/hexcore/compositional_goal_graph_benchmark.py`
- `backend/modules/hexcore/stochastic_multilatent_discovery.py`
- `results/hexcore_open_grammar_hierarchical_transfer.json`
- `results/hexcore_compositional_goal_graph.json`
- `backend/tests/test_hexcore_persistent_learning.py`
