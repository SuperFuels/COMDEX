# AION Multi-Step Document and Institutional Intelligence

## Outcome

HexCore promoted `procedure_multistep_institutional_intelligence_v1`.
AION received two institutional missions without entity identifiers or final
record endpoints. It discovered official interface evidence, constructed typed
dependency graphs, resolved the required identifiers, committed each graph
before the terminal query, and verified semantic identity across every hop.

| Measure | Result |
|---|---:|
| Institutional domains | 2 |
| Successful dependency chains | 2/2 |
| Supplied identifiers | 0 |
| Supplied final endpoints | 0 |
| Distinct identifiers resolved | 2 |
| Valid committed action graphs | 2/2 |
| Cross-hop identity checks | 2/2 |
| Invalid or malicious chains rejected | 8/8 |
| Credentials / non-GET actions / live writes | 0 / 0 / 0 |
| Later retention credits | 2/2 |

## Institutional dependency graphs

### Corporate disclosure

The mission requested Apple Incorporated's latest annual SEC filing. AION was
not supplied a ticker, CIK, submissions URL or filing record. The public search
provider failed to return usable SEC evidence during the first run. That run
was rejected rather than scored as a pass.

The successor traversed SEC's own public link graph, discovered the EDGAR CIK
lookup form and the documented `data.sec.gov/submissions/CIK##########.json`
contract, queried the name resolver, and identified:

- Entity: `APPLE INC.`
- CIK: `0000320193`
- Required form: `10-K`

Only after committing that identity and expected semantics did it query the
parameterized submissions resource. It recovered accession
`0000320193-25-000079`, filed on 2025-10-31, and verified that the response CIK,
form type, accession and primary-document fields remained mutually consistent.
The values are time-indexed evidence, not timeless facts.

### Federal rulemaking

The second mission requested the newest final rule issued by the Environmental
Protection Agency. AION resolved the agency directory before querying the
document collection:

- Agency: Environmental Protection Agency
- Agency identifier: `145`
- Agency slug: `environmental-protection-agency`

It then parameterized the Federal Register document collection by agency and
rule type, selected the newest returned document number, constructed the detail
request, and verified that the detail response preserved both the document
number and agency identifier. The promotion observation was document
`2026-15634`, *Permethrin; Pesticide Tolerances*. This record is likewise a
time-indexed observation.

## Action-graph contract

Each episode uses a directed acyclic information-action graph:

```text
broad mission
  -> discover official documentation
  -> discover identifier mechanism
  -> resolve institutional identifier
  -> precommit identifier and expected semantics
  -> query parameterized collection
  -> resolve record identifier
  -> retrieve record detail
  -> verify semantic continuity across hops
  -> schedule later reobservation
```

A step cannot execute unless all declared dependencies have produced evidence.
The contract hash covers the mission, ordered action graph, resolved identifier,
target authority and forecast. Terminal results are therefore unable to rewrite
the plan that preceded them.

## Rejection and recovery

The first SEC attempt exposed a genuine infrastructure dependency: the public
search index was throttled and returned no useful official result. The system
did not substitute a hard-coded final URL. It added institution-root traversal,
followed only same-authority public links, located the SEC's own identifier and
API documentation, and resumed the chain. This converts search failure into a
reversible acquisition strategy rather than an unsupported answer.

Eight invalid chain classes were rejected:

1. Hard-coded final URL without identifier evidence.
2. Cross-entity identifier substitution.
3. Official but semantically irrelevant JSON.
4. Unofficial authority domain.
5. Non-GET method.
6. Credential-bearing query.
7. Unresolved dependency.
8. Live-write request.

The result extends the earlier CISA rejection: official provenance and valid
syntax are necessary but insufficient. A valid institutional answer additionally
requires dependency completeness and semantic identity continuity.

## Persistent delayed authority

Both terminal contracts were durably committed with independent five-minute
eligibility boundaries. After the clocks expired, new SEC and Federal Register
requests preserved the committed institutional identifiers and terminal record
identity. Their response hashes happened to remain unchanged during the short
interval, so this establishes independently timed reobservation and retention,
not environmental change. HexCore promoted
`procedure_multistep_institutional_later_retention_v1` with 2/2 credits. No
credit was awarded before the boundary elapsed.

## Verification and boundary

The deterministic focused earned-intelligence stack passed 6/6, and the live
institutional acquisition and later reobservation both passed. Rapidly replaying
all live-web historical tests exposed public-search throttling in older remote
arenas; those availability failures were retained separately rather than
misreported as logic passes. No credential, non-GET request, unsafe execution
or live-repository write occurred.

This demonstrates bounded multi-step institutional intelligence over two real
public authorities. It does not demonstrate unrestricted institutional research,
arbitrary browser operation, legal or investment judgment, AGA or AGI. Target
missions, search-query construction, resource-name grammar, read-only action
primitives and gates remain engineered. The next boundary is open plan-grammar
invention: AION must construct a new information action when the required
institutional dependency cannot be represented by its current search, resolve,
query, select and verify primitives.

## Artifacts

- Implementation: `backend/modules/hexcore/multistep_institutional_intelligence.py`
- Regression: `backend/tests/test_multistep_institutional_intelligence.py`
- Result: `results/hexcore_multistep_institutional_intelligence.json`
- Persistent state: `backend/modules/hexcore/data/multistep_institutional_intelligence/state.json`
