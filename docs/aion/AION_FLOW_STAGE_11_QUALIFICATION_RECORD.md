# AION Flow Stage 11 qualification record

Status: internal engineering qualification complete; independent enterprise release validation remains open.

## Closed security remediations

- `AFLOW-1107R1`: every preparation, approval, execution, run-control, evaluation, template and production operation requires a short-lived, body-bound, replay-resistant signed desktop session and canonical organisation membership. Browser role claims are ignored.
- `AFLOW-1107R2`: execution policy is signed, versioned and persisted by workspace. Browser-supplied policy is ignored. The safe default permits local dry-runs only, with no external writes and no spend.
- `AFLOW-1107R3`: production has no universal fallback encryption key. It resolves a customer-provided secret, configured owner-only key file or platform keyring entry and otherwise fails closed. Development generates its own owner-only machine secret.
- `AFLOW-1107R4`: the production dependency surface has a hash-locked minimal manifest, a signed CycloneDX SBOM and no known advisories in the locked set. Legacy ECDSA and WeasyPrint paths are excluded from this production environment.

## Sustained-load qualification

The signed `AFLOW-1108` run used synthetic content only and made no model calls or external business writes.

| Profile | Production run | Result |
|---|---:|---|
| Large graph | 1,500 nodes, 1,499 edges | Passed; p95 qualification 997.635 ms |
| Parallel routing | 256 fan-out/fan-in routes, 512 edges | Passed; deterministic output; p95 38.646 ms |
| Long-running recovery | 250 atomic checkpoints | Passed; recovered checkpoint 250; p95 write 0.625 ms |

Signed report hash: `f1f1d047cbc628f02be7715fbc2c8f93fcde9fff5b18b99303d4977ecd659263`.

The figures qualify this machine and build; they are not universal performance guarantees. Customer hardware and larger graphs require their own recorded run.

## Internal accessibility and privacy qualification

The Stage 11 Production centre is a labelled modal dialog with semantic buttons, a polite live-status region, initial focus, Escape dismissal and focus restoration. Mobile review remains read-only. Encrypted import restores no authority. Operational telemetry contains counts, hashes and latency buckets rather than workflow content, credentials or customer identifiers. Load evidence contains synthetic identifiers only.

The privacy boundary remains: browser and canvas are untrusted; credentials remain opaque Visual Vault references; customer policy controls disclosure; model output grants no authority; verified adapters and receipts prove external effects.

## Open independent release gates

These items cannot be truthfully self-certified by the implementation team:

1. Independent penetration testing, including provider-specific prompt injection, connector receipt forgery and distributed concurrency.
2. Independent WCAG 2.2 AA audit with keyboard-only, VoiceOver/TalkBack, zoom, contrast and cognitive-accessibility user testing.
3. Jurisdiction-specific GDPR/DPIA, employment, records-retention, AI governance and sector-regulation review for each intended market.
4. Dependency licence review, update-signature review and macOS/phone signing and notarisation using the release owner’s identities.
5. Representative field trials with several real organisations, roles, workspaces, private models, customer-cloud endpoints and recovery exercises.

Consequential remote or enterprise release remains blocked until the applicable independent gates are evidenced and accepted by an authorised customer release owner.
