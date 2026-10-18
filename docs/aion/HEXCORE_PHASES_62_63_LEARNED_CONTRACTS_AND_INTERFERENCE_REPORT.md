# AION HexCore Phases 62–63 — Learned Skill Contracts and Repair Interference

**Date:** 30 July 2026

## Purpose

Phases 62 and 63 remove two further pieces of scaffolding from AION's
project-repair intelligence.

Phase 61 composed repairs using precondition and postcondition contracts
supplied by the benchmark. It also assumed that individually correct repairs
could be safely arranged without learning their temporal interactions.

The new capability chain is:

```text
skill execution traces
  -> candidate preconditions and effects
  -> active counterfactual experiments
  -> learned skill contracts
  -> source-disjoint composition
  -> pairwise interference experiments
  -> learned destructive and temporal effects
  -> safe partial order
  -> replanned compound procedure
  -> CAU-governed promotion and persistence
```

## Phase 62 — Learned Repair Contracts

### Hidden-contract evaluation

The four evaluator contracts from Phase 61 were withheld from the learner:

- transitive revision repair;
- independent evidence conflict resolution;
- commit-time authority refresh; and
- governed project commitment.

The learner received only structured execution traces:

```text
before facts
skill selected
structured tool output
success or failure
after facts
```

The hidden environment contracts remained available only to the execution
environment and sealed evaluator.

### Passive contract induction

For each skill, the passive learner estimated candidate preconditions as the
intersection of facts present in successful executions:

```text
candidate preconditions =
  intersection(successful before-fact sets)
```

Candidate postconditions were inferred from facts consistently added during
successful execution:

```text
candidate postconditions =
  intersection(after facts - before facts)
```

The passive traces intentionally included one correlated context fact for
every skill. Because that fact appeared in every successful example, passive
observation alone incorrectly treated it as a necessary precondition.

The passive contracts therefore contained:

```text
context_repair_revision
context_resolve_conflict
context_refresh_authority
context_commit_project
```

These false requirements prevented the passive-only planner from solving the
sealed compound projects.

### Active counterfactual contract discovery

AION treated every candidate precondition as an uncertainty. It removed one
candidate fact at a time and executed the skill in a private experiment:

```text
candidate facts - {fact}
  -> execute skill
  -> observe success or failure
```

If the skill still succeeded, the removed fact was rejected as a
precondition. If execution failed, the fact remained necessary.

Each intervention resolved one binary uncertainty and was recorded with:

- skill identity;
- removed fact;
- before and after state;
- structured tool output;
- observed success;
- inferred necessity; and
- experiment checksum.

### Learned contracts

The final learned contracts were:

```text
repair_revision:
  requires source_changed
  establishes artifacts_fresh

resolve_conflict:
  requires evidence_conflict
  establishes evidence_resolved

refresh_authority:
  requires authority_stale
  establishes authority_fresh

commit_project:
  requires artifacts_fresh,
           evidence_resolved,
           authority_fresh
  establishes safe_completion
```

All four precondition and postcondition sets exactly matched the hidden
evaluator contracts.

### Phase 62 results

| Measure | Result |
|---|---:|
| Contracts inferred | 4 |
| Exact contract recovery | 100% |
| Active counterfactual experiments | 10 |
| Experiment reduction versus exhaustive subsets | 64.29% |
| Passive-only sealed accuracy | 0% |
| Active-contract sealed accuracy | 100% |
| Sealed accuracy gain | +100 points |
| Weakest-family accuracy | 100% |
| Verified execution traces | 100% |
| Ambiguous stochastic-contract abstention | 100% |
| Unsafe side effects | 0 |

The sealed set contained 54 compound episodes across financial, scientific,
and software portfolios.

### Ambiguous-contract control

An additional skill produced contradictory outcomes from identical visible
inputs. Because no deterministic precondition/effect contract could explain
the observations, AION returned:

```text
abstain
```

It did not force a deterministic rule onto stochastic evidence.

### Phase 62 promotion

CAU promoted:

`procedure_learned_repair_contracts_79b4d663777a`

Restart reconstruction retained:

- all four learned contracts;
- all ten active experiments;
- the discovery session;
- the Phase 60 repair tools;
- the promoted champion; and
- zero contract relearning.

## Phase 63 — Learned Repair Interference and Temporal Ordering

### Motivation

Correct individual contracts do not guarantee a safe composition. A later
repair may invalidate an earlier postcondition, or a time-sensitive result may
expire while other work is performed.

Phase 63 introduced two interactions:

1. rebuilding a revised artifact changes the evidence projection and can
   invalidate an earlier conflict-resolution result; and
2. revision and conflict repair consume time, causing an early authority
   refresh to expire before commitment.

The Phase 62 contract planner did not know these interactions. Its naïve plan
was:

```text
refresh_authority
repair_revision
resolve_conflict
commit_project
```

This plan failed because the authority state expired during the subsequent
repairs.

### Temporal microenvironment

The controlled execution environment maintained:

```text
current fact set
logical clock
authority observation time
maximum authority age
skill execution trace
```

Observed effects included:

