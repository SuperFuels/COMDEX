# AION HexCore Phases 60–61 — Open Repair Invention and Compound Composition

**Date:** 30 July 2026

## Purpose

Phases 60 and 61 extend the outcome-grounded project learning introduced in
Phase 59.

Phase 59 could diagnose four project failure types and select one of four
retained repairs. It could not construct a repair when none of those operators
was adequate, nor could its single-repair policy resolve several simultaneous
failures.

The new capability chain is:

```text
unresolved verified project failure
  -> recognise retained repair family is inadequate
  -> derive a typed repair contract
  -> synthesise a private program
  -> execute inside a side-effect-free sandbox
  -> discover counterexamples
  -> resynthesise
  -> verify on source-disjoint portfolios
  -> retain the repair as a skill contract
  -> compose several repairs for compound failures
  -> verify every intermediate postcondition
  -> CAU-governed promotion and persistence
```

## Phase 60 — Open Project Repair Invention

### Capability gaps

Three project failures were constructed that could not be resolved by the
Phase 59 repair vocabulary:

1. **Transitive revision propagation.** A changed source invalidates indirect
   descendants, not only directly connected artifacts.
2. **Independent evidence quorum.** Repeated evidence from the same dependent
   source must not be counted as several independent confirmations.
3. **Commit-time authority refresh.** A cached authority state can become
   obsolete between planning and commitment.

Each failure was grounded in source identities derived from real development
portfolios. The sealed cases used financial, scientific, and software
portfolios with zero source-checksum overlap.

### Repair DSL and sandbox

Candidate repairs were built inside a typed, side-effect-free project repair
DSL. The available primitives included:

```text
detect_change
direct_dependents
transitive_dependents
invalidate
rerun
raw_vote
independent_vote
require_quorum
read_cached
refresh_authority
require_fresh
verify
```

Programs could inspect only their supplied project payload and return a
structured repair result. The sandbox denied:

```text
filesystem_write
network_request
shell_execute
dynamic_eval
self_promote
```

The program could not modify CAU, promote itself, execute arbitrary Python,
access the network, or mutate repository evidence.

### Counterexample-driven synthesis

Initial demonstrations were deliberately underdetermined:

- direct and transitive dependency repair were indistinguishable on a
  one-edge graph;
- raw and independence-aware voting were indistinguishable without duplicated
  sources; and
- cached and refreshed authority were indistinguishable while the cached
  state remained fresh.

The first candidate for each family therefore represented a plausible but
incomplete shortcut. Property evaluation then exposed:

- a deeper dependency chain;
- duplicated evidence from one independence group; and
- expired cached authority.

Each counterexample was retained with the candidate program, observed result,
expected result, and payload checksum. The synthesis loop added the
counterexample to its active examples and searched again.

### Invented repairs

The final transitive revision program was:

```text
detect_change
transitive_dependents
invalidate
rerun
verify
```

The final evidence-quorum program was:

```text
independent_vote
require_quorum
verify
```

The final authority program was:

```text
refresh_authority
require_fresh
verify
```

These are new composite repair procedures. They were not members of Phase
59's supplied repair list.

### Phase 60 sealed results

| Measure | Result |
|---|---:|
| Repair families invented | 3 |
| Counterexamples generated | 3 |
| Mean sealed accuracy | 100% |
| Weakest repair/family accuracy | 100% |
| Development/sealed source overlap | 0 |
| Malicious opcodes rejected | 100% |
| Phase 59 backward retention | 100% |
| Phase 59 unsafe commitments | 0 |
| Out-of-grammar abstention | 100% |
| Unsafe side effects | 0 |

Semantic source forgery without an independent authenticity oracle was
deliberately outside the repair grammar. AION abstained instead of inventing a
false authenticity proof.

### Phase 60 promotion

CAU promoted:

`procedure_open_repair_invention_310ba8fcee06`

Restart reconstruction confirmed that all three programs, their
counterexamples, the invention session, and the champion survived with zero
tool relearning.

## Phase 61 — Compound Project Repair Composition

### Motivation

An unfamiliar real project may contain several simultaneous failure
conditions. A single repair can be individually correct and still leave the
project unsafe.

Phase 61 tested three compound modes:

```text
revision + stale authority
evidence conflict + stale authority
revision + evidence conflict + stale authority
```

The matched control could execute at most one repair before attempting
commitment. The challenger was required to construct an executable dependency
graph from retained repair contracts.

### Skill contracts

The Phase 60 programs were converted into explicit precondition/postcondition
contracts:

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

A breadth-first contract planner searches for the shortest sequence whose
postconditions establish the governed completion contract. No skill is
executed unless its preconditions are satisfied.

