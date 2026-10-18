# HexCore Governed Cognitive Integration

Status: implemented research runtime  
Schema family: `aion.hexcore.*.v1`

## Purpose

HexCore is now the governed integration point around AION cognition. It does
not replace Gemma, OpenAI, Gemini, the AION composer, the Pattern Engine,
Tessaris, Symatics, goals, or memory. It defines what those components may
contribute and which observations are permitted to become durable learning.

The central rule is:

> A reasoning provider may propose. Evidence and execution may verify. CAU
> alone may authorize learning. Soul Laws may veto action.

This preserves the original AION design in which cognitive quality and
learning authority are separate.

## Runtime flow

1. A versioned `TurnPacket` enters the active AION conversation route.
2. HexCore obtains a fresh Cognitive Authority Unification (CAU) snapshot.
3. CEE LexMemory is queried before provider reasoning.
4. Dialogue goals and recent memories are attached to the governed context.
5. Pattern Engine results and Tessaris rules may be supplied as typed,
   provenance-bearing context.
6. Existing local or external reasoning providers produce a response.
   The older composer-side teaching mutation is disabled on this governed
   route.
7. HexCore records the outcome in an append-only, content-hashed ledger whose
   records link to the preceding record.
8. Provider output is not treated as knowledge.
9. Long-term memory mutation requires:
   - explicit teaching mode;
   - an explicit verified outcome;
   - verifier identity;
   - evidence provenance or an executable, formal, or human-authority
     verification method; and
   - a positive CAU decision.
10. HexCore actions are evaluated against Soul Laws before dispatch.

## Main implementation

- `backend/modules/hexcore/governed_runtime.py`
  - `HexCoreGovernedRuntime`
  - `GovernedTurnContext`
  - `AppendOnlyOutcomeLedger`
  - strict CAU fail-closed adapter
  - CEE LexMemory recall and verified-write adapter
  - Soul Law action evaluation
  - replaceable cognitive-foundation descriptor
- `backend/modules/aion_conversation/conversation_orchestrator.py`
  - starts and completes a governed HexCore cycle for every active
    `/api/aion/conversation/turn` request;
  - injects recalled knowledge into provider facts with source and confidence;
  - forwards dialogue commitments, unresolved goals, and recent turns;
  - returns governance and learning decisions in response metadata.
- `backend/modules/hexcore/hexcore.py`
  - evaluates every action before the system dispatcher or action switch;
  - records the action-governance result in the consciousness-cycle entry.
- `backend/modules/aion_cognition/cee_lex_memory.py` and
  `cee_exercise_playback.py`
  - legacy missing/malformed CAU fallbacks now deny learning instead of
    silently allowing mutation.
- `backend/routes/aion_conversation_orchestrator.py`
  - accepts `request_metadata` on turn requests;
  - exposes `/api/aion/conversation/governance/status`.

## Failure semantics

| Condition | Answering | Action | Long-term learning |
|---|---:|---:|---:|
| CAU permits learning | allowed | Soul Laws decide | eligible if verified |
| CAU denies learning | allowed | Soul Laws decide | denied |
| CAU missing or malformed | allowed | Soul Laws decide | denied |
| Soul Laws unavailable | allowed | denied | CAU still decides |
| Recall unavailable | allowed | unaffected | unaffected |
| Outcome ledger write fails | response may complete | unaffected | denied before memory mutation |
| Provider returns plausible but unverified text | allowed as response | separately governed | denied |

The system deliberately keeps answering availability separate from mutation
authority. A provider outage or governance outage must not silently become
permission to learn.

## Verified learning contract

Teaching requests may include:

```json
{
  "apply_teaching": true,
  "request_metadata": {
    "learning_outcome": {
      "verified": true,
      "verifier": "photon_executor",
      "verification_method": "executable",
      "answer": "verified result",
      "evidence_refs": ["capsule:sha256:..."],
      "resonance": {
        "SQI": 0.95,
        "rho": 0.90,
        "Ibar": 0.85
      }
    }
  }
}
```

`apply_teaching=true` alone is insufficient. The provider response itself is
also insufficient. Missing verification data creates a rejected candidate,
not a memory write.

## Foundation and sTPU boundary

The native AION language foundation is registered as a replaceable
representation provider. HexCore reports the configured TPU root and retained
checkpoint-selection metadata, but it does not load the 150M model inside each
web request. This avoids memory duplication and avoids interfering with
long-running training.

Gemma, OpenAI, and Gemini remain reasoning providers behind AION. They do not
own memory authority. A future 500M or 1B native foundation can replace the
representation provider without replacing knowledge memory, world learning,
skill learning, CAU, or the outcome ledger.

## Tests and invariants

The integration tests cover:

- recall-before-reasoning;
- no automatic learning from provider output;
- verified learning with positive CAU;
- CAU-denied and CAU-unavailable fail-closed behavior;
- Soul Law action veto;
- append-only, content-hashed outcome records;
- active conversation routing through HexCore;
- compatibility with existing workflow and HexCore Symatics tests.

The protected invariants are:

1. No provider can approve its own output as knowledge.
2. No authority data means no learning.
3. No Soul Law data means no action.
4. The current 150M champion remains immutable.
5. Learning and action decisions are visible in machine-readable metadata.
6. A future model can be swapped without discarding accumulated governed
   memory and outcomes.

## Next capability work

This integration establishes the control plane; it does not by itself create
frontier reasoning. The next capability work should use this stable interface
to build the three non-representation learning tracks in parallel:

1. knowledge learning: document capsules, hybrid retrieval, contradiction
   handling, provenance, and persistent concept relations;
2. world learning: structured state, causal dynamics, active experiments, and
   outcome verification;
3. skill learning: reusable reasoning procedures, challenger evaluation,
   rollback, and verified replay.

Those systems should emit verified `learning_outcome` records through HexCore
instead of writing directly to long-term memory.
