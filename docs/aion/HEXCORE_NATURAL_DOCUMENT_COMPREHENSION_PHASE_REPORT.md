# HexCore Phase 40 - Natural-Document Comprehension and Belief Revision

**Date:** 29 July 2026  
**Status:** Passed and promoted  
**Procedure:** `procedure_natural_document_comprehension_34693b852de2`

## Result

Phase 40 advances the Phase 39 workspace from document ingestion and
cost-aware information routing into scored comprehension. AION now receives a
broad project objective and a collection of prose documents without receiving
the expected claims, subgoal list or answer. It must:

1. identify the active authoritative policy;
2. extract factual claims from natural prose;
3. derive the decision dependencies from the policy;
4. assemble evidence across independent documents;
5. distinguish extraction from acceptance;
6. revise beliefs when a newer authoritative source supersedes an older one;
7. reject a higher-revision but unverified conflict;
8. calculate the project recommendation;
9. cite every material rule and fact;
10. preserve the verified belief revision across restart.

The evaluator's gold claims, expected subgoals and expected recommendation are
never passed into the solver.

## Sealed design

The sealed cohort contains 60 projects across six source-disjoint domains:

- coastal restoration;
- materials laboratory;
- travelling exhibition;
- mountain observatory;
- regional supply programme;
- digital preservation programme.

Each domain uses different state vocabulary, numeric conditions, document
authors and prose forms. Each project includes:

- an obsolete but verified board policy;
- the current verified board policy;
- obsolete factual records;
- later independently verified factual revisions;
- an anonymous revision-99 claim;
- an irrelevant contextual source.

The anonymous document may be extracted as a claim, but must never become the
accepted belief. This tests the distinction between reading a proposition and
believing it.

## Architecture

### Claim extraction

The extractor converts supported factual clauses into normalized
subject-value propositions. Each proposition retains:

- source document identity;
- source file reference;
- sentence locator;
- revision and publication time;
- authority class;
- verification status;
- provenance hash.

Claim extraction is scored independently from final decision accuracy.

### Autonomous project decomposition

The active policy is selected using verification, authority, revision and
publication time. The solver then locates the policy's decision clause and
constructs typed subgoals from its conditions:

- equality constraints;
- lower-bound constraints;
- upper-bound constraints.

The expected field list is evaluator-only. Exact decomposition requires the
discovered dependency set to match the concealed project contract.

### Contradiction and revision

Claims are grouped by normalized subject. Belief selection ranks candidates
by:

1. verification;
2. authority;
3. revision;
4. publication time.

Rejected candidates are retained as superseded claims with an explicit reason:
`unverified` or `lower_authority_or_older_revision`. Therefore, revision 99
cannot defeat a verified revision 2 merely through a larger number.

### Cross-document synthesis

Every induced policy condition is evaluated against the selected current
belief. A recommendation is approved only when all discovered conditions are
satisfied. The final evidence set includes the active decision rule and one
provenance-bearing citation for every material condition.

## Sealed results

| Measure | Phase 40 |
|---|---:|
| Projects | 60 |
| Mean goal success | **100%** |
| Weakest-domain success | **100%** |
| Claim precision | **100%** |
| Claim recall | **100%** |
| Claim F1 | **100%** |
| Exact autonomous decomposition | **100%** |
| Contradiction/revision accuracy | **100%** |
| Complete provenance | **100%** |
| Unverified acceptances | **0** |
| Verified memories committed | **60/60** |
| First-record control success | 43.33% |
| Restart relearning | **0** |

The first-record control uses the first policy and first fact found for each
subject. Its 43.33% success demonstrates that Phase 40 is not winning merely
by extracting a convenient sentence; authority-aware revision materially
changes the result.

## Real-document transfer

The unchanged solver was also tested on two real, independently authored
sources:

- the six-page Tessaris Engine technical overview;
- the SQM/SQI public technical overview.

Four evaluator-only questions covered system role, public claim boundaries,
the SQM/SQI distinction and governed collapse. Section-aware chunking and
diversity-aware retrieval were developed after a first rejected run.

| Real-document measure | Result |
|---|---:|
| Mean anchor coverage | **93.75%** |
| Weakest-question coverage | **75%** |
| Questions with citations | **4/4** |

The initial line-level representation achieved only 50.83% and was rejected.
It fragmented headings, paragraphs and enumerated processes. The promoted
representation preserves sections and retrieves complementary evidence
windows. No evaluator anchor is passed into retrieval.

## Governance and persistence

All verified project beliefs, their rejected alternatives, citations and the
promoted procedure survive a new runtime instance with zero relearning.
Promotion required:

- at least 90% mean decision accuracy;
- at least 85% weakest-domain accuracy;
- at least 90% claim F1;
- at least 90% exact decomposition;
- at least 95% revision accuracy;
- 100% provenance;
- zero unverified acceptance;
- all verified projects retained;
- at least 75% mean real-document anchor coverage;
- at least 60% weakest real-document question coverage;
- citations for every real-document question;
- CAU authorization.

## Claim boundary

This is a substantial but bounded reading result. The sealed prose is
procedurally generated, although its domains, terminology, authors and surface
forms are source-disjoint. The extractor supports a controlled factual and
policy grammar. The real-document evaluation contains only two documents and
four curated questions, and anchor coverage is a retrieval-grounding proxy
rather than human-level semantic equivalence.

Phase 40 does not demonstrate unrestricted reading, arbitrary media
understanding, general commonsense or AGI. The next frontier should expand
source families, infer relations not expressed through the current grammar,
construct multi-hop explanatory models, identify unresolved questions and
learn new document schemas from verified outcomes.

## Reproducibility

- `backend/modules/hexcore/natural_document_comprehension_benchmark.py`
- `backend/modules/hexcore/persistent_learning.py`
- `backend/tests/test_hexcore_persistent_learning.py`
- `results/hexcore_natural_document_comprehension.json`

