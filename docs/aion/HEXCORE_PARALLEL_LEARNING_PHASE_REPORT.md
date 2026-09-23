# HexCore Parallel Learning — Phase 1 Report

Date: 28 July 2026  
Status: Phases 1, 2 and 3 implemented and passed

## Objective

Build knowledge learning, world learning and skill learning around HexCore
without waiting for completion of the 150M language-foundation run and without
binding accumulated intelligence to Gemma, OpenAI, Gemini, or one native AION
checkpoint.

## Work breakdown

### Track K — Knowledge learning

1. Versioned evidence capsules.
2. Source URI, checksum, timestamp, verification state and confidence.
3. Structured claims linked to evidence.
4. Retrieval with confidence and provenance.
5. Contradiction detection.
6. Higher-revision belief replacement without deleting historical claims.
7. Future: document parsing, hybrid vector/symbolic retrieval, multi-document
   entailment and source trust.

### Track W — World learning

1. Versioned state/action/next-state observations.
2. Numeric-delta and categorical-effect discovery.
3. Support, contradiction and confidence counts.
4. Conditional threshold-rule discovery.
5. Rules remain hypotheses until minimum support and confidence gates pass.
6. Future: stochastic dynamics, hidden state, partial observability, active
   experiment selection and non-factorised causal models.

### Track S — Skill learning

1. Build procedures from learned world rules.
2. Execute procedures in a verifier-controlled environment.
3. Score outcomes.
4. Promote only successful challengers that outperform the retained champion.
5. Preserve retired champions and promotion history for rollback.
6. Reload the champion after process restart.
7. Future: multi-step search, procedure mutation, disagreement arenas,
   cross-domain transfer and budget-aware planning.

### Shared Track G — Governance and measurement

1. All persistent mutations require a positive CAU decision.
2. Missing or denied authority fails closed.
3. Writes are atomic and schema-versioned.
4. Knowledge, world rules, procedures and outcomes share one persistent state.
5. HexCore conversation recall can retrieve the new persistent claims.
6. The language provider remains optional and replaceable.
7. Every phase requires an unchanged baseline, held-out evaluation and restart
   test.

## Implemented runtime

The shared runtime is:

`backend/modules/hexcore/persistent_learning.py`

It contains:

- `EvidenceCapsule`
- `TransitionObservation`
- `ProcedureCandidate`
- `HexCorePersistentLearningStore`
- `GovernedKnowledgeLearner`
- `GovernedWorldLearner`
- `GovernedSkillLearner`
- `HexCorePersistentLearningRuntime`

The integrated benchmark is:

`backend/modules/hexcore/integrated_learning_benchmark.py`

The live persisted research state is:

`.runtime/COMDEX_MOVE/data/hexcore/persistent_learning_state.json`

The existing HexCore governance status now reports the three learning layers,
their state path and their current counts. Persistent claims are included in
recall-before-reasoning with the source
`hexcore_persistent_knowledge`.

## Phase 1 benchmark

The first bounded environment is `lumen_vault_v1`.

AION was not supplied with the action rules. It received:

- an obsolete manual claiming the vault required five energy units;
- a later verified revision correcting the threshold to four;
- nine action/consequence observations;
- an execution environment that could verify proposed procedures.

The hidden environment behavior was:

- `charge` increases energy by two;
- `leak` decreases energy by one;
- `open` succeeds when energy is at least four.

These rules were used by the simulator but were not passed directly to the
learner.

## Results

| Measurement | Baseline | After learning |
|---|---:|---:|
| Correct current knowledge | No | Yes |
| Active learned world rules | 0 | 6 |
| Task success | No | Yes |
| Composite score | 0.00 | 1.00 |
| Improvement delta | — | +1.00 |

All four phase gates passed:

- knowledge gate: passed;
- world-rule gate: passed;
- skill gate: passed;
- restart-persistence gate: passed.

The knowledge learner:

- detected one contradiction;
- retained the obsolete claim as superseded history;
- selected the revision-two value of four;
- retained complete evidence provenance.

The world learner:

- stored nine observations;
- learned the `charge` energy delta;
- learned the `leak` energy delta;
- learned the conditional `open` threshold;
- stored six active field-level rules.

The skill learner constructed:

`charge -> charge -> open`

The procedure succeeded under execution, became the first champion, and was
stored with its source rules and outcome evidence.

After a completely new runtime instance loaded the state:

- the corrected knowledge remained available;
- the learned world rules remained available;
- the champion procedure remained available;
- the procedure solved a held-out initial state;
- no new probes, ingestion or retraining were required.

Final persistent state:

- revision: 15;
- evidence capsules: 2;
- active claims: 2;
- contradictions: 1;
- observations: 9;
- active world rules: 6;
- procedures: 1;
- champions: 1;
- recorded outcomes: 1.

## Interpretation

This is the first unified demonstration in the current HexCore integration that
AION can:

1. update an obsolete belief without erasing its history;
2. infer action consequences from experience;
3. assemble a procedure from learned rules;
4. verify the procedure through execution;
5. promote the successful challenger;
6. persist all three learning layers;
7. reuse them after restart.

No language model was used by this benchmark. The result therefore measures the
learning architecture rather than provider knowledge or next-token prediction.

This is bounded operational intelligence, not general or frontier
intelligence. The environment is deterministic, compact and structurally
simple.

