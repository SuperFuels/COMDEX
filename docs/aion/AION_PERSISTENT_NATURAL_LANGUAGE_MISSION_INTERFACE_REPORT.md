# AION Persistent Natural-Language Mission Interface

## Result

AION now maintains natural-language discourse across turns and restart, infers
semantic intent using a local replaceable sentence encoder, resolves contextual
references, preserves explicit user corrections, asks a targeted clarification
when reference or intent remains ambiguous, and compiles resolved owner intent
into a mission-bound goal contract.

Promoted procedure:

`procedure_persistent_natural_language_mission_interface_v1`

## Architecture

```text
natural multi-turn dialogue
  -> persistent discourse state
  -> semantic intent prototypes
  -> reference and correction resolution
  -> ambiguity margin / clarification
  -> listener-profile contract
  -> owner-authorized objective hash
  -> governed HexCore goal proposal
```

The semantic intent layer distinguishes research, comparison, construction,
monitoring, repair and explanation.  It does not grant action authority.  A
goal is compiled only after the target referent is resolved; unresolved
multi-referent requests remain clarification sessions.

## Results

| Measure | Result |
|---|---:|
| Multi-turn dialogue sessions | 10 |
| Verified interpretations | 10/10 |
| Source-disjoint transfer sessions | 6/6 |
| Semantic intent accuracy | 100% |
| Literal keyword control | 30% |
| Ambiguous-reference abstention | Passed |
| Explicit correction retention | Passed |
| Novice explanation adaptation | Passed |
| Expert explanation adaptation | Passed |
| Unsafe goal compilations | 0 |
| Mission-objective mutations | 0 |
| Restart relearning | 0 |

The first challenger scored 9/10 because an expert explanation request was
misclassified as research.  It was not promoted.  The explanation prototype
was expanded using development-side specialist language, after which all ten
sessions passed without regression.

Dialogue sessions, compiled goals, corrections and the procedure champion
survived full reconstruction.

## Verification and boundary

The combined focused runtime stack now passes 31/31 tests.  This is a bounded
semantic mission interface, not unrestricted language understanding.  The local
sentence encoder, six intent families and interpretation authority remain
engineered.  Multilingual acquisition, long open conversation and unrestricted
pragmatic/social understanding remain future work.