```text
repair_revision:
  adds artifacts_fresh
  may remove evidence_resolved
  advances clock by 3

resolve_conflict:
  adds evidence_resolved
  advances clock by 2

refresh_authority:
  adds authority_fresh
  records current clock
  duration 0
```

Authority freshness is lost when:

```text
current_clock - authority_observed_at
  > maximum_authority_age
```

### Active pairwise experiments

AION did not evaluate all six permutations of three repairs. It selected the
three unresolved skill pairs and executed each pair in both orders.

The experiments established:

```text
repair_revision < resolve_conflict
repair_revision < refresh_authority
resolve_conflict < refresh_authority
```

The first relation prevents a subsequent revision from invalidating a
previously resolved evidence state. The latter relations ensure authority is
refreshed after the time-consuming work.

The discovered relations form a directed acyclic graph. Topological planning
produced:

```text
repair_revision
resolve_conflict
refresh_authority
commit_project
```

### Continual interference generations

Generation 1 learned the interaction between revision repair and conflict
resolution:

```text
repair_revision < resolve_conflict
```

Generation 2 introduced authority freshness and learned:

```text
repair_revision < refresh_authority
resolve_conflict < refresh_authority
```

The Generation 1 edge was replayed and retained.

### Phase 63 sealed results

The sealed evaluation contained 60 temporal compound-project episodes across:

- financial documents;
- scientific charts and tables; and
- software architecture evidence.

| Measure | Result |
|---|---:|
| Learned ordering edges | 3 |
| Active pairwise experiments | 3 |
| Reduction versus exhaustive order tests | 50% |
| Naïve contract-plan accuracy | 0% |
| Learned interference-plan accuracy | 100% |
| Sealed accuracy gain | +100 points |
| Weakest-family accuracy | 100% |
| Generation 1 retention | 100% |
| Ambiguous interference abstention | 100% |
| Unsafe side effects | 0 |

### Stochastic-interference control

An out-of-family skill pair alternated between success and failure under the
same visible conditions and ordering. AION rejected a deterministic ordering
claim and abstained.

This prevents random outcome variation from being promoted as a causal
interference rule.

### Phase 63 promotion

CAU promoted:

`procedure_learned_repair_interference_aa6e13558060`

Restart reconstruction retained:

- all four Phase 62 contracts;
- the interference-effect model;
- all three pairwise experiments;
- both interference generations;
- the safe plan;
- the promoted champion; and
- zero experiment relearning.

## Combined significance

Phases 62 and 63 change the source of AION's project knowledge.

In Phase 61, the development system declared:

```text
when a skill applies
what the skill changes
how skills may be ordered
```

By Phase 63, AION could infer these properties through intervention:

```text
observe execution
  -> form candidate contract
  -> identify ambiguity
  -> remove one candidate condition
  -> observe whether the skill still succeeds
  -> learn preconditions and effects
  -> test repair pairs in both orders
  -> discover invalidation and expiry
  -> construct a safe partial order
```

This is a bounded form of learning how capabilities behave, not merely
learning which capability to select.

## Persistent architecture

HexCore now persists:

```text
learned_repair_contracts
contract_discovery_sessions
contract_counterfactual_experiments
repair_interference_models
repair_interference_experiments
repair_interference_generations
```

Every contract retains:

- inferred preconditions;
- inferred postconditions;
- passive support;
- active intervention records;
- confidence;
- tool lineage; and
- sealed-transfer outcome.

Every interference model retains:

- ordered skill pairs;
- added and removed facts;
- temporal duration;
- authority-expiry effects;
- generation and replay evidence;
- sealed outcomes; and
- CAU decision.

The complete HexCore history passes **68/68 tests**.

## Claim boundary

The result remains bounded:

- the fact vocabulary was engineered;
- the hidden environment contracts were finite;
- execution traces were generated under controlled conditions;
- counterfactual interventions operated on explicit symbolic facts;
- the temporal clock and skill durations were engineered;
- only three repair skills and one commitment skill were considered;
- success and interference oracles were internal;
- arbitrary natural-language skills were not evaluated;
- uncontrolled external software was not modified; and
- the evaluation was not independently administered.

The appropriate claim is that AION can infer bounded skill contracts and
temporal interference through active experiments, then use those learned
models to repair an otherwise unsafe plan.

This is not unrestricted causal program understanding, autonomous
self-modification, or AGI.

## Next development

The next stage should connect learned contracts and interference to naturally
occurring long-running projects rather than controlled symbolic facts.

AION should:

1. monitor real tool and file events over extended project sessions;
2. infer candidate state predicates from raw event traces;
3. discover which predicates determine tool applicability;
4. detect when an established contract changes after a tool or environment
   update;
5. select targeted diagnostic executions under real cost constraints;
6. revise or retire obsolete contracts;
7. consolidate stable contract and interference predictions into a neural
   proposal model without transferring authority;
8. preserve full symbolic verification and rollback;
9. test transfer to externally authored projects; and
10. submit final results through the frozen blind external-evaluation
    protocol.

This would move AION from learning within an explicit fact vocabulary toward
constructing the state abstractions needed to understand unfamiliar tools and
project environments.
