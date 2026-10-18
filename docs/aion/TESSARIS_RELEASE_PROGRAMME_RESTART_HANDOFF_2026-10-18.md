# Tessaris release programme restart handoff

Checkpoint: 18 October 2026

This is the authoritative restart note for the Business Vault, cross-platform Node, safe-update, Secure Link, Photon and Revolut programme. It records the exact point reached, what remains, the external inputs required and the order in which work should resume. It does not declare Tessaris production-ready.

## One-minute restart summary

- The 28 Business Vault discovery journeys are complete: 28 passed, zero failed and zero missing.
- Backup, clean-root restore, corruption rejection and coverage of the Business Map, every department map, future departments, Foundation/onboarding, Department Pilots, Train Agent automations/runs and the complete File Cabinet have local proof.
- Static discovery has zero unknown persistence operations and zero critical findings, but the release gate is still correctly closed on 3,941 declared-blocking operations across 100 mixed or unfinished touchpoints.
- The last completed implementation item was the deterministic AION Fabric preview bundle boundary. It is approved only as rebuildable product output; signing and clean-machine qualification remain separate gates.
- No packaged-voice-runtime change was started after that item. That is the exact next local engineering task.
- Windows and Linux candidate archives are reproducible but unsigned and have not run on clean native machines. The macOS candidate is unsigned, unnotarised and unqualified.
- Secure Link and control-plane contracts have useful local foundations, but no production coordination/relay service is deployed.
- The Revolut adapter and Photon ledger contracts have strong local tests, but no real sandbox or live provider transaction has been qualified.
- General release remains blocked by native-machine qualification, publisher identities, production infrastructure and independent assurance.

## Repository and evidence checkpoint

| Item | Checkpoint |
|---|---|
| Authoritative repository | `/Users/kevinrobinson/dev/COMDEX` |
| Branch | `main` |
| Starting commit beneath the working tree | `c170aa7c557899a45438f1287b567e3feda7f234` |
| Working tree | Intentionally very dirty: 1,332 paths at checkpoint. Preserve it; do not reset, clean or bulk-checkout. |
| Current static inventory | 4,627 files; 4,583 declared persistence operations |
| Remaining blocking inventory | 3,941 operations across 100 touchpoints |
| Risk queue | 2,235 high; 1,706 medium; zero critical |
| Discovery state | 28 passed; zero failed; zero missing |
| Unknown writes | Zero |
| Release state | Fail closed; `release_ready=false` |
| Close-out regression | 86 passed, one FastAPI deprecation warning; no failures |
| Source hygiene | `git diff --check` passes |
| Governing LaTeX plans | All three compile successfully |

The dirty tree contains the entire programme, not just the latest slice. Do not infer that every modified or untracked file belongs to one feature, and do not discard or rewrite unrelated paths.

## Governing documents and machine-readable evidence

Read these in this order when work resumes:

1. This handoff.
2. `docs/aion/VAULT_NODE_PHOTON_IMPLEMENTATION_STATUS_2026-10-17.md` for the chronological evidence record.
3. `docs/aion/business-data-triage-current.v2.json` for the exact remaining operation queue.
4. `docs/aion/business-data-touchpoint-audit-current.v1.json` for the current static audit.
5. `docs/aion/business-data-discovery-baseline-current.v1.json` for aggregate discovery evidence.
6. `config/business-data-manifest.v1.json` for the authoritative ownership and release-gate declarations.

The three product plans are:

- `/Users/kevinrobinson/Documents/Tessaris/output/latex/TESSARIS_BUSINESS_VAULT_AND_SAFE_UPDATE_IMPLEMENTATION_PLAN_2026-10-17.tex`
- `/Users/kevinrobinson/Documents/Tessaris/output/latex/TESSARIS_CROSS_PLATFORM_NODE_CONNECTIVITY_AND_UPDATE_PROGRAMME_2026-10-17.tex`
- `/Users/kevinrobinson/Documents/Tessaris/output/latex/PHOTON_BILLING_IMPLEMENTATION_PLAN_2026-10-17.tex`

All three compiled successfully at this checkpoint. Keep the existing Business Vault document open in the editor and edit it in place when its scope changes.

