# Pilot AION Native Fact-Check Smoke Benchmark

Run date: 30 August 2026  
Fabric: 0.43.0  
Mode: AION local Gemma plus live public evidence; no paid AI provider  
Cases: 3 fixed public claims

## Result

- Verdict match: 3/3 (100% for this smoke set).
- HTTPS evidence coverage: 3/3 (100%).
- Mean end-to-end latency: 11,120 ms.
- 95th-percentile latency: 11,426 ms.
- Provider/runtime errors: 0.
- Report hash: `108e4c36aa699da5ed838ff97d37f293f41fe8dc56ddd4375346142c3aad4969`.

The cases covered WHO constitutional history, Apollo 11 and the International Space
Station's orbit. Expected verdicts were fixed before execution. The first run exposed
irrelevant Bing RSS evidence and scored one of three. Pilot then added token-overlap
rejection and a bounded public Wikipedia search fallback; a fresh runtime produced the
result above.

This is a repeatable smoke benchmark, not a claim of general fact-check accuracy. A
larger dated, adversarial and multilingual set remains necessary before publishing a
consumer accuracy claim. The benchmark counts network/provider failures, retains no raw
provider response and does not let the model grade itself.
