# AION HexCore Cross-Domain Semantic Transfer Report

**Date:** 31 July 2026  
**Procedure:** `procedure_cross_domain_semantic_transfer_58eae51b7d20`  
**Parent:** `procedure_open_relation_argument_memory_189258f3d567`

## Objective

Test whether AION's open semantic memory transfers beyond literary books into
unfamiliar technical, scientific and historical sources. The test requires
open concept and relation induction, reuse of previously learned canonical
relations only when semantically justified, delayed memory-only answering after
process reconstruction, exact provenance, unsupported-question abstention and
a bounded application of technical memory to software-repair reasoning.

## Sources and evaluation status

The frozen sources were the Python Design and History FAQ, NASA's Climate
Change FAQ and the U.S. National Archives' Constitution Questions and Answers.
All local captures are checksum-pinned in the source manifest. Four questions
per source were written by the external publisher, not by the benchmark code.
They are public and their answers were ingested before the delayed evaluation;
the test is therefore evidence of source-disjoint semantic transfer and durable
memory, not contamination-proof independent evaluation.

## Architecture

The execution chain was:

```text
official HTML + checksums
        -> externally authored question/answer recovery
        -> proposal-only open concept/relation/argument induction
        -> exact answer-span and source-hash verification
        -> comparison with the retained literary canonical ontology
        -> reject forced or admitted near-match mappings
        -> persistent HexCore semantic memory
        -> process reconstruction and source closure
        -> memory-only answers with target-memory citations
        -> unsupported-question abstention
        -> CAU promotion or rejection
```

Every source statement remains `reported_by_official_source`; it is not
silently converted into independently verified causal truth. Arguments remain
`reported_argument`. The language provider proposes structures and answers;
HexCore controls source integrity, grounding, persistence, abstention gates and
promotion.

## Results

| Measure | Result |
|---|---:|
| Source-disjoint domains | 3 |
| Externally authored delayed questions | 12 |
| Delayed memory-only accuracy | **91.67%** |
| Weakest-domain accuracy | **75.00%** |
| Mean answer token F1 | 58.63% |
| Invented concepts | 46 |
| Grounded relations | 52 |
| Reported arguments | 15 |
| Defensible prior canonical relations reused | 10 |
| Domains exhibiting prior-relation reuse | 2 |
| Relation-mapping coverage | 100% |
| Unsupported-question abstention | 100% |
| Provenance completeness | 100% |
| Source rereads during delayed evaluation | 0 |
| Restart relearning | 0 |
| Unsafe knowledge commitments | 0 |

Eleven answers cited their target retained memory and exceeded the declared
token-overlap gate. One historical answer cited the correct memory but was
rejected because its wording did not meet the answer-overlap threshold. This
failure is retained rather than being relabelled after inspection.

## Cross-domain abstraction audit

The proposal mapped new technical and scientific relations onto retained
operators including `causally_leads_to`, `includes_or_contains`, `applies_to`
and `is_linked_to`. An audit rejected mappings with no justification and any
mapping whose own explanation admitted it was merely the closest available
operator. Ten mappings survived. No historical relation was forced into the
old ontology solely to satisfy the transfer gate.

## Software-documentation bridge

From retained Python documentation alone, AION explained why an interface
description cannot authorize a repository repair: executable tests can verify
behaviour that an interface declaration cannot. The bridge is explicitly
proposal-only. Existing hidden tests, independent execution, the mandatory
security scanner and CAU remain authoritative. This connects knowledge memory
to software reasoning without weakening the rejected menu-free repair gate.

## Cold control and interpretation

The no-memory control necessarily abstained after source closure. This confirms
that the delayed result depends on persisted semantic memory, but it is not a
competitive reading baseline because the control has no retained evidence. A
future matched control must receive the same raw indexed evidence without the
learned ontology and use the same language/tool budget.

## Verification

Four new regression tests cover frozen source hashes, question recovery,
governed promotion, cross-domain mapping audits, citation-grounded answers,
unsupported abstention and the proposal-only software bridge. Together with
the parent semantic-memory and software-repair tests, **14 focused tests pass**.
The expensive full historical suite was intentionally deferred.

## Claim boundary and next development

This is a bounded cross-domain semantic-memory promotion, not general reading
intelligence or AGI. The sources are public FAQs, question-answer pairing is
explicit, semantic proposals use a strong language substrate and only three
domains were tested.

The next decisive stage should combine open semantic memory with real
repository work: ingest unfamiliar RFCs, architecture documents and bug
reports; invent the required software ontology; localize and propose multi-file
changes; invent executable functional and adversarial security tests; and
measure against a matched no-memory control on hidden repositories. In
parallel, an evaluator independent of development must author delayed questions
over new technical, scientific and historical sources.