## Completed and evidenced

### Business Vault discovery and customer-data scope

- All 28 end-to-end journeys passed with content-free write evidence.
- The Vault contract covers the Business Map, department maps and intelligence, every present department, dynamically added future departments, Foundation/onboarding sessions and receipts, Department Pilot records, Train Agent automation definitions and run history, business knowledge, Founder Notes, Work & Schedule, Sales, Finance, Marketing, Support, Cybersecurity, File Cabinet records and originals, and registered provider boundaries.
- New departments are not dependent on a fixed UI list. Department discovery, wildcard domain policy, migration coverage and backup/readback use the registry and discovered department identities.
- Application, updater, Node state, Vault and secret-store roots have explicit non-overlap rules.
- Browser/local caches are not accepted as durable business authority.
- Unknown static persistence is zero. A new undeclared writer must continue to fail the release gate.

### Backup, restore and migration proof

- The encrypted snapshot/restore path covers all named continuity surfaces and the complete registered domain catalogue.
- A clean-root restore, semantic readback, corruption rejection and no-plaintext checks exist.
- Migration is copy, verify and retain-source; it must not delete legacy sources merely to pass a test.
- This is strong local proof, not yet cross-machine release qualification.

### Recent blocker reduction

- A2A commerce now fails closed in production until shared platform authentication/replay state is separated from each business's records and originals.
- Legacy backend bootstrap no longer creates or repairs repository-local runtime data roots.
- Proof-of-life mutation controls are disabled in production and require an explicit non-production flag.
- The sealed engineering battery requires an explicit safe external output root and no longer reads repository `.env` secrets.
- The app-local voice worker packaging boundary is classified as rebuildable application output; it accepts no customer audio or transcript.
- The AION Fabric preview build now uses an explicit external output root, rejects application/updater/Vault overlap, closes its dependency set, emits a per-file hash manifest and builds deterministically.

### Cross-platform and commercial foundations

- Common installation layouts, Node health, release-manifest/preflight, updater separation, platform qualification envelopes, dynamic loopback locator, content-free diagnostics and signed entitlement/offline-lease contracts exist.
- Exact current candidate hashes are:
  - Windows x64: `4be8a80c8b75c537d25e2624e69cde63118ba679b6f83e4b6ac77eed1f9ebef9`
  - Linux x64: `8fad279be3d90a1fa1fa9c3399b8c269894d0afc6f16d4d55d14bee8b4f19a46`
  - macOS candidate: `dd301754fa72558a8bef8eb66b0b9b8cc279354075ae0c88a81e534d24f5578d`
- The candidates are not production artifacts. They are unsigned and unqualified.
- The Revolut adapter verifies bounded checkout inputs, official webhook signatures, authoritative order retrieval, replay, out-of-order events, refunds and disputes. No real sandbox/live call has been made.
- Current production dependency audits are locally clean and the major frontend/contract migrations are recorded in the status note. This does not replace signed SBOM/provenance or independent review.

## Remaining programme in the agreed order

### 1. Finish declared persistence blocker reduction

Status: active and next.

Discovery itself is complete, but 100 declared touchpoints are still deliberately blocking. Each must be resolved by one of four honest outcomes:

1. move customer/business authority behind the correct Guardian domain;
2. split mixed customer state from rebuildable product or content-free infrastructure;
3. move disposable build/runtime output outside the application and Vault trees with bounded retention; or
4. prove a narrow content-free/rebuildable exclusion with adversarial tests and then change its manifest gate.

Do not approve a touchpoint merely to reduce the count. Approval requires ownership classification, safe root, negative-content tests, restart/readback or rebuild proof, migration/retention treatment and updated manifest evidence.

#### Exact next task: packaged local voice runtime build assets

Touchpoint: `packaged-local-voice-runtime-build-assets` — 21 blocking operations.

Start with:

- `scripts/aion_voice_build_embedded_runtime_o24a.py`
- `scripts/aion_voice_bundle_staging.py`
- `scripts/aion_voice_materialize_python_o24e.py`
- `desktop/mac/voice/manifest.o23a.json`

Required outcome:

- define an exact product-asset allowlist for Python/runtime/model inputs;
- prevent broad discovery manifests from importing `.runtime`, Vault, customer audio, transcript, prompt, credentials or business files;
- require explicit safe build/output roots and reject application/update/Vault overlap where appropriate;
- emit a deterministic per-file digest manifest;
- scan staged output for secrets and customer-data signatures;
- prove the bundle imports/runs without the development checkout or hidden downloads;
- keep live recordings and transcripts governed only by their separate customer-data touchpoint;
- update the manifest gate only after focused tests and audit evidence pass.

Run the existing voice locks first as the baseline:

```text
.venv/bin/pytest -q \
  backend/tests/workflow_capsules/test_aion_o23b_o23d_voice_bundle_staging_lock.py \
  backend/tests/workflow_capsules/test_aion_o23e_voice_runtime_bundle_strategy_lock.py \
  backend/tests/workflow_capsules/test_aion_o23f_packaged_voice_resolver_lock.py \
  backend/tests/workflow_capsules/test_aion_o23i_staged_worker_paths_lock.py \
  backend/tests/workflow_capsules/test_aion_o23k_voice_latex_documentation_lock.py \
  backend/tests/workflow_capsules/test_aion_o24a_embedded_voice_runtime_build_lock.py \
  backend/tests/workflow_capsules/test_aion_o24b_voice_relocation_hardening_lock.py \
  backend/tests/workflow_capsules/test_aion_o24e_voice_materialize_python_lock.py
```

After that, address `root-research-voice-packaging-capability-and-integration-scripts` — 98 operations — by separating dedicated scripts from the catch-all declaration and applying the same customer-data/product-output distinction.

#### Subsequent blocker-reduction order

Work by ownership boundary, not simply by file count. The largest remaining groups are:

| Operations | Touchpoint | Required split |
|---:|---|---|
| 803 | `hexcore-mixed-learning-memory-and-experiment-store` | Guardian customer learning/audit vs signed models, deterministic caches and bounded research fixtures |
| 493 | `aion-model-research-training-business-evaluation-and-gate-evidence` | Customer evaluation/decision evidence vs product research and rebuildable model artefacts |
| 215 | `aion-games-mixed-player-state-and-derived-simulation-store` | Customer/player authority vs disposable simulation output |
| 177 | `aion-cognition-mixed-sovereign-memory-and-derived-model-store` | Encrypted customer memory vs models/caches/telemetry |
| 139 | `aion-fabric-mixed-runtime-device-and-build-store` | Business/device authority vs external Node state and rebuildable packages |
| 125 | `legacy-remaining-module-customer-state-research-and-runtime-output` | File-by-file ownership classification and retirement |
| 109 | `dimensions-mixed-customer-experiment-and-derived-science-store` | Customer experiments vs derived research artefacts |
| 108 | `aion-equities-mixed-financial-research-and-customer-decision-store` | Private financial decisions vs market/research caches |
| 98 | `root-research-voice-packaging-capability-and-integration-scripts` | Customer media vs product packaging/integration output |
| 91 | `legacy-backend-operator-model-security-and-release-scripts` | Customer/operator evidence vs content-free release tooling |

The full and authoritative queue is the triage JSON, not this top-ten summary.

### 2. Close the common Node and platform abstraction

Status: substantially implemented, not complete.

Remaining work:

- remove residual developer-machine and macOS-only assumptions found in the blocker queue;
- finish adapters for paths, services, key stores, permissions and notifications;
- confirm supported OS/version/architecture baselines;
- ensure every local database/cached runtime caller uses the correct external Node-state or Guardian boundary;
- keep dynamic authenticated loopback ownership and prohibit a public inbound administration port.

Exit evidence: identical common Node contract passes on clean macOS, Windows and Linux machines with no checkout dependency.

### 3. Freeze the production contracts

Status: Node, Guardian and release-manifest V1 foundations exist; Secure Link and production compatibility negotiation remain incomplete.

Remaining work:

- finalise stable Node/Guardian API and schema compatibility ranges;
- freeze device/member identity, pairing, revocation and session replay contracts;
- freeze direct/relay route negotiation and support-lease scopes;
- bind every production artifact to exact signed qualification evidence;
- document migration and minimum-safe-version behavior.

