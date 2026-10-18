# HexCore Latent Causal State Construction — Phase 5 Report

Date: 28 July 2026

## Purpose and claim boundary

Phase 4 allowed AION to construct a causal graph over observable variables.
Phase 5 addresses a harder failure: two observations can have the same visible
state and action yet produce different consequences because an unobserved
context persists through time.

This phase demonstrates construction and revision of one bounded binary latent
state in a controlled partially observable process. The observable variable
and action vocabularies are supplied. Hidden-state labels and candidate latent
graphs are not supplied. This is not arbitrary latent-variable discovery.

## Architecture

The learner now performs five governed operations:

1. **Visible-state criticism.** It hashes each visible state/action context and
   detects contexts associated with incompatible next states.
2. **Latent-state authorization.** A hidden variable may be proposed only when
   a visible Markov model fails the held-out adequacy gate and alias conflicts
   are present.
3. **Bounded construction.** It enumerates a small inspectable grammar over
   latent initialization, latent-transition interventions, visible targets,
   and readout interventions. Candidate graphs are generated internally rather
   than supplied as a finite hypothesis list.
4. **Episode-held-out evaluation.** Whole episodes, not randomly interleaved
   transitions, are excluded from construction. This prevents history leakage.
5. **Governed revision.** A retained latent graph is criticised on observations
   from the changed environment. A replacement must exceed the old graph on
   unseen episodes, stay within latent and complexity caps, pass CAU, and
   explicitly supersede the previous graph.

Experiment sequences are selected through balanced ordered-pair coverage over
the available actions. This maximises untested action-history contexts without
using the hidden environmental rule.

## Benchmark environment

The only observable variable is a binary lamp. The environment also maintains
an invisible binary operating mode. `pulse` changes the lamp only when that
hidden mode is active. During Phase A, `toggle_mode` changes the hidden mode;
during Phase B, the environment changes and `switch_mode` becomes the causal
intervention. The hidden mode is never returned in evidence.

Forty episodes of twelve actions were used per phase. Episodes divisible by
four were sealed as held-out sequences.

## Phase A results: latent construction

The visible-only Markov model scored 94.1667% on unseen episodes but contained
repeatable alias conflicts. Because the operational adequacy gate was 98%, the
learner correctly returned `NONE_ADEQUATE`.

AION constructed:

- latent variable: `latent_context_1`;
- cardinality: two;
- initial state: zero;
- transition: toggle on `toggle_mode`;
- readout: affect `lamp` on `pulse`;
- graph complexity: four.

The constructed graph scored 100% held-out accuracy, a 5.8333-point gain.

## Phase B results: structural change and revision

After the environment changed, the Phase A graph fell to 87.5% held-out
accuracy and was rejected. AION constructed revision two:

- latent variable: `latent_context_2`;
- transition changed from `toggle_mode` to `switch_mode`;
- the `pulse` readout relation remained;
- graph complexity remained four;
- held-out accuracy returned to 100%;
- gain over the obsolete graph was 12.5 points.

The new graph explicitly records the identifier of the graph it supersedes.
The earlier latent variable is retained as `superseded`; exactly one current
latent variable remains active.

## Persistence, governance, and safety

The revised graph survived process restart at 100% Phase B held-out accuracy
with zero relearning experiments. The persistent HexCore schema now retains
latent-variable records and exposes their count through runtime status.

A separate authority-cap test set the allowed number of latent variables to
zero. The otherwise justified proposal was rejected and no causal graph was
retained. Predictive improvement therefore cannot bypass the latent-complexity
authority.

All 20 persistent-learning, governed-runtime, and conversation-governance tests
pass.

## Remaining development

The next world-learning stage should combine:

- stochastic latent transitions and calibrated posterior belief;
- more than one possible latent factor, with a minimum-description penalty;
- active experiments chosen by expected information gain over latent graphs;
- graph-informed planning and procedure generation;
- cross-environment transfer with entirely new variable and action names;
- contradiction-aware links between latent causal rules, knowledge provenance,
  and outcome memory.

Gemma and OpenAI may later translate natural language into candidate variables
or interventions, but execution, held-out prediction, CAU, and observed
outcomes remain the authority for accepting causal structure.

