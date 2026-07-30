# AION HexCore Phase 57 — Richer Learned World Models

**Date:** 30 July 2026

## Purpose

Phase 57 connects learned world modelling to the real-file project substrate
created in Phase 56. Rather than receiving a fixed list of complete worlds,
AION observes typed source and artifact entities, project dependencies, file
revisions and reconciliation outcomes. It must infer which transition theory
best explains those events, preserve uncertainty over alternatives, predict
withheld events and declare its model family inadequate when a novel event
cannot be explained safely.

## Real-file event substrate

The learner operated on checksum-grounded copies of actual repository:

- JSON result files;
- Markdown technical reports; and
- YAML governance policy.

Original files remained unchanged.

The development families were Phases 48–52. The sealed families were Phases
53–56, including two dependency topologies not present in development.

Each project graph contained typed source entities and derived artifacts:

```text
result source -> status projection
report source + status -> evidence binding
policy source + status -> authority check
status + evidence + authority -> manifest
manifest -> independent verification
verification -> project closure
```

Some sealed graphs also contained a publication receipt that altered the
downstream topology.

## Competing model induction

AION compared twelve inspectable relational world models formed from:

### Invalidation operators

- no effect;
- direct dependants only;
- transitive dependency propagation; and
- blanket invalidation.

### Conflict policies

- ignore;
- rebuild; and
- abstain.

Models were scored on exact and field-level transition prediction with a
complexity penalty. Posterior mass was retained rather than collapsing the
entire model space into an unqualified answer.

The selected model learned:

```text
source revision
  -> invalidate every transitively dependent artifact

confirmed reconciliation
  -> ready for independent verification

unresolved conflict
  -> abstain
```

The retained posterior was:

| Model | Posterior |
|---|---:|
| Transitive invalidation + abstain | 71.28% |
| Transitive invalidation + rebuild | 17.37% |
| Transitive invalidation + ignore | 6.98% |

The leading alternative models remain available for criticism and future
revision.

## Withheld-event protocol

For each sealed project:

1. a real copied source was revised;
2. the before and after SHA-256 values were recorded;
3. AION predicted the affected artifacts before the expected transition was
   exposed;
4. a reconciliation outcome was withheld and predicted;
5. predictions were compared against the independently traversed dependency
   graph; and
6. an unseen authority-revocation event was submitted as an out-of-family
   control.

AION did not force the novel event into an existing transition. It emitted:

```text
EVENT_OUTSIDE_LEARNED_MODEL_FAMILY
```

and abstained.

## Cold control

The cold control had the same project files and source-change observation but
no learned relational transition model. It invalidated every derived artifact
after each change.

The learned system invalidated only the transitive consequences of the changed
source.

## Sealed results

| Measure | Result |
|---|---:|
| Development projects | 5 |
| Sealed projects | 4 |
| Candidate models compared | 12 |
| Competing explanations retained | 3 |
| Withheld-event accuracy | 100% |
| Weakest-family accuracy | 100% |
| Novel-event criticism | 100% |
| Unsafe novel-event forcing | 0 |
| Provenance completeness | 100% |
| Unseen topologies evaluated | 2 |
| Learned re-execution cost | 20 |
| Cold re-execution cost | 26 |
| Cost reduction versus cold | 23.08% |
| Original repository files modified | 0 |

## Persistent architecture

HexCore now persists:

- `relational_world_models`;
- `world_model_sessions`;
- the selected model and retained alternatives;
- model posteriors and development scores;
- project dependency graphs;
- withheld predictions and revealed outcomes;
- model criticisms;
- source checksums; and
- the promoted procedure lineage.

Restart verification confirmed that the world model, every sealed session and
the promoted champion survived reconstruction with zero event relearning.

## Promotion

CAU promoted:

`procedure_richer_world_model_0d316f0f69ad`

Its operational chain is:

```text
real project event
  -> typed relational state
  -> competing transition models
  -> posterior-weighted champion
  -> withheld-event prediction
  -> outcome comparison
  -> criticism or revision
  -> CAU-governed persistence
```

## Interpretation

Phase 57 demonstrates that AION can transfer a learned rule about consequences
across renamed files, different project families and unseen dependency
topologies. It does not simply memorise that a result-file change always costs
five tasks. It follows the dependency relations in the current graph and
predicts the specific downstream artifacts that become stale.

It also demonstrates a critical metacognitive behaviour: when presented with
an event type outside the learned explanatory family, AION states that its
model is inadequate and abstains rather than manufacturing a prediction.

## Claim boundary

The result remains bounded:

- source roles and dependency graphs were engineered;
- the candidate operator grammar was supplied;
- the revision controller and correctness oracle were internal;
- file events were controlled rather than naturally occurring over weeks;
- the learner did not infer arbitrary physics, human intentions or software
  semantics from raw observation; and
- external certification remains deferred to Phase 62.

This is a transferable relational project world model, not unrestricted world
understanding.

## Next development

Phase 58 should replace typed synthetic modality contracts with natural
multimodal evidence:

- real photographs and diagrams;
- charts and tables;
- PDF page layout;
- structured files and software state;
- contradictory cross-modal evidence; and
- temporal sequences in which observations change.

The Phase 57 model should then predict cross-modal consequences while exact
source evidence, independent checks and CAU remain authoritative.