### 4. Establish production release and supply-chain operations

Status: local audits and deterministic candidates exist; production trust chain does not.

Remaining work:

- establish offline root and online threshold release key hierarchy with ceremonies and recovery;
- create isolated CI builders for declared targets;
- regenerate and sign release-commit SBOMs and provenance;
- publish immutable expiring release metadata and a signed artifact repository;
- implement stable/preview/LTS channels, staged cohorts, pause and minimum-safe-version controls;
- connect platform installers to SovereignUpdateService and Guardian preflight;
- conduct clean rebuild and malicious-release exercises.

### 5. Obtain platform publisher authority

Status: external blocker.

Needed from the business:

- Apple Developer ID Application and Developer ID Installer certificates plus an authorised `notarytool` profile. This Mac currently has only an Apple Development identity and no stored `tessaris-notary` profile.
- A verified Windows publisher/code-signing identity and secure signing route.
- Named release-lab signing authority kept separate from build machines.

Do not substitute ad-hoc/self-signed production artifacts.

### 6. Run the portable clean-machine Node proof

Status: candidate kits prepared; execution not complete.

Use `scripts/prepare_node_platform_qualification_kit.py` and the generated fail-closed evidence workspaces. Every mandatory case currently starts `not-run`, which is correct.

Required clean targets:

- clean Apple Silicon macOS machine/VM;
- clean Windows 11 x64 machine/VM;
- clean supported Linux x64 machine/VM.

Run the same create/read/update/backup/restore/export/uninstall/reinstall scenario, native service identity checks, credential-store checks, firewall/no-public-port checks and artifact signature checks. The evidence collector must bind results to the exact artifact hash and size. Only the separate release-lab authority may sign the final qualification envelope.

### 7. Finish the vault-safe macOS Apple Silicon release

Status: open after clean-machine proof and publisher authority.

Remaining work:

- sign every executable and native dependency;
- apply hardened runtime, notarise and staple;
- install Node and Guardian under least-privilege identities;
- qualify recovery point, staged update, injected failure and automatic rollback;
- qualify onboarding, pairing, backup/export, device replacement, uninstall-preserve-data and reinstall;
- conduct a small authorised founder pilot.

Intel/universal support follows only after Apple Silicon is qualified.

### 8. Deploy the minimum Secure Link and control plane

Status: local contracts only; no production service.

Remaining work:

- deploy organisation/device registry, coordination, opaque relay and generic notification broker;
- use outbound-first mutually authenticated transport;
- prove relay operators cannot read business content;
- add route selection, roaming, revocation, replay protection, rate/abuse controls and regional failure handling;
- implement founder-approved, time-limited, scoped and audited support leases with no silent shell access;
- prove a control-plane outage does not remove local business/data access.

Required business input: hosting account, domains/DNS, TLS and key/KMS custody decisions, relay regions and operating ownership.

### 9. Qualify Windows, then Linux/private cloud/Hub

Status: unsigned reproducible previews only.

Windows first:

- signed Windows 11 x64 installer and all executable payloads;
- dedicated least-privilege service identity, DPAPI/Credential Manager custody and firewall adapter;
- Smart App Control, Defender and enterprise App Control tests;
- update/rollback across supported previous versions and clean-machine pilot.

Then Linux/private cloud/Hub:

- declare supported distributions and versions;
- signed DEB/RPM and/or signed OCI route;
- systemd supervision, external data volumes, restart/recovery and digest-pinned images;
- qualify power loss, disk pressure, host migration and primary/standby fencing;
- create Hub provisioning and recovery media.

### 10. Activate Photon and Revolut

Status: ledger, receipt, entitlement, offline lease and adapter foundations exist; provider activation is not complete.

Remaining work:

- deploy the authoritative Photon control-plane ledger and signed price book;
- implement the founder-admin price control within governed minimum/maximum bounds and version every price change;
- finish Usage and billing, wallet balance, receipts, alerts, bundles and ownership-preserving expiry UI;
- provision Revolut sandbox secrets through managed secret custody;
- expose a hosted HTTPS webhook endpoint and verify real signed webhook delivery;
- qualify checkout, authoritative order retrieval, duplicate/delayed/out-of-order events, refunds, disputes and reconciliation;
- run live approval only after sandbox, legal, accounting, refund and operational review;
- preserve read, correct, export, backup, restore and migrate when entitlement expires.

