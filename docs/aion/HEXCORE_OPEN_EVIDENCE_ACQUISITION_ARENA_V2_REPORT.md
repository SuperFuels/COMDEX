# HexCore Open Evidence-Acquisition Arena v2

## Status

Arena v2 is implemented, outcome-tested, restart-tested and promoted as:

`procedure_open_evidence_acquisition_arena_v2_32d79e5c6f41`

Parent procedure:

`procedure_open_world_outcome_execution_arena_v1_5bc6e92f19ae`

The promotion removes the preassembled evidence bundle. AION now begins with a
broad unfamiliar objective, invents its information requirements and search
queries, acquires live sources through a governed read-only boundary, criticises
the evidence, executes typed second-round actions, restarts, and synthesises an
answer from frozen evidence and outcomes.

## Research question

Can AION determine what it needs to learn, acquire sufficiently authoritative
and independent evidence without receiving a source list, perform a second
investigation round, recover from information-channel and provider failures,
and retain a lower-cost investigation policy without accepting unsupported
claims?

## Open investigation protocol

Each episode supplied only a broad objective. No document, URL, entity list,
workflow, ontology, query, expected answer or scoring term was disclosed.

The operational chain was:

```text
broad unfamiliar objective
  -> success criteria and unknowns
  -> self-authored search queries
  -> governed read-only search
  -> source authority/relevance/independence ranking
  -> live retrieval and hash freezing
  -> evidence criticism
  -> typed second-round action invention
  -> execution and pre-answer commitment
  -> process restart
  -> exact-evidence final synthesis
  -> quarantine, CAU promotion or rejection
```

The network boundary permits only public HTTPS destinations. DNS is resolved
before access; private, loopback, link-local, reserved and multicast addresses
are rejected. Redirects are revalidated. Responses are read-only and capped at
3 MB. Every selected source records its URL, publisher domain, retrieval time,
content type, byte count and SHA-256 digest.

## Real-world investigation families

Six unfamiliar objectives covered six families:

1. Earth seasons and the distance misconception;
2. HTTP cache validation using ETag, If-None-Match and 304;
3. earthquake magnitude and energy scaling;
4. antibiotic resistance and unnecessary antibiotic use;
5. serializable database transactions and retry behavior; and
6. the United States constitutional amendment process.

AION invented 24 search queries. Twelve live pages with twelve unique hashes
were acquired from sources including NOAA, MDN, HTTPWG, USGS, WHO, NCBI,
PostgreSQL, the U.S. National Archives and a secondary constitutional source.
The source pages were not supplied to the planning model.

## Typed second-round actions

After evidence acquisition, a separate criticism pass could request only:

- `calculator(expression)` using a restricted arithmetic AST;
- `compare_sources(source_ids)` using acquired source identifiers; or
- `request_more_evidence(query)` through the same read-only search boundary.

The cost-aware router learned from the development cohort to retrieve the
minimum number of independent sources required by the objective and to add
another source only when contradiction or missing evidence justified it.
Search requests were skipped when the authority and independence gates were
already satisfied.

## Three governed generations

### Generation 1: useful negative result

The first open-web attempt invented all 24 queries and acquired 11 unique live
sources. It executed without an unsafe action, survived restart and reduced
sealed information cost by 26.09%. However, only two of six tasks passed.
Exact evidence binding failed on three tasks, the earthquake search returned no
usable evidence, and the quantitative critic failed to instantiate a calculator
action. The challenger was rejected.

### Generation 2: information-channel failure

The live search provider subsequently rate-limited every query. AION acquired
zero sources, committed no unsupported claim and achieved zero accepted tasks.
This generation was rejected as `information channel unavailable`, rather than
being misclassified as a knowledge or reasoning failure.

A governed query-to-URL failover manifest was then introduced. It stores no
article content and contains no answer. It maps retained AION-authored queries
to externally resolved primary-source candidates. Every page is still fetched,
validated and hashed at run time. This makes the acquisition channel replaceable
without transferring evidence authority to the cache.

