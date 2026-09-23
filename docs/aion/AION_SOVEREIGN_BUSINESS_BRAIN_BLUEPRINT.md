# AION Sovereign Business Brain — Product and Build Blueprint

Status: canonical strategic build blueprint — Phase 1 partially complete; Phases 2 and 3 implementation complete — 4 September 2026  
Scope: downloadable AION brain + Personal Pilot + Workspace + Boardroom + modular model, harness and compute ecosystem

## 1. Product decision

Tessaris will not compete by owning one foundation model. It will deliver a customer-controlled
**AION brain** that is useful before a premium model is connected and becomes progressively more
valuable as it learns the customer's organisation.

The initial installation is deliberately an **empty governed brain**, not an empty chatbot. It
already contains identity, memory, learning, planning, policy, permission, capability, evidence,
approval and audit machinery. What it does not contain on day one is the customer's private
institutional context. That context is earned through explicit onboarding, authorized connectors,
observed work, corrections and verified outcomes.

Models, inference engines, agent harnesses, evidence providers, business connectors and compute
backends are replaceable modules. AION remains the enduring system of record for what the customer
knows, who may do what, which routes work, and what happened.

The governing flow is:

> Request → active person and space → business context → policy and authority → capability plan →
> model/tool route → Pilot presentation or execution → verification → receipt → bounded learning.

## 2. Product layers

### 2.1 Experience layer

- **Personal Pilot** provides personal communication, tasks, calendar, services, devices and memory.
- **Workspace** provides bounded participation in an employer, client, project or professional engagement.
- **Boardroom** provides organisation-wide briefings, department agents, delegated work, approvals and intervention.
- Television, phone, desktop, car and future device nodes are surfaces, not independent brains.

### 2.2 AION brain layer

The brain owns the stable customer intelligence:

- people, personas, organisations, teams, locations and authority;
- goals, decisions, policies, processes, terminology and operating constraints;
- canonical business entities and relationships;
- private, household, workspace and organisation memory boundaries;
- capability definitions and approval requirements;
- tasks, plans, actions, evidence, outcomes and receipts;
- learned route performance and model/tool evaluations;
- correction, provenance, retention, export and deletion.

### 2.3 Intelligence and capability router

The router must evaluate each request against:

- task type and required capability;
- sensitivity, residency and permitted disclosure;
- active identity, organisation, role and purpose;
- required quality, latency and context size;
- available hardware, providers and current health;
- measured domain accuracy and tool-use reliability;
- cost and energy budgets;
- internet availability and customer preference.

The default route is deterministic local capability, AION knowledge and memory, local model,
public evidence, customer-configured low-cost provider, specialist provider, optional frontier
provider, then an honest limitation or human review. Cloud absence must not remove core operation.

### 2.4 Modular execution layer

Adapters expose versioned contracts for:

- local runtimes such as llama.cpp or Ollama;
- private inference servers and OpenAI-compatible endpoints;
- Gemini and other customer-authorized providers;
- optional premium frontier providers;
- NVIDIA NIM, NeMo and customer GPU infrastructure;
- private cloud, VPC, on-premise and confidential-compute systems;
- retrieval, search and evidence services;
- business systems, communications, files and device capabilities.

No adapter owns the customer's identity, memory, policy or business map.

### 2.5 Customer-owned deployment layer

One signed product must support four deployment profiles:

1. **Personal/local:** laptop, desktop or home server.
2. **Business appliance:** dedicated workstation or small server.
3. **Private cloud:** infrastructure in the customer's chosen provider and account.
4. **Enterprise:** VPC, on-premise cluster, air-gapped environment or approved confidential compute.

The same customer brain must be exportable between these profiles without changing its logical
identity or copying unapproved provider secrets.

## 3. The business map

The business map is a versioned, permission-aware graph rather than a folder of embeddings. Its
initial ontology includes:

- organisation, legal entity, brand, business unit, department, team and location;
- person, role, responsibility, membership, delegation and approval limit;
- customer, lead, supplier, partner and regulator;
- product, service, asset, system, account and data source;
- objective, metric, risk, obligation, policy and decision;
- process, workflow, task, event, dependency and exception;
- document, claim, evidence, source, version and retention rule;
- capability, tool, model, provider, compute target and execution receipt.

Every relationship carries source, confidence, visibility scope, owner, observed time and review
state. Inferred facts are visibly different from authorized records. A model cannot promote an
inference into organisational truth without the relevant evidence or human authority.

### 3.1 Day-one learning journey