Required business input: Revolut merchant/developer sandbox and later live credentials, approved hosted callback domain, webhook configuration, products/prices, tax/accounting decisions and refund policy.

### 11. Complete independent assurance and field release

Status: open.

Remaining work:

- independent penetration test and software-supply-chain review;
- privacy, legal, AI and relevant sector review for launch regions;
- disaster recovery, key compromise, malicious release and control-plane outage exercises;
- small-business and multi-unit pilots;
- publish support matrix, recovery guide, security contact, vulnerability disclosure, status communications and capability limits;
- resolve or explicitly accept findings before general availability.

## External blockers that cannot be completed from this development Mac

Do not spend another session trying to code around these:

1. Apple distribution certificates and notarisation authority.
2. Windows trusted publisher signing authority.
3. Clean native Windows/Linux/macOS qualification targets.
4. Hosted Secure Link coordination/relay/control-plane infrastructure and production key custody.
5. Real Revolut sandbox/live secrets and a public HTTPS webhook endpoint.
6. Independent security, privacy/legal and supply-chain reviewers.
7. Authorised real-business pilot participants.

## Mandatory restart checks

Use the controlled project environment; `python` is not on this shell path, while `.venv/bin/python` and `.venv/bin/pytest` are available.

Run before the next code change:

```text
cd /Users/kevinrobinson/dev/COMDEX
git status --short
git diff --check
.venv/bin/pytest -q \
  backend/tests/workflow_capsules/test_aion_agent_commerce_protocol.py \
  backend/tests/aion_business/test_legacy_runtime_data_root.py \
  backend/tests/aion_business/test_proof_of_life_runtime_boundary.py \
  backend/tests/aion_business/test_sealed_repository_execution_boundary.py \
  backend/tests/workflow_capsules/test_aion_o24g_app_local_voice_worker_lock.py \
  backend/tests/aion_fabric/test_aion_fabric_packaging.py \
  backend/tests/aion_business/test_business_data_discovery.py \
  backend/tests/aion_business/test_business_data_discovery_campaign.py \
  backend/tests/aion_business/test_business_data_discovery_triage.py \
  backend/tests/aion_business/test_node_release_contract.py
```

Checkpoint result: 86 passed in 31.67 seconds; one existing FastAPI `on_event` deprecation warning.

After changing a persistence boundary:

1. run its focused tests;
2. run discovery/campaign/triage/release-contract tests;
3. regenerate the static audit and triage queue using the scripts' current `--help` contract;
4. verify zero unknown writes, zero critical findings and 28/28 journeys still complete;
5. confirm any reduction is caused by evidence and manifest changes, not exclusions that hide source;
6. update the engineering status note and relevant LaTeX plan;
7. compile the edited LaTeX document;
8. run `git diff --check`.

The audit and triage scripts may intentionally exit non-zero while declared blockers remain. That is a release-gate result, not automatically a tool failure.

## What must not happen

- Do not reset or clean the dirty worktree.
- Do not rerun all 28 discovery journeys unless a journey contract or relevant runtime behavior changes.
- Do not move business data into the app, updater, build or repository tree.
- Do not treat browser storage, shared SQLite or a developer directory as customer authority.
- Do not approve mixed stores without splitting ownership.
- Do not put customer data, prompts, filenames, paths or secrets in release/health/Photon evidence.
- Do not call an unsigned candidate a production installer.
- Do not mark a platform qualified without a clean native run and separately signed evidence.
- Do not activate charging or live checkout before provider, ownership and reconciliation gates pass.
- Do not add permanent remote control or a public inbound administration port.

## Exact pickup instruction

Resume at `packaged-local-voice-runtime-build-assets`. Run the eight listed voice-lock tests, inspect the three build/staging scripts and discovery manifest, add explicit source/output/taint/determinism controls, and keep the touchpoint blocking unless every stated acceptance condition passes. Then regenerate the audit, record the new honest counts and continue through the triage queue before attempting platform signing or hosted activation.
