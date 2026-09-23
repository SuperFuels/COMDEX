# AION Adaptive Metacognitive Deliberation

## Promotion

`procedure_adaptive_metacognitive_deliberation_v1` is internally promoted.

AION now performs an independent, non-LLM review between planning and action commitment. The review inspects the executable decision contract and returns one of five operational results: execute, revise, investigate, abstain or escalate.

## Runtime architecture

```text
goal -> investigate -> learn -> plan
     -> metacognitive_review
     -> commit_action -> act -> observe
     -> criticise -> improve -> retain
```

The controller maintains an assumption ledger, uncertainty and risk estimates, counterfactual replies, contradiction checks, reversibility and rollback analysis, outcome-calibrated failure memory and alternative-action comparisons. Low-risk reversible actions receive three cheap checks. High-risk, uncertain, irreversible, contradicted or historically fragile actions receive five additional checks. No language model is called.

## Rejected challenger and correction

The first challenger prevented every trap but activated deep deliberation for every later action in the same domain. It was rejected. The promoted controller keys failure memory by decision signature: action type, risk tier, irreversibility and rollback availability. It learns that a particular decision structure failed without generalising fear to every action in that domain.

## Sealed results

| Measure | Result |
|---|---:|
| Actor-only success | 50% |
| Metacognitive success | 100% |
| Weakest-domain success | 100% |
| Tempting traps prevented | 5/5 |
| Routine actions preserved on cheap path | 5/5 |
| Deliberation reduction vs always-deep | 31.25% |
| Unsafe executions | 0 |
| LLM calls | 0 |
| Restart retention | Passed |

Ten sealed decisions covered chess, software, research, causal inference and tool use. Metacognition remains control logic rather than truth authority. HexCore and CAU govern commitment; executable or independently revealed outcomes judge success.

## Boundary

The benchmark supplied counterfactual probes, alternatives and outcome authorities. This demonstrates bounded, outcome-calibrated pre-action metacognition, not machine consciousness or unrestricted introspection.