1. Create or import the organisation and its legal/operating boundaries.
2. Identify the owner and bootstrap administrators using possession-bound identity.
3. Ask a short adaptive interview about purpose, products, people, locations and systems.
4. Generate a proposed map and an explicit unknowns/conflicts queue.
5. Connect selected read-only sources before requesting write access.
6. Observe normal work and propose workflows rather than silently automating them.
7. Record corrections and verified outcomes.
8. Promote repeated, successful procedures into governed reusable capabilities.

The system must show **what AION knows, how it knows it, what it is unsure about and who may
change it**.

## 4. Learning system

AION uses four separate learning loops:

1. **Memory learning:** facts, preferences, relationships, decisions and corrections.
2. **Operational learning:** successful procedures, tool routes, recovery paths and failure modes.
3. **Routing learning:** measured selection of models, tools and compute for a task class.
4. **Model adaptation:** optional fine-tuning or distillation after sufficient licensed evidence.

The first three loops must work without modifying model weights. No live interaction may trigger
unreviewed training, and private material may enter a training set only through an explicit,
revocable data-use policy.

## 5. Model and artefact independence

AION maintains a signed model catalogue. Each record contains:

- exact model and version, immutable hashes and trusted mirrors;
- source, licence, attribution and commercial-use conditions;
- supported modalities, languages, context and structured-output behavior;
- hardware, memory, inference engine and quantization compatibility;
- domain, safety, tool-use, latency, cost and energy evaluations;
- provenance, vulnerability notices and last-qualified date;
- permitted data classifications and deployment regions.

Hugging Face, NVIDIA and model developers are sources, not roots of trust. The customer can pin
approved versions and retain independently verified packages. A disappearing or changing supplier
must not erase the operational brain.

## 6. Build programme

### Phase 0 — Freeze the sovereign-brain boundary

- [x] `SBB-0001` Declare AION identity, memory, business map, policy, capability and receipt stores provider-independent.
- [x] `SBB-0002` Inventory existing COMDEX/AION components and assign reuse, adaptation or retirement status.
- [x] `SBB-0003` Define forbidden provider ownership: no model adapter may write canonical memory or grant authority.
- [x] `SBB-0004` Publish schemas for Brain Identity, Brain Export, Business Map and Intelligence Route Receipt.
- [x] `SBB-0005` Add boundary tests proving provider removal does not remove customer state.
- [x] `SBB-0006` Record a versioned architecture decision and migration policy.

**Closure:** one customer brain boots with no cloud keys, reports its boundaries and passes a
provider-removal/restart test.

**Closed:** the provider-independent contracts, portable schema bundle, component inventory,
accepted boundary decision and provider-removal/model-swap tests are implemented. The reference
flow compiles with local specialists and no cloud keys. Compilation is explicitly non-executing.

### Phase 1 — Downloadable empty brain

- [ ] `SBB-0101` Build signed installers for Mac, Windows and Linux/server targets.
  - [x] `SBB-0101A` Build the macOS application/package payload and register the installed runtime with launchd.
  - [ ] `SBB-0101B` Sign with an Apple Developer ID, notarise, staple and validate on clean supported Intel and Apple Silicon Macs.
  - [x] `SBB-0101C` Build the Windows developer installer and register the installed runtime with Windows Service Control Manager.
  - [ ] `SBB-0101D` Sign the Windows binaries/installer and validate installation, upgrade, rollback and removal on clean supported Windows systems.
  - [ ] `SBB-0101E` Build signed Linux/server packages with systemd registration for the declared supported distributions and architectures.
  - [ ] `SBB-0101F` Run the complete clean-machine matrix covering offline setup, recovery, update, rollback, backup/restore and removal.
- [x] `SBB-0102` Add hardware profiling and select an appropriate local runtime/model pack.
- [x] `SBB-0103` Create a first-run owner, mother identity and encrypted local vault.
- [x] `SBB-0104` Initialize empty personal, workspace and business-map stores without demo identities.
- [x] `SBB-0105` Add non-technical local, private-cloud and enterprise deployment choices.
- [x] `SBB-0106` Add health checks, automatic recovery, signed updates and rollback.
- [x] `SBB-0107` Add encrypted backup, restore and complete brain export.
- [x] `SBB-0108` Prove offline installation and useful operation without a paid API on the qualified macOS arm64 reference platform.

**Closure:** a clean machine reaches a working local Pilot without a terminal, cloud account or
preloaded customer data; backup/restore reproduces the same logical brain.

**Current evidence:** the provider-free first-run authority, localhost-only graphical setup,
coarse hardware profile, bounded model recommendation, owner and mother identity, six empty
canonical stores, encrypted local vault, customer deployment selection and encrypted signed
brain export/restore are implemented. An integrity-manifested developer-preview archive contains
macOS, Windows and Linux launchers and passes an extracted-package offline initialization test.
The companion Pilot Fabric 0.53 archive now computes and packages its narrow recursive internal
dependency closure. From outside the COMDEX checkout it imports successfully and completes the
local Fabric demonstration with a valid audit chain and verified compact transport, with provider
keys removed. This closes the previous archive-isolation defect without packaging wider COMDEX
intelligence or customer state.

