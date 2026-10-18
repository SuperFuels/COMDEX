# Phase 47 — Stronger Replaceable Cognitive Substrate V1

**Date:** 30 July 2026

**Status:** Bounded V1 passed and promoted.

## Objective

Determine whether a substantially stronger pretrained language substrate improves AION's natural-language transfer without moving truth, memory, execution or promotion authority into the language model.

## Local substrate

| Property | Value |
|---|---|
| Model | `gemma4:e2b` |
| Parameters | 5.1B |
| Quantization | Q4_K_M |
| Context | 131,072 tokens |
| Representation width | 1,536 |
| Local artifact size | approximately 7.2GB |
| Capabilities advertised by runtime | completion, vision, audio, tools, thinking |
| Model digest | `7fbdbf8f5e45a75bb122155ed546e765b4d9c53a1285f62fd9f506baa1c5a47e` |

The Ollama package does not expose this model through its embedding endpoint. Phase 47 therefore uses constrained generation with a strict procedure-label interface, deterministic temperature and a small output budget.

## Architecture

Gemma is frozen, local, replaceable and proposal-only.

```text
natural instruction
    -> frozen Gemma procedure proposal
    -> label parser
    -> HexCore capability-contract check
    -> executable verification
    -> accept or governed fallback
    -> outcome memory and CAU
```

The language substrate cannot:

- accept its own proposal;
- create an executable capability contract;
- write HexCore knowledge;
- approve promotion;
- bypass fallback;
- modify the protected 150M foundation;
- become required for correct operation.

All responses are cached by model and instruction hash, making evaluation resumable.

## Evaluation

The official cohort contained:

- 96 sealed natural-paraphrase tasks;
- 48 external-source paraphrase tasks;
- 48 subjective, ambiguous or unknown OOD requests.

Twelve executable procedure classes covered mathematics, logic, evidence, causal reasoning, planning and tool routing. The lexical control was trained on the Phase 46 procedural language. Gemma received the same allowed procedure schema and source-disjoint natural instructions.

## Results

| Measure | Result |
|---|---:|
| Lexical-control proposal accuracy | 8.33% |
| Gemma proposal accuracy | 90.97% |
| Proposal transfer gain | +82.64 points |
| Weakest-family proposal accuracy | 66.67% |
| Governed outcome accuracy | 100% |
| Reasoning-attempt reduction | 73.66% |
| Unsafe accepted proposals | 0 |
| Mean recorded local proposal latency | 321 ms |
| Provider-disabled governed accuracy | 100% |
| Raw Gemma OOD abstention | 50% |
| Governed OOD abstention | 100% |
| Governed OOD unsafe acceptances | 0 |
| Restart retention | 100% |

Promoted procedure:

`procedure_stronger_substrate_3ddbe4956a12`

## Decisive negative and architectural finding

Gemma itself abstained on only half of the OOD requests. The first evaluation correctly rejected promotion when raw model abstention was incorrectly treated as the safety gate.

The corrected architecture applies the pre-declared HexCore rule: no proposal can be accepted without a compatible executable contract. Every OOD request lacked such a contract, so all were safely routed to abstention/fallback. The raw 50% score remains recorded as a model limitation.

This establishes why the dual architecture matters:

- the pretrained model supplies stronger semantic intuition;
- HexCore determines whether that intuition is actionable;
- executable authorities determine correctness;
- CAU determines promotion.

## Boundary

The task suite is internally authored and limited to constrained procedure classification. The result does not establish broad reading comprehension, discourse understanding, native AION language generation, general multimodal cognition, independent frontier competitiveness or AGI.

Phase 47 V2 should test the frozen substrate on natural documents, open-schema extraction, multimodal proposals and grounded generation. The next numbered phase is Phase 48: frozen, contamination-controlled external evaluation.
