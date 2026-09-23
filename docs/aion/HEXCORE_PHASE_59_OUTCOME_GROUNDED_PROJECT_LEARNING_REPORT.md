# AION HexCore Phase 59 — Outcome-Grounded Project Learning

**Date:** 30 July 2026

## Purpose

Phase 59 tests whether verified project outcomes can produce transferable
improvement rather than merely being stored as history. It extends Phase 58
open multimodal project intelligence with:

- delayed outcome revelation;
- explicit failure attribution;
- counterfactual repair testing;
- private challenger construction;
- protected replay across successive generations;
- source-disjoint sealed transfer;
- safe abstention outside the learned repair family; and
- restart-persistent promotion under CAU.

The central question was:

> Can AION observe that a project failed, determine where in its cognitive
> chain the failure arose, discover a repair from outcomes, retain that repair
> and apply it to unfamiliar project families?

## Project chain

The evaluated chain separates five stages:

```text
source perception
  -> evidence interpretation
  -> verification planning
  -> tool execution
  -> governed commitment
```

This separation prevents every failed project from being treated as one
undifferentiated error.

## Outcome protocol

Each episode proceeds in a fixed temporal order:

1. AION receives a broad goal and natural file portfolio.
2. It discovers the sources, constructs a schema and generates a plan.
3. It produces a provisional result.
4. The result is retained only as `reported_pending_delayed_outcome`.
5. An independently recomputed outcome is revealed later.
6. AION compares the revealed outcome with its source inventory, grounded
   result, verification graph, execution receipt and authority state.
7. Private repair candidates are tested counterfactually.
8. A repair becomes eligible only when it alone restores the verified
   outcome.

The delayed outcome was never available before the provisional attempt. No
failed provisional result was written as verified knowledge.

## Failure model

Four development failure families were introduced at distinct points in the
project chain:

| Failure family | Observable discrepancy |
|---|---|
| Perception | Expected source checksum is absent from the discovered inventory |
| Interpretation | Complete evidence is present, but recomputation disagrees with the provisional conclusion |
| Planning | The independent verification action is missing |
| Execution | The plan and conclusion are correct, but the execution receipt is invalid |

An authority-revocation condition was withheld as an out-of-family control.

## Causal attribution correction

The first implementation was rejected. A missing source caused both:

- an inventory gap; and
- a downstream interpretation mismatch.

Treating these as two independent failures prevented a unique repair from
being learned. The diagnostic model was corrected to attribute the earliest
independently observed cause:

```text
authority unavailable -> outside learned repair family
inventory gap         -> perception
outcome mismatch      -> interpretation
verification missing  -> planning
invalid receipt       -> execution
```

This is a causal ordering, not merely a change to a score threshold. Repairing
the upstream source inventory is allowed to resolve its downstream symptoms.

## Counterfactual repair arena

The learner was given four bounded repair operators, but no evaluator failure
label:

```text
restore_complete_inventory
recompute_from_grounded_evidence
restore_independent_verification
retry_with_verified_receipt
```

For every failed development outcome, each operator was applied privately.
The operator was retained only if:

- it restored exact project correctness;
- no competing operator also passed;
- it did not create an unsafe commitment; and
- it passed replay on previously learned failure families.

The resulting learned policy was:

| Diagnosed failure | Learned repair |
|---|---|
| Perception | Restore the checksum-complete source inventory and reconstruct downstream state |
| Interpretation | Recompute from grounded evidence |
| Planning | Restore independent goal and abstention verification |
| Execution | Retry and require a verified outcome receipt |

## Continual generations

### Generation 1

Generation 1 learned perception and planning repair from six delayed
development outcomes across three real chart portfolios.

| Measure | Result |
|---|---:|
| Development accuracy | 100% |
| Weakest-family accuracy | 100% |
| Diagnosis accuracy | 100% |
| Unsafe final commitments | 0 |
| Promotable | Yes |

### Generation 2

Generation 2 added interpretation and execution repair while replaying every
Generation 1 case.

| Measure | Result |
|---|---:|
| Development accuracy | 100% |
| Weakest-family accuracy | 100% |
| Diagnosis accuracy | 100% |
| Backward retention | 100% |
| Unsafe final commitments | 0 |
| Promotable | Yes |

No earlier repair was overwritten or forgotten.

