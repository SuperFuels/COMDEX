# HexCore Phase 39 — Cost-Aware Open-Document Reasoning

**Date:** 29 July 2026  
**Status:** Passed and promoted  
**Procedure:** `procedure_cost_aware_open_docs_09c260698e08`

Phase 39 gives HexCore a governed open-document workspace. From a broad
objective, AION identifies the active policy, derives the information required
for a decision, and chooses among verified memory, source retrieval,
deterministic tools, user clarification, safe probing and abstention.

The information-action utility is:

`expected information gain - 0.25 * action cost - epistemic/operational risk`

Every accepted result retains source identity, revision, authority,
verification status, locator and provenance. High-revision anonymous claims
cannot supersede lower-revision authoritative evidence merely because their
revision number is larger.

## Sealed results

The sealed cohort contained 40 projects across harbor, laboratory, archive,
supply and observatory domains.

| Measure | Result |
|---|---:|
| Mean decision success | **100%** |
| Weakest-domain success | **100%** |
| Information-action routing accuracy | **100%** |
| Mean selected information cost | 4.85 |
| Mean exhaustive-policy cost | 25.50 |
| Cost reduction | **80.98%** |
| Complete provenance | **100%** |
| Unverified rumor acceptances | **0** |
| Verified outcomes committed | **40/40** |
| First-document control success | 75% |
| Restart relearning | **0** |

The production ingestion path also extracted and indexed a six-page Tessaris
PDF and the SQM/SQI Markdown technical overview, producing 119 chunks and five
traceable retrieval citations. This was an extraction and citation smoke test,
not a scored claim of complete document comprehension.

All 44 HexCore regression tests pass. The next frontier is scored,
source-disjoint natural-document comprehension with verified claim extraction,
cross-document synthesis, contradiction revision and autonomous project
decomposition.

## Claim boundary

The sealed documents, need classes, action utilities, tool contracts and
decision oracle remain engineered. Phase 39 is not unrestricted web research,
general agency or AGI.

## Reproducibility

- `backend/modules/hexcore/cost_aware_open_document_benchmark.py`
- `backend/modules/hexcore/persistent_learning.py`
- `backend/tests/test_hexcore_persistent_learning.py`
- `results/hexcore_cost_aware_open_document.json`