Bootstrap 0.14 adds bounded health supervision and a portable update authority. Candidate releases
must carry a manifest signed by a separately pinned publisher; every declared file is verified and
undeclared, tampered, oversized, symbolic-link and traversal content fails closed. Releases stage
away from the active version, activation changes an atomic version pointer, and a post-start health
failure restores and restarts the last healthy release. The mother identity signs a hash-chained
local update history. Ten focused supervision, rollback, adversarial package and isolated packaging
tests pass. The developer preview deliberately has no production publisher trust anchor.

Bootstrap 0.15 closes the reference-platform offline proof. Its macOS arm64 archive includes a
SHA-256-pinned relocatable CPython 3.13 runtime, exact binary wheelhouse, Ollama arm64 runtime,
Gemma 3 1B manifest and every referenced model blob. The package carries its component licence
records, a 1,718-file integrity manifest and a local verifier. Generated Python bytecode is removed
before sealing and disabled during launch so verification is stable. From a fresh extracted copy,
the package verifies itself, installs its dependencies without an index, creates an owner-bound
brain, encrypted vault, six canonical stores and canonical Boardroom map bridge, and executes a
structured meeting-summary and two-task extraction through the bundled model with OpenAI, Gemini
and Anthropic keys removed. No model or dependency download occurs after the archive is obtained.

The reference macOS arm64 payload is also packaged as a native unsigned component package. It
installs the sealed AION payload under Application Support, provides a normal Pilot Setup
application entry point and registers a per-user launchd agent for a loopback-only, read-only
health/status service. The package deliberately reports its unsigned state: production signing,
notarisation, stapling and clean Intel/Apple-Silicon validation remain separate release evidence.

**Remaining platform gate:** `SBB-0101` still requires signed/notarized installers and clean-machine
qualification for macOS, Windows and Linux/server. Windows and Linux require equivalent sealed
runtime/model bundles before the whole platform matrix—not merely the macOS arm64 reference
platform—can be described as offline-qualified.

Unsigned developer packages now cover Windows x64 and Linux x64. The Windows package installs into
Program Files, keeps customer brain state beneath ProgramData, registers the loopback service with
Windows Service Control Manager and uses an explicit administrator boundary. The Linux package
installs a dedicated unprivileged service account, private state directory and systemd unit with
no-new-privileges, strict system protection, private temporary storage and one declared writable
brain path. These package structures are statically verified, but were built on macOS: Windows
execution/signing and Linux native execution/signing remain unqualified external platform gates.

### Phase 2 — Business-map bootstrap

- [x] `SBB-0201` Reuse the canonical Boardroom container ontology and Business Map source of truth.
- [x] `SBB-0202` Move adaptive onboarding progress from browser-local state into revisioned, resumable mother-brain authority; browser storage is now migration/offline cache only.
- [x] `SBB-0203` Apply confidence, source and review-state enforcement to every legacy relationship, not only newly governed facts.
- [x] `SBB-0204` Add the user-facing map inspection, merge, correction and selective-deletion interface. The existing Boardroom surface now exposes revision-checked owner controls and preserves audit receipts.
- [x] `SBB-0205` Add unknown, contradiction, stale-information, missing-provenance and missing-review-owner queues.
- [x] `SBB-0206` Complete deterministic exact-name entity linking over the existing provenance-preserving, owner-approved document chunks; unapproved claims and unidentified entities are excluded.
- [x] `SBB-0207` Bind the existing files, Gmail, Calendar, CRM/Sales and Xero read routes into one onboarding connector screen and prove their map projections.
- [x] `SBB-0208` Reuse department-scoped map projections and Organisation Authority viewer boundaries; personal data remains outside the business container.
- [x] `SBB-0209` Add retention, legal-hold and confirmed source-revocation behavior, including retrieval withdrawal, entity-link withdrawal, local raw-material deletion and durable governance receipts.

**Closure:** a sample company can be reconstructed from onboarding plus approved sources, and a
restricted user cannot enumerate or infer inaccessible parts of the map.

**Existing Boardroom foundation reused:** `BusinessMapContainer` is already persisted under the
Business Container repository and is consumed by the Boardroom through an exact revision and
payload-hash confirmation. Business Identity, Business Structure, Department Intelligence,
Financial Model, Operating Model and Organisation Authority provide its surrounding ontology.
The earlier browser-local parallel map compiler is already disabled.

