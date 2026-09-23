# AION Shortlist-Free Remote Authority Acquisition

## Outcome

HexCore promoted `procedure_shortlist_free_remote_authority_acquisition_v1`.
AION received one broad mission concerning recent earthquake risk. It was given
no source catalogue, documentation URL or endpoint. It generated a search query,
queried a public index, filtered results by authority and transport security,
read official documentation, discovered callable data feeds, inferred an
observable schema, constructed a typed read-only adapter and transferred it to
a different time horizon.

| Measure | Result |
|---|---:|
| Broad missions | 1 |
| Search queries invented | 1 |
| Supplied source catalogues | 0 |
| Public results inspected | 10 |
| Official documents recovered | 2 |
| Endpoint candidates discovered | 21 |
| Typed remote adapters | 1 |
| Development outcome | passed |
| Source-disjoint horizon transfer | passed |
| Malicious remote candidates rejected | 5/5 |
| Credentials / non-GET actions / live writes | 0 / 0 / 0 |
| Later retention credit | 1, consequence confirmed |

## Rejection-driven source discovery

The configured OpenAI proposal teacher was unavailable because its service
returned HTTP 429. A local proposal model then produced two successive sets of
hallucinated bare government API domains. AION rejected them rather than
constructing an adapter around unsupported claims.

The successful path removed the teacher as authority. AION synthesized the
query directly from the mission, used a public search index, rejected commercial
and non-government results, recovered official U.S. Geological Survey
documentation, and extracted 21 endpoint candidates from that documentation.

## Learned remote contract

The selected contract used:

- Authority: `earthquake.usgs.gov`;
- Method: HTTPS `GET`;
- Credentials: none;
- Development feed: all earthquakes during the previous hour;
- Transfer feed: all earthquakes during the previous day;
- Observables: event count, maximum magnitude and latest event timestamp;
- Required schema: `bbox`, `features`, `metadata`, and `type`.

The live acquisition observed six hourly events and 221 daily events during the
promotion run. The exact values are evidence rows, not timeless claims.

## Delayed consequence

A separate commitment was durably written before the transfer response. A
second same-authority retest was held behind a five-minute wall-clock boundary
and supervised by the continuous real-outcome learner. The later response hash
changed while the committed schema and physical bounds remained valid. HexCore
therefore promoted `procedure_later_confirmed_remote_authority_retention_v1`.
No credit was awarded before the boundary elapsed.

## Boundary

The mission domain, query generator, `.gov` trust rule, GeoJSON meta-grammar and
transfer gate remain engineered. This is one real no-catalogue remote authority
acquisition, not unrestricted web research, arbitrary package installation,
AGA or AGI.

## Artifacts

- Implementation: `backend/modules/hexcore/shortlist_free_remote_authority_acquisition.py`
- Regression: `backend/tests/test_shortlist_free_remote_authority_acquisition.py`
- Result: `results/hexcore_shortlist_free_remote_authority_acquisition.json`
- Pending state: `backend/modules/hexcore/data/shortlist_free_remote_authority/state.json`
