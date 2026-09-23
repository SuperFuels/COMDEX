# AION Flow formal threat model and dependency review

Status: AFLOW-1107 review completed on 4 September 2026. Remediations R1--R4 and AFLOW-1108 are now implemented; independent release validation remains open.

## Security objective

AION Flow must allow a customer to assemble replaceable models, evidence, harnesses and business capabilities without allowing the canvas, a model, a template, an imported graph or a connected provider to acquire authority. The mother brain remains the authority, memory and receipt boundary.

## Protected assets

- Customer Business Map, memories, files and private operational context.
- Visual Vault credentials, provider tokens and private endpoint details.
- Canonical people, roles, workspace membership and organisational boundaries.
- Exact approvals, workflow revisions, execution receipts and learning evidence.
- Customer compute budgets, residency rules and connected-system authority.
- Publisher identities, template signatures and application update packages.

## Trust boundaries and untrusted inputs

The desktop canvas, mobile reviewer, browser requests, workflow JSON, imported packages, model output, retrieved evidence, templates, provider responses and connector payloads are untrusted. The canonical workspace and Organisation Authority stores, mother-brain signing identity, encrypted vault and verified capability adapters are trusted only within their explicit responsibilities. A model response is never evidence of identity, permission, execution or success.

## Threat analysis

| Threat | Attack path | Implemented control | Residual decision |
|---|---|---|---|
| Tenant or role forgery | Browser claims `owner` or another workspace | Every AION Flow mutation and private read now requires a short-lived, body-bound, replay-resistant signed session followed by canonical workspace and Organisation Authority resolution; browser role labels are ignored | Independent multi-user penetration testing remains required |
| Graph resource exhaustion | Deep, cyclic, huge or malformed graph reaches hashing, migration or persistence | Depth, item, scalar, node, edge and encoded-size ceilings; typed node/edge validation; invalid graphs fail before hashing; signed synthetic large/parallel/recovery qualification completed | Distributed and lower-spec customer hardware must run its own qualification |
| Revision race | Two editors commit the same base revision concurrently | Inter-process exclusive lock plus optimistic revision comparison and atomic replacement | Distributed/customer-cloud commits require a transactional shared store |
| Encrypted-import abuse | Oversized ciphertext, invalid base64 or attacker-selected crypto metadata consumes resources | Strict schema/KDF/cipher allowlist, base64 validation, salt/nonce/ciphertext bounds, minimum password length, authenticated AES-GCM and constant-time graph-hash comparison | Password recovery is intentionally impossible; enterprise KMS import remains future work |
| Embedded credentials | Template or graph contains an API key instead of a vault reference | Recursive secret-shaped field detection, redaction, package size ceiling and opaque `vault://` bindings outside signed templates | A full data-loss-prevention scanner is still required for arbitrary free text |
| Template tampering | Modified or replaced template version | Ed25519 signature verification, immutable version conflict, pin/rollback/quarantine/revoke controls | Third-party marketplace remains disabled pending publisher and dependency attestation |
| Approval replay or scope change | Old approval is reused after graph changes | Exact scope and review hashes, expiry/revocation support, separation-of-duty rule and fresh receipt | Approver identity must be bound to a signed trusted-device session across every execution endpoint |
| Prompt/model injection | Model output asks for more data or an undeclared action | Models have no intrinsic capability; graph admission, declared fields, disclosure plan, deterministic validation, approval and connector verification remain separate | Red-team corpus and provider-specific injection benchmarks remain required |
| Data exfiltration | Route sends restricted fields to an external model/provider | Declared boundary fields, classification, encryption, residency, destination and disclosure checks; zero-content telemetry; signed persisted workspace policy overrides browser policy | Provider-specific red-team and customer policy review remain required |
| False success | Model or connector claims an action occurred | Governed capability adapters and normalized receipts distinguish proposal, execution and verified outcome | Every new connector still requires provider-specific receipt qualification |
| Supply-chain compromise | Vulnerable application or build dependency | Minimal hashed production lock, signed CycloneDX SBOM, advisory scan, upgraded Electron packager and API/security dependencies; legacy ECDSA/WeasyPrint excluded | Independent licence, provenance and update-signature review remains release work |

## Adversarial verification added

The automated security suite now proves that malformed node and edge records, unsafe scoped identifiers, non-list graph collections, excessive nesting, cyclic structures, oversized scalar content, unsupported encryption headers, invalid base64, oversized encrypted transfers, weak import passwords, dangling edges, duplicate node identities, stale revisions, cross-workspace access and forged role claims fail closed. Private templates reject nested password, token, authorization, private-key and API-key fields before signing.

## Dependency review

- Desktop production and build dependency audit: zero known advisories after upgrading `electron-builder` from 24.13.3 to 26.15.3 and refreshing its lock file.
- Minimal Python product lock: zero known advisories after upgrading FastAPI, Starlette, Click, IDNA, python-dotenv and python-multipart.
- Broader backend manifest: upgraded aiohttp, cryptography, requests, urllib3, Pillow, pyasn1, WeasyPrint and their compatible dependencies. Two upstream areas remain without a complete patched route in the current dependency family: the ECDSA implementation used transitively by legacy JWT support and one WeasyPrint advisory. They must be isolated from untrusted verification/rendering inputs or replaced before an exposed enterprise release.
- The all-purpose developer/research environment is not a production bill of materials. It includes large ML and document toolchains, currently including advisories in Torch and related development packages. A production image must install only the product lock and feature-specific extras, never clone the development environment.

## Release gates created by this review

1. Keep the current API loopback-only; do not expose it directly through a VPN, public listener or customer network.
2. Disable live consequential AION Flow execution in remote and multi-user builds until prepare, approve, execute, run-view/control, evaluation and template lifecycle operations all resolve a signed session through canonical authority and persisted policy.
3. Replace the development fallback encryption key with a generated customer secret or platform keystore secret during installation; startup must fail closed in production if it is absent.
4. Produce a minimal, hashed production dependency lock and signed SBOM; isolate or replace the remaining ECDSA and WeasyPrint paths.
5. Commission independent penetration testing, secrets scanning, dependency licence review and update-signature verification before enterprise field deployment.
6. Sign and notarize the macOS package with a Developer ID Application identity; the local qualification build completed but correctly reported that no suitable Developer ID certificate was available.

The threat model and internal remediations are complete as engineering artifacts. They do not certify the product as independently penetration-tested or enterprise-release-ready. AFLOW-1109 remains open for independent accessibility, privacy, regulatory, security and representative field qualification, and those release gates cannot be waived by a model or canvas policy.