**New sovereign integration:** the empty brain now registers the Boardroom repository as the sole
business-map authority. Its sovereign store holds only a binding record, never a copied map. A
new workspace can be initialized as four evidence-empty Boardroom containers, while registering
an existing workspace preserves every byte of its map. Governed fact proposals require source,
confidence and proposer; approve, correct, reject and confirmed-delete operations are revision
checked and emit hash-bound receipts. Queue inspection exposes proposed, stale, missing-source,
missing-review-owner, unknown, conflicting and incomplete department evidence.

**Connector closure:** the existing Boardroom now presents Files, Gmail, Google Calendar,
CRM/Sales and Xero through one non-technical onboarding view. The view reads established connector
authorities rather than creating replacements, shows secret-free health and aggregate projections,
and performs no external write on load. Provider credentials, messages, contacts, calendar titles
and bank details are excluded. The owner must explicitly begin connection; imported material remains
evidence until the existing review boundary promotes it. Provider failure is isolated per card so an
unavailable service does not hide local files or other healthy connections.

### Phase 3 — Unified intelligence contract

- [x] `SBB-0301` Define one provider-neutral request, structured response and streaming contract.
- [x] `SBB-0302` Define deterministic capability, model, retrieval, evidence and agent-harness adapters.
- [x] `SBB-0303` Require declared data disclosure and residency before an external call.
- [x] `SBB-0304` Add route budgets for quality, cost, latency, energy and context.
- [x] `SBB-0305` Emit an Intelligence Route Receipt without storing unnecessary prompt content.
- [x] `SBB-0306` Implement health-aware fallback, circuit breaking and idempotent retry.
- [x] `SBB-0307` Prevent fallback from crossing a privacy or cost boundary.
- [x] `SBB-0308` Route final results into Pilot presentation or governed capability execution.

**Implemented routing closure:** portable JSON schemas now cover the request, structured response,
stream event and adapter manifest. One router accepts deterministic capability, model, retrieval,
evidence and agent-harness adapters. External candidates are ineligible until destination,
residency and disclosed fields are declared; the adapter receives only the named top-level fields.
Every candidate is checked against minimum quality and maximum cost, latency, energy and context.
Failed routes update a persistent circuit state, while request identifiers make replay idempotent
and reject changed payloads. Receipts store request and result hashes instead of raw content.
Successful output is handed either to a Pilot presentation sink or to a separate governed
capability authority that requires an approval receipt; the router itself never grants authority.

**Closure:** the same business task runs through two local models and one optional remote provider,
with equivalent contracts and an inspectable reason for each selection.

### Phase 4 — Signed model catalogue and evaluation fabric

- [x] `SBB-0401` Implement signed model manifests, hashes, licences, mirrors and revocation.
- [x] `SBB-0402` Build hardware compatibility and model-pack installation checks.
- [x] `SBB-0403` Add task, domain, safety, tool-use, latency, cost and energy benchmarks.
- [x] `SBB-0404` Separate public benchmark scores from customer-private outcome scores.
- [x] `SBB-0405` Add champion/challenger routing with bounded canaries and rollback.
- [x] `SBB-0406` Detect regression, drift and provider behavior changes.
- [x] `SBB-0407` Create an administrator catalogue showing qualified, blocked and experimental models.
- [x] `SBB-0408` Mirror only licence-permitted artefacts needed by active deployment profiles.

**Implemented model-catalogue closure:** model versions are immutable records signed by a trusted
Ed25519 issuer and bound to an artefact hash, byte length, licence, mirrors and hardware/runtime
requirements. Installation preflight checks the real artefact, machine profile, engine and
commercial-use permission. A fixed seven-dimensional suite records task, domain, safety,
tool-use, latency, cost and energy results. Repeatable public results remain in the administrator
catalogue while customer outcome scores are stored separately in an owner-only file and are never
projected into administration views. Only compatible models meeting explicit thresholds can
become qualified. Challenger traffic is limited to 20 percent and 1,000 requests, with paired
measurement against the active champion; inferior candidates are rejected. Regression, provider
fingerprint change or signed revocation blocks a model and rolls back an active route where a
previous champion exists. Mirror plans contain only non-blocked, redistribution-permitted models
referenced by active deployment profiles. Model operations never write the canonical business map.

**Closure:** swapping or removing a model does not change business state; an inferior candidate
cannot become the default without passing the customer's acceptance thresholds.

### Phase 5 — Compute and inference plug-ins