Every repair remains inside its own sandbox. The next skill may run only after
the previous repair's output passes an explicit postcondition check.

### Continual generations

Generation 1 learned composition across the two pairwise failure modes.

| Measure | Result |
|---|---:|
| Development accuracy | 100% |
| Weakest-family accuracy | 100% |
| Single-repair control | 0% |
| Promotable | Yes |

Generation 2 added the triple-failure condition while replaying both pairwise
families.

| Measure | Result |
|---|---:|
| Development accuracy | 100% |
| Weakest-family accuracy | 100% |
| Pairwise backward retention | 100% |
| Promotable | Yes |

### Sealed compound evaluation

The sealed evaluation contained 54 compound episodes across three unfamiliar
portfolio families:

- financial documents;
- scientific charts and tables; and
- software architecture evidence.

| Measure | Single-repair control | Composed challenger |
|---|---:|---:|
| Exact project success | 0% | **100%** |
| Weakest-family success | 0% | **100%** |
| Accuracy gain | — | **+100 points** |
| Verified intermediate traces | — | **100%** |
| Mean total plan actions | — | **3.33** |

Pairwise problems required two repairs followed by governed commitment.
Triple failures required:

```text
refresh_authority
repair_revision
resolve_conflict
commit_project
```

The order can vary where contracts are independent, but commitment remains
blocked until all three required facts are established.

### Protection and criticism

The complete Phase 59 atomic repair evaluation was rerun using the unchanged
policy:

| Protection measure | Result |
|---|---:|
| Phase 59 repair retention | 100% |
| Phase 59 unsafe commitments | 0 |
| Pairwise composition retention | 100% |
| Out-of-contract source-forgery abstention | 100% |
| Unsafe side effects | 0 |

No retained contract could establish `authentic_source` for semantic source
forgery. The authority wrapper therefore kept the completion goal closed and
required abstention.

### Phase 61 promotion

CAU promoted:

`procedure_compound_project_repair_077066167290`

Restart reconstruction retained:

- all Phase 60 repair programs;
- four compound repair contracts;
- both continual generations;
- the sealed composition session;
- the promoted champion; and
- every protected earlier capability.

No episode or repair tool was relearned after restart.

## Combined significance

The two phases establish two distinct forms of improvement:

1. **Capability creation:** AION constructs a repair program that did not
   exist in its Phase 59 repair vocabulary.
2. **Capability composition:** AION assembles independently verified repairs
   into a new procedure for a compound problem.

The complete operational chain is now:

```text
project outcome contradicts expectation
  -> diagnose known or unresolved capability gap
  -> use retained repair when sufficient
  -> otherwise synthesise a private repair program
  -> refine it using counterexamples
  -> verify transfer and retain its contract
  -> compose several contracts when failures interact
  -> verify intermediate effects
  -> commit only after every governed condition is satisfied
```

This is materially stronger than a fixed failure router. The system can add
new bounded repair procedures and reuse them compositionally.

## Persistent architecture

The HexCore persistent state now includes:

```text
invented_project_repairs
project_repair_invention_sessions
project_repair_counterexamples
compound_repair_contracts
compound_repair_generations
compound_repair_sessions
```

Every retained artifact contains its program, complexity, sandbox contract,
source lineage, sealed performance, counterexamples, generation record, and
CAU decision.

The complete HexCore history passes **66/66 tests**.

## Claim boundary

These are governed but bounded invention results:

- the repair DSL and primitive opcodes were engineered;
- the fact and skill-contract vocabulary was supplied;
- project failure payloads were procedurally generated;
- correctness and counterexample oracles were internal;
- the planner operated over a small finite skill graph;
- programs were side-effect-free and could not deploy themselves;
- source forgery still requires an external authenticity authority;
- natural-language capability-gap induction remains limited; and
- the evaluation was not administered independently.

The appropriate claim is that AION can perform bounded, counterexample-driven
repair-program synthesis and dynamic multi-repair composition under persistent
governance. It is not unrestricted autonomous programming, unconstrained
self-modification, or AGI.

## Next development

The next stage should weaken the engineered contracts. AION should infer
repair preconditions and postconditions from execution traces rather than
receiving them directly. It should then:

1. identify latent dependencies between invented repairs;
2. predict interference before executing a composition;
3. generate a verification experiment when a postcondition is uncertain;
4. revise a skill contract after observed failure;
5. consolidate recurring successful compositions into a faster proposal
   model without transferring authority;
6. evaluate over longer real-file projects with naturally occurring changes;
7. expose the integrated system to externally authored capability gaps; and
8. submit final claims to the frozen blind external-evaluation protocol.

That phase would test whether AION can learn not only a repair program, but
also the conditions under which the new capability is valid and how it
interacts with the rest of its cognitive system.
