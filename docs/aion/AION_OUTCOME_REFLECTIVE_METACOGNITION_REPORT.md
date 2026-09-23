# AION Outcome-Reflective Metacognition

## Outcome

`procedure_outcome_reflective_metacognition_v2` is internally promoted.

AION now performs two distinct metacognitive operations around consequential
action. Before commitment, it criticises the proposed decision. After an
observed outcome, it compares expectation with consequence, attributes the
result, extracts a bounded lesson and makes that lesson available to matching
future decisions.

## Runtime chain

```text
goal -> investigate -> learn -> plan -> pre-action metacognition
     -> commit -> act -> observe -> criticise -> post-action reflection
     -> improve -> retain
```

Routine expected success produces a cheap no-op. Reflection is activated for a
bad or average outcome, material prediction error, or a high-risk action.

## Attribution

The reflector distinguishes:

- assumption failure;
- decision-model failure;
- execution or tool-path failure;
- evidence or observation failure;
- environmental change; and
- authority failure.

This matters because a failed execution does not prove that the chosen strategy
was wrong, while a changed environment does not prove that an earlier model was
always wrong.

## Lesson contract

Lessons are provisional records containing an evidence hash, attribution,
required future checks, a recommended adjustment and a decision signature.
Their scope is deliberately limited to matching signatures. They do not become
global beliefs from a single outcome.

## Sealed result

| Measure | Result |
|---|---:|
| Failure families | 5 |
| Attribution accuracy | 100% |
| Matching lesson transfer | 100% |
| Unrelated cheap-action preservation | 100% |
| Routine success reflection | Cheap no-op |
| Unsafe executions | 0 |
| LLM calls | 0 |
| Restart relearning | 0 |

The five families covered assumption, execution, environment, evidence and
authority failures. Each generated lesson affected the matching future action
while an unrelated read-only action remained on the cheap path.

## Claim boundary

This is deterministic, outcome-calibrated reflection over engineered failure
authorities. It is not consciousness, emotion, unrestricted causal attribution
or evidence of subjective experience. Its operational value is narrower and
testable: AION can learn a correctly scoped decision lesson from consequences
without relying on an LLM or indiscriminately slowing unrelated actions.