- [x] `SBB-0501` Qualify llama.cpp/Ollama-class local inference for personal and small-business systems.
- [ ] `SBB-0502` Qualify a private OpenAI-compatible inference endpoint.
- [ ] `SBB-0503` Build NVIDIA NIM/NeMo deployment and evaluation adapters without NVIDIA lock-in.
- [x] `SBB-0504` Add private-cloud/VPC deployment recipes for customer-owned accounts.
- [x] `SBB-0505` Add Kubernetes scheduling, quotas, observability and scale-to-zero where appropriate.
- [x] `SBB-0506` Add optional confidential-compute/attestation integration through replaceable providers.
- [x] `SBB-0507` Add CPU, Apple Silicon, NVIDIA and later qualified accelerator profiles.
- [x] `SBB-0508` Prove air-gapped, no-paid-AI and premium-enabled operating modes.

**Implemented compute foundation:** local Ollama and llama.cpp-class execution, private
OpenAI-compatible endpoints and NVIDIA NIM-compatible endpoints share the provider-neutral
intelligence contract. Local endpoints are restricted to loopback; remote endpoints require
HTTPS and may contain neither credentials nor query secrets. Credentials are stored only as
vault references and resolved at invocation. Customer-owned deployment recipes declare account
ownership, immutable images, resource limits, secret references, private ingress,
deny-by-default egress, health/metrics surfaces, bounded replicas and optional scale-to-zero.
Confidential-compute routes require a fresh nonce-bound measurement accepted by a replaceable
attestation verifier. CPU, Apple Silicon, NVIDIA and future signed profiles are explicit. Mode
qualification proves a useful local air-gapped route, a no-paid-AI route and optional premium
routes without making paid compute a dependency. A live local \texttt{gemma3:1b} Ollama probe on
the development Apple Silicon machine returned valid structured JSON.

**Open external qualifications:** `SBB-0502` remains open until a real customer-controlled
private endpoint is supplied and measured end to end. `SBB-0503` remains open until an authorized
NVIDIA NIM deployment and NeMo evaluation environment are available; the portable NIM route and
customer-owned deployment boundary are implemented, but no production NVIDIA result is claimed.

**Closure:** one brain migrates between local, customer-cloud and GPU-backed inference without
changing its identity, map, policy or application interfaces.

### Phase 6 — Harness and agent capability market

- [x] `SBB-0601` Define a signed Agent/Capability Package manifest with tools, scopes, tests and limits.
- [ ] `SBB-0602` Sandbox packages and deny undeclared network, file, identity and execution access.
- [x] `SBB-0603` Require dry-run, adversarial permission and outcome tests before activation.
- [x] `SBB-0604` Version and roll back prompts, procedures, tools and policy independently of models.
- [x] `SBB-0605` Add the core department and first industry capability-pack library without copying the customer brain. Real-adapter outcome qualification remains a release gate per pack.
  - [x] `SBB-0605A` Build the first deterministic signed Sales and Lead Response pack.
- [x] `SBB-0606` Add a curated catalogue and later third-party publishing/revenue controls.
- [x] `SBB-0607` Preserve human ownership and accountability for every installed capability.

**Implemented capability-market foundation:** a trusted Ed25519 publisher signs an immutable
package manifest binding the artefact hash, tools, network hosts, file roots, identity scopes,
named execution actions, usage limits, test requirements, department, industry and commercial
terms. Packages containing customer brain or customer data are rejected. Activation requires
passing dry-run, adversarial-permission and outcome suites plus a named accountable human and an
approval receipt. A broker denies every undeclared network, file, identity, tool and execution
request and enforces the manifest's authorization ceiling. Prompt, procedure, tool and policy
versions can be selected and rolled back independently of the model. The administrator catalogue
shows curated, customer and third-party provenance, commercial terms and the accountable owner,
without exposing customer brain content. Revocation or removal ends authority while retaining the
qualification and audit evidence.

**Open capability-market work:** `SBB-0602` remains open for a production OS/container sandbox
that can safely execute arbitrary third-party package code on each supported platform; the current
broker authorizes only declared operations and does not execute untrusted code itself. `SBB-0605`
now contains signed Sales/Lead Response, Marketing Content, Customer Support Triage, Finance
Monitoring, Operations Coordination and Field Services Dispatch packs. Expansion can continue
incrementally; real-adapter outcome qualification remains open per pack. Third-party publishing
terms are represented in the catalogue, but marketplace payment and publisher onboarding remain
part of later commercial operations.

**Closure:** a capability pack can be installed, inspected, constrained, evaluated, revoked and
removed without corrupting memory or expanding its authority.

### Phase 7 — Boardroom at medium-business scale