## Next development gates

### Phase 2 — Generalisation

- at least five unfamiliar domain variants;
- held-out vocabularies and surface descriptions;
- the same learned abstraction must transfer across at least three worlds;
- no hard-coded domain names in the learning algorithms;
- restart retention must remain 100 percent.

### Phase 3 — Uncertainty and active discovery

- stochastic consequences;
- noisy and contradictory observations;
- hidden operating modes;
- experiment cost;
- expected information-gain selection;
- abstention when uncertainty remains too high.

### Phase 4 — Language grounding

- convert natural documents into evidence capsules;
- require exact claim-to-source grounding;
- use Gemma/OpenAI/Gemini only as candidate parsers;
- use execution, entailment and provenance checks as acceptance authorities;
- compare provider-assisted learning with provider-free structured controls.

### Phase 5 — Self-improving procedures

- multiple procedure challengers;
- procedure mutation and recombination;
- held-out challenger arenas;
- mean and worst-world promotion gates;
- rollback after regression;
- outcome-weighted replay;
- measure improvement across at least ten cycles.

## Phase 2 multi-domain generalisation result

Phase 2 replaced the single Lumen Vault with three new domains:

| Domain | State | Gain action | Loss action | Terminal action | Threshold |
|---|---|---|---|---|---:|
| Thermal Seal | temperature | warm | cool | release | 6 |
| Nutrient Reactor | nutrient | feed | consume | harvest | 8 |
| Pressure Lock | pressure | pump | bleed | unlock | 10 |

The learning implementation was unchanged. Only the environment specifications
and observations differed.

Results:

- domains attempted: 3;
- domains learned: 3;
- baseline success rate: 0 percent;
- learned success rate: 100 percent;
- restart success rate: 100 percent;
- cycle-one probes: 27;
- cycle-two probes: 0;
- evidence capsules: 6;
- obsolete claims detected and resolved: 3;
- observations retained: 27;
- active world rules: 18;
- promoted champion procedures: 3;
- recorded verified outcomes: 3.

The learned procedures were:

- `warm -> warm -> release`;
- `feed -> feed -> harvest`;
- `pump -> pump -> unlock`.

After restart, all three procedures solved held-out initial states without
re-ingestion, new experiments or retraining.

All multi-domain gates passed:

- all domains learned;
- all domains survived restart;
- all knowledge retained provenance;
- cycle two required zero relearning;
- no language provider was used;
- no domain-specific branch was added to the learning algorithms.

This is stronger than the single-world result because it demonstrates reuse of
one learning architecture across different state and action vocabularies.
However, the three environments remain structurally related threshold-control
problems. This is not yet evidence of transfer across fundamentally different
causal structures.

## Phase 3 active causal discovery result

Phase 3 introduced a partially observable stochastic system with two hidden
operating modes:

- in mode alpha, `amber` normally increases the state and `cobalt` decreases it;
- in mode beta, the effects are reversed;
- each action follows its mode rule with probability 0.9;
- the hidden mode is never shown to AION;
- actions have different experiment costs;
- AION must decide which experiment to run and when to stop.

The causal learner maintains an explicit posterior:

`P(hidden mode | actions, observed consequences)`.

For each possible experiment, it calculates expected entropy reduction and
subtracts an experiment-cost penalty. The selected experiment maximises:

`expected information gain - weighted experiment cost`.

An independent audit used 60 seeds per mode, or 120 episodes.

| Measurement | Result |
|---|---:|
| Hidden-mode identification accuracy | 97.5% |
| Calibrated-session rate | 100% |
| Average experiments | 2.483 |
| Average experiment cost | 0.248 |
| Maximum experiments observed | 6 |

The retained alpha belief was then exposed to a beta-mode observation. The
observation had predictive probability 0.1098 under the retained model, below
the 0.20 surprise threshold. AION:

1. detected that the environment had probably changed;
2. recorded a causal change event;
3. reset the stale posterior to an uninformative prior;
4. resumed active discovery;
5. identified beta with posterior confidence 0.9878.

Because action outcomes are stochastic, a minimal two-action procedure is not
reliable enough. AION calculated the number of repeated actions needed to
exceed a 95% target success probability. It constructed:

- alpha: `amber` repeated five times, followed by `open`;
- beta: `cobalt` repeated five times, followed by `open`.

Both procedures achieved 99% success across 200 simulator rollouts. Both were
promoted as separate mode-specific champions.

After restart:

- the latest beta causal belief was retained;
- both alpha and beta procedures were retained;
- both procedures again passed 100-rollout verification;
- no relearning experiments were required.

All Phase 3 gates passed:

- mode accuracy at least 90%;
- calibration at least 90%;
- average experiment count at most five;
- alpha discovery;
- mode-change detection;
- beta rediscovery;
- robust-procedure verification;
- restart retention.

Phase 3 is a meaningful advance over fixed-probe learning. AION now selects
experiments based on uncertainty, accounts for cost, stops when sufficiently
confident, detects model failure and relearns after environmental change.

The result remains bounded. The hypotheses were enumerable, the outcome space
was small and the causal structure was supplied as candidate models. The next
stage should require AION to construct or expand its own hypothesis set,
represent multi-variable causal graphs and decide when none of its current
models adequately explains the observations.
