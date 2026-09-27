# Legal Pilot Harness Evaluation

## Evaluated release

- Harness: `tessaris.legal-pilot-harness.v1`
- Execution boundary: local deterministic Legal capability router
- External writes: prohibited
- External delivery: prohibited
- Legal conclusion or representation: prohibited
- Human review: required

## Accepted capabilities

| Capability | Bound evidence | Result |
|---|---|---|
| Secure chat attachment | Encrypted `document-<id>` record; raw filesystem paths rejected | Pass |
| Contract triage | Exact original and extracted-text SHA-256; explainable rules and excerpts | Pass |
| Exact version comparison | Two workspace-isolated protected document identifiers and hashes | Pass |
| Workspace overview | Encrypted Legal matters and document metadata only | Pass |
| Cross-workspace access rejection | Workspace-bound authenticated-encryption context | Pass |
| No autonomous external action | Response and capability receipt both report false authority | Pass |

## Evaluation cases

The automated evaluation proves that the harness:

1. reviews only protected document identifiers and records the exact review receipt;
2. rejects local filesystem paths and other unprotected attachment references;
3. cannot read a protected document from another workspace;
4. compares two exact versions without modifying either;
5. reports open and high-priority Legal matters without inventing advice; and
6. preserves human-review, no-legal-advice and no-external-delivery boundaries.

The focused tests are in
`backend/tests/workflow_capsules/test_aion_legal_pilot_harness_service.py`.

## Claim boundary

This is acceptance of the bounded Tessaris harness and its safety controls, not
an evaluation of legal correctness across jurisdictions. It does not establish
that a general-purpose or specialist model is a lawyer, that templates are
legally approved, or that qualified professional review can be removed. Live
jurisdictional template approval and customer pilot evidence remain release
gates.