- [x] `SBB-0701` Extend the business map to multiple entities, locations, business units and geographies.
- [x] `SBB-0702` Connect Boardroom departments and agents to the shared map and router.
- [x] `SBB-0703` Add enterprise identity, role, group and separation-of-duty integration.
- [x] `SBB-0704` Add organization-specific workflows, approval limits and escalation paths.
- [x] `SBB-0705` Add portfolio dashboards for objectives, metrics, risks, work and model expenditure.
- [x] `SBB-0706` Support employees, freelancers, advisers, accountants and directors through bounded workspaces.
- [x] `SBB-0707` Add data-residency, retention and regional provider policies.
- [x] `SBB-0708` Build redacted support bundles and customer-readable audit/export tools.

**Implemented medium-business foundation:** the operating model represents a group, legal
entities, nested divisions and business units, locations, projects, primary and dotted-line
reporting, arbitrary position titles and internal or external engagements. Each entity carries
an explicit existing Boardroom workspace and canonical Business Map reference; bounded
department-route envelopes hand work to the existing department router rather than creating a
parallel company model. Project positions retain objectives, metrics, work, milestones, risks,
team allocation, budget, commitments, actuals, forecast and model expenditure. Portfolio totals
are grouped by currency and unlike currencies are never silently added together.

Enterprise identity subjects resolve to one active person and never derive authority from a job
title. Role capabilities, entity/unit/location/project scopes, approval ceilings, requester versus
approver separation and named escalation paths are evaluated before work proceeds. Employees,
freelancers, advisers, accountants and directors receive projections limited to their scope.
Classification-specific residency and retention plus provider-region allow lists fail closed.
Support bundles contain only counts and hashes; customer-readable audit exports redact sensitive
fields and both require explicit capabilities.

**Production qualification gates:** connect and field-test the identity-subject contract with each
customer's chosen SAML/OIDC/directory provider; validate the portfolio against a real multi-unit
organisation and its currencies; and independently test regional hosting, retention deletion and
legal-hold operations. These are deployment qualifications, not permission for Pilot to invent
authority or combine entities.

**Closure:** one multi-unit test organisation can operate Boardroom while each user sees only their
authorized map, work and evidence across mobile and desktop.

### Phase 8 — Continuous governed improvement

- [x] `SBB-0801` Record correction and verified outcome signals separately from conversation history.
- [x] `SBB-0802` Learn reliable procedure and route preferences by task class.
- [x] `SBB-0803` Add temporal validation so stale success does not remain permanent authority.
- [x] `SBB-0804` Propose automation only after repeated evidence and explicit owner approval.
- [x] `SBB-0805` Build licensed dataset curation, redaction and consent controls.
- [x] `SBB-0806` Permit fine-tuning/distillation only through reviewed, reversible model releases.
- [x] `SBB-0807` Add retention and unfamiliar-transfer tests before learned capability promotion.
- [x] `SBB-0808` Show customers what changed, why and how to reverse it.

**Implemented governed-improvement foundation:** corrections retain hashes and target references
in a store separate from verified outcome receipts and never preserve conversation content.
Task-class route and procedure preferences require at least three fresh independently verified
outcomes and expire for revalidation. Automation proposals require repeated high-quality evidence
on the preferred route, remain without execution authority and bind approval to the exact proposal.
Dataset admission requires an allow-listed licence, consent reference, declared purpose and prior
removal of sensitive fields; its registry stores hashes and counts rather than raw records.

Fine-tuning, distillation and adapter training can enter service only as a named human-reviewed
release with an explicit rollback target and eligible datasets. Promotion requires a genuinely
elapsed retention evaluation and a passing source-disjoint unfamiliar-transfer evaluation. A
customer change view records what changed, why, who authorized it and the supported reverse action.

**Production qualification gates:** the current foundation governs training and promotion but does
not itself provide a GPU training farm or manufacture labelled datasets. Real customer datasets,
evaluators and release artefacts require independent privacy, licence, quality and infrastructure
qualification before deployment.

**Closure:** AION demonstrates measurable improvement on held-out business tasks without hidden
authority expansion, privacy-boundary crossing or irreversible behavior change.

### Phase 9 — Operations, assurance and commercial readiness

- [x] `SBB-0901` Add tenant-safe licensing for free Pilot, Boardroom and Sovereign Fabric editions.
- [x] `SBB-0902` Meter optional compute and premium services without monetizing private content.
- [x] `SBB-0903` Add customer-controlled telemetry and a zero-content diagnostics mode.
- [ ] `SBB-0904` Complete threat modelling, penetration testing and software supply-chain review.
- [ ] `SBB-0905` Complete privacy, employment, sector and AI-regulation assessments for launch regions.
- [ ] `SBB-0906` Define service levels, disaster recovery, incident response and vulnerability disclosure.
- [ ] `SBB-0907` Pilot with one small business and one medium multi-unit organisation.
- [x] `SBB-0908` Publish plain-language ownership, portability and provider-disclosure guarantees.

