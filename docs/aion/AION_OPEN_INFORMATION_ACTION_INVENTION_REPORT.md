# AION Open Information-Action Invention

## Outcome

HexCore promoted `procedure_open_information_action_invention_v1`. When the
existing institutional action vocabulary could not represent variable-horizon
pagination or non-JSON evidence, AION synthesized two new executable typed AST
programs inside a bounded interpreter:

1. `BOUNDED_PAGINATED_GET`
2. `SAFE_LOCALNAME_XML_EVIDENCE`

| Measure | Result |
|---|---:|
| New executable action primitives | 2 |
| Candidate programs criticised | 7 |
| Development outcomes | 2/2 |
| Source-disjoint transfers | 2/2 |
| Pagination authorities | 2 |
| XML authorities | 2 |
| Federal Register records independently enumerated | 29 |
| World Bank observations independently enumerated | 66 |
| Malicious programs rejected | 10/10 |
| Binary/outside-grammar abstention | passed |
| Arbitrary execution / credentials / live writes | 0 / 0 / 0 |
| Later retention credits | 4/4 |

## Residual-driven action invention

The invention trigger was an expressivity residual rather than a task label.
Single-request JSON retrieval could not produce a complete record witness from
a paginated authority, and the JSON interpreter could not recover evidence from
institutional XML. AION generated executable candidates, applied adversarial
properties, rejected unsafe or brittle programs, and committed the surviving
ASTs before source-disjoint execution.

```text
unfamiliar investigation
  -> existing action grammar fails
  -> characterize residual
  -> synthesize typed action ASTs
  -> generate counterexamples
  -> reject brittle/unsafe programs
  -> precommit surviving implementation
  -> development execution
  -> source-disjoint institutional transfer
  -> later public re-execution
  -> retain or reject
```

## Invented bounded pagination

The selected pagination program follows authority-provided continuation
evidence, enforces an eight-page resource ceiling, detects repeated URLs,
deduplicates records by stable identity, and rejects incomplete truncation. Its
candidate history retained three failures:

- trusting a declared total without witnessing records;
- fetching a fixed second page, which fails variable horizons;
- following continuations without a cycle guard.

The surviving implementation handled two structurally different protocols:

- Federal Register: object payload with `results` and `next_page_url`;
- World Bank: array payload with separate `page` and `pages` metadata.

It independently enumerated 29 recent Federal Register records and transferred
without modification to 66 World Bank GDP observations. Duplicate inflation,
cycles, cross-authority continuations and unbounded work were rejected.

## Invented namespace-tolerant XML evidence

The selected XML action rejects DTD and entity declarations, enforces a byte
ceiling, parses with a non-resolving standard parser, normalizes namespace-local
element names and extracts bounded text evidence. Regex extraction was rejected
for nested-markup and entity counterexamples. Exact case-sensitive tag matching
was rejected because it failed namespace and schema transfer.

The promoted implementation recovered `AGENCY` and `SUBJECT` evidence from a
live Federal Register document whose root was `NOTICE`. The identical operator
then transferred to the RFC Editor's substantially larger RFC 9110 XML, whose
root was `rfc`, recovering `title` and `abstract` evidence. This is operator
transfer across institutions and document conventions rather than reuse of one
hard-coded tag path.

## Safety and authority

Ten malicious or invalid action programs were rejected: continuation cycles,
duplicate inflation, unbounded pagination, cross-authority continuation,
external XML entities, DTDs, oversized XML, arbitrary evaluation, shell
adapters and write methods. The interpreter exposes no `eval`, `exec`, shell,
credential or write primitive. Photon-style invention remains proposal-only;
real HTTP responses and HexCore promotion gates remain authoritative.

Both operators were durably committed before their transfer outcomes. After
the independent five-minute boundaries, the persistent outcome learner
re-executed all four institutional contracts. Federal Register pagination,
World Bank pagination, Federal Register XML and RFC Editor XML again preserved
the committed properties, earning 4/4 retention credits and promoting
`procedure_open_information_action_later_retention_v1`. Response-derived result
hashes were unchanged during the short interval, so this demonstrates delayed
re-execution and retention rather than environmental change.

## Verification and boundary

Focused operator and institutional regressions passed 3/3. The live initial
cohort passed all four development/transfer outcomes. No arbitrary code,
credential, unsafe method or live write was used.

This is bounded open information-action invention, not unrestricted program
synthesis or research. The interpreter atoms, authority allowlist, missions,
resource ceilings and promotion gates remain engineered. The next boundary is
recursive action-language expansion: when no existing AST atom can represent a
required transformation, AION must implement a new atom privately, prove its
semantics against generated properties and multiple independent authorities,
and retain it only after delayed transfer without expanding ambient authority.

## Artifacts

- Implementation: `backend/modules/hexcore/open_information_action_invention.py`
- Regression: `backend/tests/test_open_information_action_invention.py`
- Result: `results/hexcore_open_information_action_invention.json`
- Persistent state: `backend/modules/hexcore/data/open_information_action_invention/state.json`
