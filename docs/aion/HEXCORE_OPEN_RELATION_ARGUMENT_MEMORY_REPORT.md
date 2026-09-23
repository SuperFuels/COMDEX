# HexCore Open Relation and Argument Memory — Phase Report

## Outcome

AION completed and promoted its first bounded open-schema relation and argument
learning cycle. No concept list, relation vocabulary, character inventory or
argument schema was supplied.

The system sampled evidence from three complete books, proposed its own
concepts, predicates and argument structures, retained only structures whose
quotations were recoverable, reconstructed the runtime, and answered delayed
questions exclusively from retained semantic memory.

Promoted:

`procedure_open_relation_argument_memory_189258f3d567`

## Results

| Measure | Result |
|---|---:|
| Supplied relation types | 0 |
| Invented concepts | 63 |
| Grounded relations | 50 |
| Invented predicate types | 45 |
| Canonical predicate types after consolidation | 35 |
| Predicate compression | 22.22% |
| Predicate coverage after consolidation | 100% |
| Reported argument structures | 20 |
| Weakest-book relation count | 6 |
| Delayed memory-only questions | 12 |
| Delayed memory accuracy | 100% |
| Provenance completeness | 100% |
| Source files reread during delayed evaluation | 0 |
| Arguments incorrectly marked verified | 0 |
| Unsafe knowledge commitments | 0 |
| Restart relearning | 0 |

## Architectural advance

The prior phase stored supplied attribute relations such as colour-to-object.
This phase removed that relation vocabulary. The proposal layer invented
predicates such as asking, issuing, describing, causing and following from
evidence. HexCore accepted a relation endpoint only when it was grounded
directly in the quotation or through an already accepted concept from the same
evidence span.

The first successful run exposed ontology fragmentation: almost every relation
received its own predicate name. A governed consolidation pass therefore
clustered compatible predicates into canonical operators. It reduced 45
invented predicate types to 35 while retaining:

- every original predicate;
- every concrete relation;
- every source quotation;
- the mapping from original to canonical predicate.

This separates open invention from abstraction. AION can create a specialized
relation when needed, then merge compatible relations without destroying their
original provenance.

## Delayed memory use

After the source files had been closed and HexCore reconstructed, AION answered
12 questions from retained concepts, relations and arguments only. Correctness
required either lexical recovery of the retained object or citation of the
exact target relation plus a substantive natural-language answer. The source
books were not reread.

## Epistemic boundary

All literary arguments remain `reported_argument`, not verified truth.
Likewise, relations are `reported_by_source`. Language models proposed
structures, but exact evidence, persistent memory and CAU controlled
acceptance.

## Remaining limitations

Evidence windows, provider selection, delayed question construction and
acceptance rules remain development controlled. The sources are public and not
contamination-proof. Predicate consolidation has not yet been evaluated by an
independent semantic judge. The next stage should use unfamiliar technical,
scientific and historical documents with independently authored delayed
questions and open concept split/merge decisions.
