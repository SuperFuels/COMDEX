# AION HexCore Phase 42 - Adaptive Schema Theory Revision

**Status:** Promoted  
**Promoted procedure:** `procedure_adaptive_schema_revision_d5ea7bf85c36`  
**Parent:** `procedure_open_schema_learning_1d0456fd3c9f`

## Purpose

Phase 41 showed that AION could invent a missing relation schema from documents. Phase 42 tests a harder question: can it recognise that an inherited explanation is inadequate, construct a better variable-arity theory from interventions, preserve competing explanations under noise, and revise the accepted theory when the world's rule changes?

The phase deliberately keeps the theory language bounded. It includes Boolean threshold rules and threshold rules with one veto or exception over three, four, or five variables. The learner does not receive the correct schema.

## Architecture

Each world exposes an intervention point \(x\in\{0,1\}^n\), where \(n\in\{3,4,5\}\), and a noisy Boolean outcome. The bounded theory grammar contains:

\[
f_{\tau}(x)=\mathbf{1}\!\left[\sum_i x_i\geq\tau\right]
\]

and the defeasible form

\[
f_{\tau,v}(x)=\mathbf{1}\!\left[x_v=0\;\land\!
\sum_{i\neq v}x_i\geq\tau\right].
\]

The Phase 41 inheritance contains only the two limiting threshold rules, logical ANY (\(\tau=1\)) and logical ALL (\(\tau=n\)). Phase 42 adds:

1. **Model criticism.** The inherited rules are tested across the complete Boolean intervention cube. Three repeated observations per point make one noisy result insufficient to authorize expansion or preserve a weak theory.
2. **Controlled theory construction.** If neither inherited rule reaches 90% diagnostic agreement, HexCore opens the threshold-plus-veto grammar and removes predictively duplicate theories.
3. **Bayesian competition.** Every candidate retains posterior probability. Outcomes update all candidates using the declared 3% observation-noise model.
4. **Active experimentation.** The next intervention maximises expected posterior information gain divided by action cost.
5. **Noise-resistant stopping.** A theory must exceed 97% posterior confidence after at least eight independently selected interventions. This prevents one anomalous early observation from causing a brittle stop.
6. **Continuous criticism.** A rolling surprise monitor requires at least three contradictions in a five-observation window before authorising revision.
7. **Persistent revision.** Old and revised schemas, criticism status, evidence traces, CAU decision, and outcome are retained separately.

The neural and language systems have no authority in this phase. Experimental outcomes and held-out prediction decide whether a theory is accepted.

## Sealed Evaluation

The sealed cohort contained 72 unfamiliar worlds across six named domains:

- 24 three-variable worlds;
- 24 four-variable worlds;
- 24 five-variable worlds;
- 42 worlds requiring a schema beyond inherited ALL/ANY;
- 24 worlds with a genuine mid-stream rule change;
- 48 stable worlds used to measure false revision.

The random control used the same candidate grammar, likelihood, confidence threshold, minimum evidence requirement, and intervention budget. Its only difference was random rather than information-directed experiment selection.

## Results

| Measure | Result |
|---|---:|
| Final exact theory recovery | **100.00%** |
| Weakest-domain exact recovery | **100.00%** |
| Held-out predictive accuracy | **100.00%** |
| Novel-schema exact recovery | **100.00%** |
| Inadequate inherited theory rejected | **100.00%** |
| Genuine rule-change recall | **100.00%** |
| False durable revisions in stable worlds | **0** |
| Mean active interventions | **8.125** |
| Mean random-control interventions | **11.778** |
| Environmental intervention reduction | **31.01%** |
| Mean Brier score | **0.0009** |
| Unjustified complexity violations | **0** |
| Restart relearning | **0 worlds** |

All pre-declared promotion gates passed. The complete champion, 72 theories, and 72 revision-session records survived restart. CAU authorised promotion.

## Why This Matters

In plain English, AION can now say:

> "The rule I inherited does not explain these outcomes. I need a richer explanation. These experiments will distinguish the alternatives most efficiently. The evidence supports this threshold with this exception. Later observations show that the old rule has stopped working, so I will keep its history but adopt the newly verified rule."

This connects open-schema invention to probabilistic scientific revision. It is stronger than selecting from a fixed supplied list because grammar expansion is conditional on predictive failure, and it is stronger than one-shot induction because the accepted theory can be revised without erasing its provenance.

## Governance and Claim Boundary

Promotion required exact and predictive performance, weakest-domain protection, successful novel-schema discovery, correct criticism, change recall, zero stable-world false revisions, at least 10% intervention reduction, calibrated predictions, zero unjustified complexity growth, restart retention, and CAU authorisation.

This remains bounded causal/schema learning. The Boolean variables, candidate operator family, observation interface, noise model, and outcome oracle are engineered. The result does not establish arbitrary mathematical theory invention, unrestricted scientific discovery, real-world causal identification, or AGI.

## Recommended Phase 43

The next leap should remove the single-rule assumption. AION should learn **compositional probabilistic programs** containing multiple interacting clauses, context-dependent exceptions, continuous or multi-valued variables, and latent intermediate predicates. It should decide whether failure requires parameter revision, a new exception, a hidden variable, or a new operator. Evaluation should preserve active experimental accounting and introduce source-disjoint external simulators so that the system cannot succeed by fitting only the current generator.