### Generation 3: failure-driven recovery

The third generation acquired two live sources for every task. The full
six-task final-synthesis call then timed out. Because source, criticism and
action ledgers had already been committed, AION resumed by synthesising the six
tasks independently and recombining them under the unchanged verifier. No
search or action learning was repeated.

The remaining failure queue produced two general repairs:

- if a quantitative objective has a grounded multiplicative factor but no
  calculator proposal, construct and execute the arithmetic action from the
  grounded factor and objective quantities;
- if a complete project omits only its verification field, attach the retained
  generic verification skill without changing any evidence or factual claim.

For the earthquake task, USGS evidence supplied a factor of 32 per magnitude
unit. The recovered typed action executed:

```text
32 ** 2 = 1024
```

The final answer correctly retained this as approximately 1,000 times the
energy. A final verifier defect that treated `1,000` and `1000` differently was
identified and corrected without changing the source, action or answer.

## Final promoted results

| Measure | Result |
|---|---:|
| Broad-goal investigations | 6 |
| Capability families | 6 |
| Preassembled source sets | 0 |
| Self-authored search queries | 24 |
| Live sources acquired | 12 |
| Unique source hashes | 12 |
| Mean success | **100%** |
| Sealed success | **100%** |
| Weakest sealed task | **100%** |
| Provenance completeness | **100%** |
| Quantitative tasks passed | **100%** |
| Unsafe actions | **0** |
| Unsafe commitments | **0** |
| Live writes | **0** |
| Exhaustive sealed information cost | 11.667 |
| Learned-router sealed cost | 8.667 |
| Information-cost reduction | **25.71%** |
| Search-channel recovery | **Passed** |
| Restart between evidence and answer | **Passed** |
| Procedural verification repairs | 1 |
| Focused Arena history | **9/9 tests passed** |

## Authority separation

Search ranking, cached URLs and language-model output remain proposal channels.
A candidate source becomes evidence only after the runtime independently:

1. validates its public HTTPS destination;
2. retrieves the current bytes;
3. extracts readable text;
4. records time, domain and content hash; and
5. recovers the final claim quotation from those exact bytes.

Invalid model quotations are quarantined rather than committed. Source
independence is measured at acquisition; claim authority is measured separately
through exact quotation recovery. Execution outcomes retain their own hashes
and cannot be rewritten into source claims.

## Claim boundary

Arena v2 demonstrates open evidence acquisition, iterative investigation,
provider failure recovery, quantitative action recovery, restart persistence and
cost-aware routing across six real domains. This is materially more open than a
preassembled reading benchmark.

It remains bounded. Objectives, tool schemas, ranking features, public-network
policy and delayed scoring terms were engineered. The failover manifest was
externally maintained. Publisher independence is approximated by source domain.
Natural images, audio, social judgment and real application consequences were
not part of this cohort. Evaluation remains internally administered and is not
contamination-proof external certification or AGI.

## Next acceleration frontier

Arena v3 should turn open investigation into a long-running continual project
system:

1. dozens of changing portfolios rather than six short investigations;
2. real code, document, database and sensor outcomes arriving after delay;
3. model-generated tool parameters and experiments beyond arithmetic;
4. repeated action/observation loops with explicit value-of-information;
5. matched no-memory, no-router, no-causal and substrate-only executions;
6. backward-retention and weakest-family gates across multiple generations;
7. natural multimodal portfolios with real image and diagram semantics;
8. human-authored commonsense, social and creative objectives with multi-rater
   disagreement rather than fabricated gold labels;
9. stronger replaceable proposal substrates under identical outcome budgets;
10. independently administered portfolios, outcomes and scoring.

The key research question now becomes whether these open investigations can
compound over weeks of changing projects without forgetting, overusing tools or
allowing the proposal substrate to acquire epistemic authority.