**Implemented commercial-assurance foundation:** Ed25519-signed licences bind an edition, feature
set, limits and expiry to exactly one tenant and contain no customer content. Optional service
metering records capability, provider, units, cost, currency and a provider-receipt hash while
rejecting prompts, responses, messages, documents, credentials and secrets. Cross-currency totals
remain separate. Telemetry is disabled by default and each diagnostic category requires explicit
customer activation; the accepted diagnostic schema contains component, status, duration and error
code only. Public guarantees state that the customer owns and can export its brain, can replace
models and providers, receives disclosure before external transmission, and does not require a
premium model, token or blockchain for core operation.

**Still open and not paper-completed:** `SBB-0904` requires an independent penetration test and
software-supply-chain review; `SBB-0905` requires qualified legal, privacy, employment, sector and
AI-regulation assessment in each launch region; `SBB-0906` has the service-level, restore-test,
incident and vulnerability-disclosure contract but still needs staffed operational validation;
`SBB-0907` requires real small-business and medium multi-unit pilots. The runtime exposes these as
unsatisfied external release gates.

**Closure:** paid operation is supportable without centralizing customer brains or making a token,
blockchain or premium model mandatory.

### Phase 10 — Commercial adoption, trials and sovereign-compute conversion

- [x] `SBB-1001` Extend tenant-safe licensing into signed Free, Operator, Boardroom, Growth and Sovereign entitlement records without granting Tessaris access to customer data.
- [x] `SBB-1002` Build the bounded full-department trial state machine with time, verified-action and managed-intelligence limits plus a safe review-only fallback.
- [ ] `SBB-1003` Connect a certified live payment provider through the completed opaque-reference billing boundary; exact approval, cancellation, grace and idempotent signed-event receipts are implemented.
- [x] `SBB-1004` Define and implement normalized verified-business-action metering that excludes local tokens, internal retries, deterministic checks and customer-funded provider usage.
- [x] `SBB-1005` Separate local compute, customer-supplied provider expenditure and Tessaris-managed intelligence in policy and metering.
- [x] `SBB-1006` Build the private evidence-backed value ledger with verified work, bounded estimates, separated cost and evidence-quality labels. Customer-visible Boardroom presentation is delivered with `SBB-1007`.
- [x] `SBB-1007A` Add the completed department lifecycle, trial progress, cancellation, capacity, overage approval, downgrade and value-summary controls to the locally authenticated Boardroom; renewal remains exact-term and provider-confirmed through the billing boundary.
- [x] `SBB-1007B` Expose the same content-free commercial summary and exact trial, cancellation, capacity and overage controls to Pilot Mobile through its signed-phone and canonical organisation-membership gateway. The tenant is derived from the active membership; the phone cannot choose an arbitrary tenant or infer a business from a shared surface.
- [x] `SBB-1008` Produce evidence-based capability, capacity and AION Box/rack recommendations from observed workload, concurrency, privacy and availability requirements without invented financial claims.
- [x] `SBB-1009` Build governed whole-brain migration from an existing Level-1 installation into a customer-owned appliance, rack or private-cloud target without changing logical identity. Production target qualification remains a deployment gate.
- [ ] `SBB-1010` Validate packaging, allowances, conversion language, willingness to pay and rack economics through real customer trials before publishing fixed tariffs.

**Decided commercial boundary:** the downloadable sovereign brain is Level~1 and remains useful
without a paid Tessaris model. Local inference and customer-supplied provider keys are not taxed as
AION tokens. Customers pay when AION assumes continuing operational responsibility through
department operators, scheduled/background work, governed execution, managed intelligence,
collaboration, support or dedicated infrastructure. Pilot-to-Pilot and agent-to-agent communication
remain free except for transparently passed-through external carrier costs.

**Adoption sequence:** free customer-owned brain, one complete bounded department trial, private
evidence-backed value report, paid continuous operation, additional capability/capacity, then an
optional migration of the same learned brain into dedicated customer-owned compute.

**Closure:** a new customer can install the free sovereign brain, activate a clearly bounded
department trial, observe verified work and costs, explicitly continue or safely downgrade, and
migrate the same logical brain into dedicated infrastructure when measured demand justifies it.

**Implemented state and accounting foundation:** signed version-two entitlements cover Free,
Operator, Boardroom, Growth and Sovereign editions, enforce exact tenant/feature/limit boundaries,
contain no authority over customer information, and preserve ownership/export/recovery capabilities
even when a paid entitlement is missing or expired. A department trial records its exact consent,
period, verified-action ceiling, managed-intelligence ceiling, renewal terms and hashed receipts.
Reaching a limit enters a useful review-only state: enquiry intake, deterministic routing,
agent-to-agent exchange and preparation for human review remain available while managed inference
and autonomous external action stop. The meter counts verified business actions, never internal
reasoning, retries, deterministic checks, local tokens or customer-provider tokens. Local,
customer-funded and Tessaris-managed costs remain separate by currency. A private value ledger
separates verified, estimated and inferred evidence and refuses unsupported generated-revenue
claims. Twenty focused entitlement, lifecycle, accounting and value tests pass.

