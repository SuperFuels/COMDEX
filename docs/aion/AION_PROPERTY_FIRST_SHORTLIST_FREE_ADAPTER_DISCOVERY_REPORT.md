# AION Property-First, Shortlist-Free Adapter Discovery

## Outcome

HexCore promoted `procedure_property_first_adapter_discovery_v1`. AION received
three natural-language objectives and real repository artifacts without a
requirement label or candidate-tool shortlist. It formulated an observable
property, searched the operating system's public manual index, ranked candidates
by semantic fit, trust and cost, inspected the selected interface, synthesized
a typed adapter and verified it on development and source-disjoint artifacts.

| Measure | Result |
|---|---:|
| Natural objectives | 3 |
| Observable properties formulated | 3/3 |
| Tool shortlists supplied | 0 |
| Requirement labels supplied | 0 |
| Manual-index candidates discovered | 267 |
| Adapters acquired | 3 |
| Development properties | 3/3 |
| Source-disjoint transfer | 3/3 |
| Malicious candidates rejected | 6/6 |
| Ambiguous-objective abstention | passed |
| Network actions / live writes | 0 / 0 |
| Restart relearning | 0 |

## Discovered solutions

- Structural JSON validity became a successful-parse property; AION discovered
  `jq`, inferred `-e .`, and validated it against Python's independent parser.
- Report length became a physical-line-count property; AION discovered `wc`,
  inferred `-l`, and validated the output through direct text recomputation.
- Exact-literal matching became a fixed-string matching-line property; AION
  discovered `grep`, inferred `-F -c`, and compared it with an independent line
  scan.

The first challenger was rejected. Its macOS help parser did not recognise
grouped short flags and selected `msggrep` instead of `grep`; its trust policy
also treated `/bin/sh` as safe merely because it occupied a trusted path. The
revised challenger learned two reusable constraints: parse compact flag groups,
and distinguish trusted provenance from dangerous capability class. It then
passed without relaxing any outcome or security gate.

## Capability chain

```text
natural objective + unfamiliar artifact
  -> formulate observable property
  -> query public interface catalogue
  -> rank semantic fit, trust and cost
  -> inspect one low-risk interface
  -> synthesize typed read-only adapter
  -> precommit and execute
  -> independent recomputation
  -> source-disjoint transfer
  -> retain or abstain
```

## Boundary

The natural-language property parser, observable-property meta-grammar, trusted
filesystem roots, project cohort and independent Python authorities remain
engineered. This is bounded property-first local adapter discovery, not arbitrary
package installation, remote API acquisition, AGA or AGI.

## Artifacts

- Implementation: `backend/modules/hexcore/property_first_adapter_discovery.py`
- Regression: `backend/tests/test_property_first_adapter_discovery.py`
- Result: `results/hexcore_property_first_adapter_discovery.json`

