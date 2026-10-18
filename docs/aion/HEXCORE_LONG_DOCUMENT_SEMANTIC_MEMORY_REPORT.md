# HexCore Long-Document Semantic Memory — Phase Report

## Result

AION completed and promoted its first bounded long-document semantic-memory
cycle over three complete public-domain books:

- *Alice's Adventures in Wonderland*;
- *The Time Machine*;
- *Frankenstein*.

The corpus contains 143,164 words. The proposal substrate answered questions
from retrieved sentence windows, while HexCore independently required a
recoverable supporting quotation before retaining any answer or concept.

## Sealed development results

| Measure | Result |
|---|---:|
| Complete books | 3 |
| Source words | 143,164 |
| Verified question accuracy | 88.89% |
| Weakest-book accuracy | 66.67% |
| Provenance recovery for accepted answers | 100% |
| Delayed relation retrieval after restart | 100% |
| Concept-composition accuracy | 100% |
| Hypothetical compositions committed as facts | 0 |
| Unsafe knowledge commitments | 0 |
| Restart relearning | 0 |

Promoted procedure:

`procedure_long_document_semantic_memory_6d1736d5906a`

## Architectural advance

The retained memory separates:

1. source-bound concepts;
2. source-bound attribute relations;
3. hypothetical compositions;
4. reported but unverified contradictions;
5. independently accepted knowledge.

For example, the text-supported relations `white -> rabbit`,
`pink -> eyes`, `blue -> caterpillar`, `white -> sphinx` and
`yellow -> skin` survived restart. A first proximity learner incorrectly
created `pink -> rabbit`; the delayed structural test detected it and the
binding rule was corrected to adjective-to-immediately-modified-noun.

AION then constructed previously unstated combinations such as `blue rabbit`,
`yellow machine` and `white being`. These were retained only as
`hypothetical_composition`; none became a claim about the books or the world.
This implements the required distinction between reusable conceptual
composition and fabricated knowledge.

## Substrate evidence

The local Gemma proposal path improved after sentence-window retrieval but
remained unreliable on *The Time Machine*. Under the unchanged retrieval,
memory and verification contracts, the stronger OpenAI proposal substrate
reached the promotion gate. This identifies language proposal quality as a
current bottleneck while demonstrating that HexCore memory and authority remain
substrate-independent.

## Claim boundary

The books and questions are public development material. Query expansion,
question expectations, colour/object types and adjective binding remain
engineered. The experiment does not test arbitrary-book summarisation,
argument understanding, delayed retention over real elapsed weeks, native
language generation or independent evaluation. It is a bounded but genuine
step from document storage toward provenance-bearing, composable semantic
memory.
