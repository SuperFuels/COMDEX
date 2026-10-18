# AION Cross-Domain Remote Authority Transfer

## Outcome

HexCore promoted `procedure_cross_domain_remote_authority_transfer_v1`. The
grounded acquisition method learned during the USGS mission was applied to two
qualitatively different objectives with no endpoint catalogue: public finance
and exploited software vulnerabilities.

| Measure | Result |
|---|---:|
| New remote domains | 2 |
| Successful acquisitions | 2/2 |
| Distinct official authority domains | 2 |
| Supplied source catalogues | 0 |
| Attempt reduction versus actual parent acquisition | 75% |
| Malicious candidates rejected | 5/5 |
| Precommitments | 2 |
| Credentials / non-GET actions / live writes | 0 / 0 / 0 |
| Later retention credit | 2/2 consequence-confirmed |

## Acquired authorities

### Public finance

AION discovered U.S. Treasury Fiscal Data documentation and constructed a
read-only adapter for its fiscal-service API. The accepted response contained
`data`, `links`, and `meta`, with independently observed exchange-rate records.
Three structurally or operationally invalid candidates failed before the valid
authority was reached.

### Software security

The first live challenger incorrectly accepted NIST's favicon
`manifest.json`: it was official and structurally valid JSON but contained no
vulnerability evidence. That run was rejected. The successor added semantic
authority grounding and selected CISA's Known Exploited Vulnerabilities feed,
containing the catalog version, release date, count, and vulnerability records.

This rejection establishes an important constraint:

```text
official domain + valid JSON != relevant authority
```

Endpoint authority requires semantic evidence that can score the mission's
observable property.

## Measured transfer

The parent USGS acquisition required four attempts: one rate-limited OpenAI
proposal, two hallucinated local-model proposals, and grounded public search.
Both new missions reused the retained grounded-search policy immediately,
reducing proposal-path attempts from four to one per mission, or 75%.

## Delayed consequence

Both contracts were committed before later retests. After the five-minute
wall-clock boundaries, the continuous outcome learner independently queried
both authorities again. Their response hashes were unchanged during this short
interval, but both separately timed responses preserved the committed containers
and nonnegative record properties. HexCore promoted
`procedure_cross_domain_remote_later_retention_v1` with 2/2 retention credits.

## Boundary

Missions, query parser, government trust rule, JSON affordance grammar, the
actual-parent cost baseline and promotion gates remain engineered. This is
bounded cross-domain transfer of remote authority acquisition, not general web
mastery, AGA or AGI.

## Artifacts

- Implementation: `backend/modules/hexcore/cross_domain_remote_authority_transfer.py`
- Regression: `backend/tests/test_cross_domain_remote_authority_transfer.py`
- Result: `results/hexcore_cross_domain_remote_authority_transfer.json`
