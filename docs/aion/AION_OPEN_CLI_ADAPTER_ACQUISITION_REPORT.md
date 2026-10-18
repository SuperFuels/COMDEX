# AION Open CLI Adapter Acquisition

## Outcome

HexCore promoted `procedure_open_cli_adapter_acquisition_v1`. When no retained
adapter could execute three verification requirements, AION inspected locally
published CLI help, inferred typed read-only argument contracts, security-
scanned them, executed development properties, and transferred the contracts to
different repository artifacts.

| Measure | Result |
|---|---:|
| Public interfaces discovered | 3 |
| Typed adapters invented | 3 |
| Development properties passed | 3/3 |
| Source-disjoint transfers passed | 3/3 |
| Malicious adapters rejected | 6/6 |
| Attempt reduction versus cold search | 66.67% |
| Network actions / credentials | 0 / 0 |
| Unsafe executions / live writes | 0 / 0 |
| Restart relearning | 0 |

## Acquired interfaces

- `xmllint`: a non-networked XPath adapter for XML/SVG root-structure evidence.
- `file`: a brief MIME-type adapter for artifact classification.
- `openssl dgst`: a read-only SHA-256 adapter checked against independent
  byte-level recomputation.

No executable path or argument template was supplied to the inventor. It
located installed tools, captured their published interfaces, matched required
semantics to supported flags, precommitted the resulting contract, and executed
only after the security policy accepted the typed argument vector.

Candidate contracts involving output files, signing keys, shell execution,
network URLs, unapproved executables or write-enabled modes were rejected before
execution.

## Capability chain

```text
valid verifier contract
  -> detect missing adapter
  -> inspect published tool interfaces
  -> synthesize typed read-only argv
  -> reject privileged variants
  -> execute a development property
  -> transfer to an unrelated artifact
  -> retain and reconstruct without relearning
```

## Boundary

The tool shortlist, requirement vocabulary, hidden semantic properties and
sandbox policy remain engineered. This phase did not install packages, acquire
credentials or discover remote APIs. It demonstrates bounded public-interface
adapter acquisition, not unrestricted environment mastery, AGA or AGI.

## Artifacts

- Implementation: `backend/modules/hexcore/open_cli_adapter_acquisition.py`
- Regression: `backend/tests/test_open_cli_adapter_acquisition.py`
- Result: `results/hexcore_open_cli_adapter_acquisition.json`

