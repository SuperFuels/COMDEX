# AION Independent Evaluation — External Handoff

## Why this handoff exists

The development team cannot independently certify its own benchmarks. This
packet defines the information an evaluator outside the AION development
process must provide before the external-evaluation gate can open.

## Evaluator responsibilities

The evaluator should:

1. author a source-disjoint sealed cohort after the evaluated build is frozen;
2. keep labels hidden until all system predictions are committed;
3. provide the same model, tool, time and information budgets to every system;
4. include enough tasks to report mean and weakest-family performance;
5. audit source and task overlap against disclosed development corpora;
6. reveal answers using the committed salts;
7. publish failures, abstentions, costs and confidence—not only aggregate wins;
8. sign an independence statement and retain the original task artifacts.

## Required task envelope

Each pre-evaluation task contains:

```json
{
  "task_id": "external-opaque-id",
  "family": "reading|research|mathematics|code|science|planning|causal|tool_use",
  "payload": {},
  "answer_commitment": "sha256-of-canonical-task-answer-and-salt"
}
```

The evaluator computes:

```text
SHA256(canonical(task_id, answer, external_salt))
```

The answer and salt are not disclosed until predictions from AION and every
matched control have been frozen.

## Required reveal

```json
{
  "task_id": "external-opaque-id",
  "answer": {},
  "salt": "external-secret-used-for-the-commitment"
}
```

Missing or commitment-invalid reveals are not scoreable and cannot authorize
promotion.

## Required comparisons

At minimum, report:

- AION with its retained memory and skills;
- AION with accumulated memory disabled;
- the same language substrate with equivalent tools but without HexCore;
- at least one current agent framework;
- the appropriate specialist baseline for causal or planning families;
- a human baseline where the task permits meaningful human scoring.

## Promotion gates

Promotion remains closed unless:

- the evaluator is independent from benchmark and implementation development;
- all answer commitments validate;
- no prohibited source overlap is found;
- AION improves mean performance over the matched no-memory control;
- no material weakest-family collapse occurs;
- unsafe acceptance does not increase;
- costs, tool calls and model budgets are within the frozen contract;
- restart and component-replacement checks pass;
- CAU authorizes the resulting challenger.

## Human-judgment extension

Commonsense, social and creative evaluation uses a separate blind pairwise
packet and requires at least three complete independent raters. Candidate
identity is hidden. Raters score contextual appropriateness, reasoning quality,
helpfulness, uncertainty calibration and originality, and can mark either
response unacceptable. Internal synthetic scores cannot replace this panel.

## Current status

The scoring and commitment infrastructure is implemented. No external
evaluator has yet supplied and administered the sealed cohort. Therefore the
external capability gate remains correctly closed.

## Signed result return

The evaluator returns one
`aion.external.agi_evidence_attestation.v1` JSON envelope signed with an
Ed25519 key controlled by the evaluator. The public key, evaluator identity and
independence statement must be published separately. The envelope commits to:

- the frozen registry and capability-artifact manifest;
- the sealed portfolio, delayed outcomes, rater panel, budgets and answer
  reveals;
- all required portfolio families, matched systems and audit flags;
- one evidence commitment and pass/fail result for every AGI evidence gate;
- at least one independent reproduction with verified artifact hashes and
  complete logs.

The verifier is:

`backend/modules/hexcore/external_agi_evidence_attestation.py`

It rejects altered signatures, incomplete portfolio or baseline coverage,
failed audit fields, missing gates and incomplete reproduction. Cryptographic
verification authenticates the submitted statement; it does not replace public
scientific audit of evaluator independence or measurement quality.