**Signed capability-pack evidence:** the first Sales and Lead Response package is a deterministic
archive containing independently versioned prompt, procedure, tool declaration and policy. Its
manifest is Ed25519-signed, declares no copied brain or customer data, has no default network
authority and cannot become active before dry-run, adversarial-permission and outcome gates plus
an accountable owner approval. A development signature proves the mechanism; the release
publisher key remains a production gate. Further specialist packs remain demand-led additions.

The library now adds five further deterministic packs: Marketing Content, Customer Support
Triage, Finance Monitoring, Operations Coordination and Field Services Dispatch. Every pack has a
tailored purpose, read set, reversible draft operation, explicit external action and forbidden-
claim policy. All default to preparation for review, contain no credential or network destination
and remain installed-but-unqualified until their own three qualification gates pass.

**Customer-visible control:** the main Boardroom dashboard now mounts a collapsible Departments,
Usage and Value panel immediately below the Business Map. It reads a private content-free mother-
brain summary, shows active/review-only/paid department state, verified-action and managed-cost
progress, and evidence-quality-labelled value ranges. It permits an explicit bounded thirty-day
trial with automatic renewal disabled and requires confirmation before cancellation. The API also
enforces separate approval before overage can be enabled.

**Payment and sovereign-compute evidence:** the billing boundary stores only opaque vault
references, binds approval to exact visible terms, makes provider events signature-verified and
idempotent, and retains normalized receipt hashes without card details or provider secrets. A live
certified payment-provider adapter remains open. Capacity selection now derives Level 1, AION Box,
single-GPU rack or private-cluster recommendations from observed concurrency, throughput,
inference volume, privacy, topology and availability rather than employee count. Short evidence
windows are labelled provisional, no vendor is silently selected and no financial saving is
invented. Governed migration creates an encrypted complete export, restores it into a staged
customer-controlled target, verifies health and logical identity, requires separate activation,
retains the source for recovery and supports receipt-bearing rollback.

## 7. Relationship to existing programmes

- `AION_FLOW_VISUAL_INTELLIGENCE_STACK_BUILD_CHECKLIST.md` is the canonical nested programme for
  the Glyph canvas, model/harness/compute composition and governed multi-model execution. It spans
  the implementation concerns in Sovereign Brain Phases 3--6 without changing their closure gates.
- `PILOT_UNIFIED_MOBILE_APP_MASTER_BUILD_CHECKLIST.md` remains the canonical phone, Personal,
  Workspace, Boardroom and communications delivery programme.
- Existing AION cognition, learning, memory, provider routers and capability registries are reuse
  candidates. This blueprint does not authorize overwriting or collapsing them before inventory.
- Boardroom remains the first rich business application over the brain.
- Pilot Fabric remains the device/surface and governed action fabric.
- GlyphNet remains the private person-to-person and agent-to-agent communications substrate.
- GlyphChain may later anchor selective non-identifying proofs; it is not required for inference.
- PHO, wallets and speculative economic controls remain hidden until separately governed and reviewed.

## 8. Commercial packaging

- **Pilot Free:** customer-owned personal brain, local core capabilities and optional user-supplied providers.
- **Boardroom:** paid business agents, connectors, workflows, evaluations and approval controls.
- **Tessaris Sovereign Fabric:** customer-controlled private deployment, enterprise governance,
  model/compute administration, support and service levels.
- **Optional consumption:** premium models, managed GPUs, specialist capabilities and verified transactions.

Tokens or blockchain assets are not the initial adoption dependency. They may later support
marketplace settlement, inter-organisation proof or capability economics after the network and
regulatory case are established.

## 9. Immediate build order

The first executable sequence is:

1. Close Phase 0 and freeze the brain/provider boundary.
2. Build the clean downloadable empty-brain installer and export format.
3. Implement the versioned business-map core and onboarding proposal flow.
4. Consolidate current provider routers behind one intelligence contract.
5. Add signed model manifests and the first customer-specific evaluation suites.
6. Qualify local, private endpoint and NVIDIA-backed compute as interchangeable targets.
7. Connect the resulting brain to the existing Personal, Workspace and Boardroom surfaces.

No model marketplace, token system or large-enterprise customization should precede these
foundations. The first strategic proof is not that AION can call many models. It is that a customer
can remove every model provider, preserve the brain, connect a replacement, and continue operating.