## Source-disjoint sealed transfer

The development sources were three scientific chart portfolios. The sealed
cohort used unfamiliar:

- financial PDF evidence;
- Fourier table and chart evidence; and
- GlyphOS architecture PDF, configuration and implementation evidence.

Development and sealed source checksums had zero overlap.

Every sealed portfolio was evaluated under:

- perception failure;
- interpretation failure;
- planning failure;
- execution failure; and
- a clean control.

This produced fifteen sealed episodes. The unchanged control and learned
challenger received the same source files, goals and failure events.

## Sealed results

| Measure | Cold control | Learned challenger |
|---|---:|---:|
| Project accuracy | 20% | **100%** |
| Weakest-family accuracy | 20% | **100%** |
| Failure-diagnosis accuracy | 100% | **100%** |
| Unsafe final commitments | 0 | **0** |
| Repair actions | 0 | 12 |

The exact project-accuracy gain was **80 percentage points**.

The cold control solved only the three clean episodes. The challenger repaired
all twelve failed episodes and preserved all three clean outcomes.

## Unknown-failure criticism

Authority revocation was not present during repair learning. It was applied
once to each sealed portfolio.

In all three cases AION emitted:

```text
outside_learned_failure_family
```

and abstained. It did not misuse one of the four learned repairs to bypass
missing authority.

| Measure | Result |
|---|---:|
| Unknown-failure cases | 3 |
| Safe abstentions | 3 |
| Unsafe forced repairs | 0 |

## Persistent architecture

HexCore now persists:

- `project_outcome_ledger`;
- `project_failure_models`;
- `project_learning_challengers`;
- `project_learning_generations`;
- the diagnosis-to-repair policy;
- every provisional outcome and later revealed result;
- every counterfactual repair trial;
- separate project failure queues;
- backward-retention results; and
- the CAU-authorized promotion lineage.

The outcome ledger contains twelve development records: six from each
generation.

Restart validation confirmed:

| Persistence check | Result |
|---|---:|
| Failure policy retained | Passed |
| Both continual generations retained | Passed |
| Promoted champion retained | Passed |
| Episodes relearned | 0 |

## Promotion

CAU promoted:

`procedure_outcome_grounded_projects_f314900848fe`

The operational chain is:

```text
open multimodal project
  -> provisional reported result
  -> delayed independently verified outcome
  -> causal failure attribution
  -> private counterfactual repair arena
  -> protected replay
  -> source-disjoint sealed transfer
  -> abstention outside learned repair family
  -> CAU promotion
  -> restart-persistent skill
```

The complete HexCore history passes **64/64** regression tests.

## Interpretation

Phase 59 demonstrates a bounded but meaningful self-improvement loop. AION did
not receive the correct repair directly. It:

- observed delayed success or failure;
- located the responsible stage in its project process;
- tested alternative repairs;
- retained the uniquely successful repair;
- added further repairs without forgetting earlier ones; and
- transferred the combined policy from scientific development files to
  financial, scientific and software sealed portfolios.

This is stronger than storing successful answers. The learned object is a
reusable method for correcting future cognitive work.

## Claim boundary

The result remains bounded:

- the four observable failure signals were engineered;
- the failure taxonomy and candidate repair operators were supplied;
- failures were deliberately injected;
- the delayed outcome oracle was implemented internally;
- the project set contains only three development and three sealed
  portfolios;
- the learned system did not invent an entirely new repair operator;
- no uncontrolled external action was permitted; and
- the evaluation is not independent external certification.

This is governed transferable self-repair, not unrestricted autonomous
self-improvement or AGI.

## Next development

The next phase should remove the fixed repair vocabulary. AION should:

1. encounter project failures that none of the retained repair operators can
   resolve;
2. describe the missing capability from the residual outcome discrepancy;
3. compose or invent a sandboxed Photon tool, diagnostic or verification
   procedure;
4. test the invention against counterexamples;
5. evaluate transfer across unrelated project families;
6. preserve clean and previously repaired capabilities through replay;
7. reject unnecessary or excessively complex inventions; and
8. submit any surviving invention to blind external evaluation and CAU.

That would connect outcome-grounded project learning to AION's existing tool
and experiment invention stack and test whether failure can create a genuinely
new capability rather than merely select among four supplied repairs.
