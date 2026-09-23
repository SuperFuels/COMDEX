# AION Flow — Visual Intelligence Stack Build Checklist

Status: Stages 0--10 complete; Stage 11 engineering complete with independent release validation open — 4 September 2026  
Scope: Glyph workflow canvas + sovereign AION brain + replaceable models, harnesses, evidence,
compute and governed capabilities

This checklist extends the existing Glyph-based workflow editor. It does not create another canvas
or replace the current Flow Control, Tools, Text Parser, AI, Apps or Custom Logic sections. The
existing **Add a step** interface receives a new top-level **Intelligence Stack** section and the
existing AI modules are migrated into it where appropriate.

The product proposition is:

> AION Flow is a sovereign visual intelligence orchestration system: plug-and-play models,
> harnesses, evidence, compute and real actions, while the customer's AION brain retains identity,
> memory, policy, authority, verified outcomes and learning.

## Non-negotiable operating model

AION is not an ordinary first or last node. It encloses every runnable graph:

**AION admission → permitted context/evidence → specialist intelligence → bounded deliberation →
AION policy/approval → capability execution → verification → receipt/learning**

- Model output is a proposal, never authority.
- Drawing, saving or compiling a graph never executes it.
- Agreement between models is not evidence.
- Every external edge discloses what leaves, where it goes, residency and encryption.
- Every loop has iteration, time, cost and failure limits.
- Removing a provider cannot remove customer identity, memory, policy or business knowledge.

## Catalogue structure in “Add a step”

The new **Intelligence Stack** category should contain these searchable subgroups:

1. **AION Brain** — admission, identity, scoped memory, business map, policy and receipt.
2. **Models** — local models, private endpoints and explicitly connected provider models.
3. **Harnesses** — prompts, schemas, procedures, tools and domain capability packs.
4. **Compute** — this device, another AION node, private server, VPC, GPU or provider API.
5. **Evidence** — approved files/systems, retrieval, public evidence and deterministic validators.
6. **Deliberation** — critic, compare, rank, debate, vote, reconcile and bounded refinement.
7. **Governance** — disclosure, redaction, policy, approval, human review and budget gates.
8. **Action & Verification** — capability execution, observe, test, verify, receipt and outcome learning.

Each module card must show local/private/external location, required credentials, data classes,
estimated cost, risk, approval status and whether it can cause an external effect.

The existing double-click **Node Editor** is the canonical configuration surface. Intelligence
nodes use its current Input / Parameters / Output structure rather than introducing a separate
settings application. The editor stores safe configuration and opaque vault references; it never
stores raw API keys, passwords, provider tokens or private model credentials in the canvas.

## Stage 0 — Sovereign foundation

- [x] `AFLOW-0001` Declare provider-independent canonical brain stores.
- [x] `AFLOW-0002` Prevent model adapters from granting authority or writing canonical state.
- [x] `AFLOW-0003` Publish Brain Identity, Brain Export, Business Map and Route Receipt schemas.
- [x] `AFLOW-0004` Implement the non-executing Sovereign Flow compiler.
- [x] `AFLOW-0005` Require one AION ingress and one AION receipt boundary.
- [x] `AFLOW-0006` Require policy before capability execution and approval before consequential action.
- [x] `AFLOW-0007` Require external disclosure, residency and encryption metadata.
- [x] `AFLOW-0008` Enforce bounded consensus/refinement configuration.
- [x] `AFLOW-0009` Prove provider removal, model replacement and provider-free restart.
- [x] `AFLOW-0010` Publish the public Pilot “How the second brain works” explanation.

**Closure:** complete. The contracts, compiler, schema bundle, architecture decision, component
inventory, public explainer and automated boundary tests are implemented.

## Stage 1 — Intelligence Stack catalogue and canvas UX

- [x] `AFLOW-0101` Add **Intelligence Stack** to the existing Add-a-step category rail.
- [x] `AFLOW-0102` Add the eight subgroup filters and unified module search.
- [x] `AFLOW-0103` Create visually distinct glyphs for brain, model, harness, compute, evidence,
  deliberation, governance, capability and verification nodes.
- [x] `AFLOW-0104` Show local, customer-cloud and external-provider badges on cards and canvas nodes.
- [x] `AFLOW-0105` Show credentials, permissions, risk and approval requirements before insertion.
- [x] `AFLOW-0106` Add searchable filters for modality, domain, location, licence, cost and maturity.
- [x] `AFLOW-0107` Add keyboard navigation, focus management and accessible module descriptions.
- [x] `AFLOW-0108` Add node configuration drawers without exposing provider secrets in browser state.
- [x] `AFLOW-0109` Preserve autosave, undo/redo, zoom, copy/paste and existing workflow behavior.
- [x] `AFLOW-0110` Add a compact legend showing the AION boundary and data-disclosure edges.
- [x] `AFLOW-0111` Make double-click open the existing full Node Editor for every Intelligence Stack node.
- [x] `AFLOW-0112` Generate the Node Editor fields from each module's signed configuration schema.
- [x] `AFLOW-0113` Preserve Input Schema, Input Table, Input JSON, Parameters, Settings, Output Schema,
  Output Table and Output JSON inspection for intelligence nodes.
- [x] `AFLOW-0114` Add inline validation, safe defaults, contextual help, test-configuration and reset controls.

**Closure:** complete in the existing Glyph canvas and Node Editor. A user can add and configure
every node family through the existing modal on desktop and tablet without breaking existing Glyph
workflows. Raw credential-shaped values are rejected, vault-backed fields accept opaque references
only, and consequential execution remains disabled until governance and approval are present.

### Intelligence-node editor requirements

The editor adapts its Parameters and Settings tabs to the selected node family:

| Node family | Configurable fields |
|---|---|
| AION Brain | active identity/space, memory scope, business-map query, purpose and retention |
| Model | model/version, modality, temperature, context/output limits, structured-output mode and tools |
| Harness | instruction package, schema, examples, procedure version, allowed tools and rollback version |
| Compute | local/node/private-cloud/provider target, region, queue, timeout and resource ceilings |
| Evidence | source bindings, query, freshness, provenance, cache and required confidence |
| Deliberation | participants, roles, independence rules, judge/validator, exit criteria and loop budgets |
| Governance | data classes, redaction, disclosure, residency, policy, approver and expiry |
| Capability | exact action, target system, idempotency, risk, compensation and approval requirement |
| Verification | expected outcome, observer, timeout, retries, evidence and receipt fields |

The Input and Output panes must show real schemas before execution, sample or simulated data during
dry-run, and provenance-labelled results after execution. The **Execute step** control remains
disabled for consequential nodes until policy, authority and approval requirements are satisfied.

## Stage 2 — Provider-neutral model catalogue

- [x] `AFLOW-0201` Define the signed model-node manifest and immutable model/version identifier.
- [x] `AFLOW-0202` Register local llama.cpp/Ollama-compatible models through adapters.
- [x] `AFLOW-0203` Register OpenAI-compatible private endpoints without assuming a named provider.
- [x] `AFLOW-0204` Add optional Gemini, OpenAI, Anthropic and other approved adapters.
- [x] `AFLOW-0205` Add NVIDIA NIM/NeMo and customer GPU endpoint descriptors without lock-in.
- [x] `AFLOW-0206` Record modalities, context, structured output, tools, languages and domain strengths.
- [x] `AFLOW-0207` Record licence, commercial-use, attribution, source, hashes and revocation state.
- [x] `AFLOW-0208` Display hardware compatibility, estimated latency, cost and energy.
- [x] `AFLOW-0209` Distinguish qualified, experimental, blocked, unavailable and deprecated models.
- [x] `AFLOW-0210` Reject missing, altered, revoked or policy-incompatible model manifests.
- [x] `AFLOW-0211` Add a Node Editor credential selector that creates or chooses an opaque mother-vault binding.
- [x] `AFLOW-0212` Add a connectivity/model-list test that returns only bounded health metadata to the editor.
- [x] `AFLOW-0213` Redact secret-shaped values from canvas state, autosave, logs, receipts, exports and previews.
- [x] `AFLOW-0214` Add key rotation, binding replacement and revocation without editing every referencing workflow.

**Closure:** the same model node contract can target one local model, one customer-owned endpoint
and one optional provider, with no provider-specific data inside the workflow definition.

The Node Editor now lists only safe binding metadata, can move a newly supplied credential directly
into the encrypted mother-brain vault and saves only its stable `vault://model/...` reference in the
graph. Raw credentials are cleared from the form, are never returned by the API and cannot enter
canvas state, autosave, workflow history, logs, previews, exports or receipts.

## Stage 3 — Compute and hosting nodes

- [x] `AFLOW-0301` Add **This mother brain** and **Local AION node** compute targets.
- [x] `AFLOW-0302` Add customer server and private OpenAI-compatible endpoint targets.
- [x] `AFLOW-0303` Add customer-owned AWS, Google Cloud, Azure and compatible VPC targets.
- [x] `AFLOW-0304` Add NVIDIA, Prem and other qualified compute adapters as replaceable options.
- [x] `AFLOW-0305` Add region, residency, accelerator, memory and network-policy settings.
- [x] `AFLOW-0306` Add maximum spend, time, energy and concurrency budgets.
- [x] `AFLOW-0307` Add health, capacity, queue, circuit-breaker and scale-to-zero state.
- [x] `AFLOW-0308` Keep endpoint credentials exclusively in the mother-brain vault.
- [x] `AFLOW-0309` Prove moving a workflow between local and private-cloud compute preserves the graph.

**Closure:** users can swap the hosting node without rebuilding the model, harness or downstream
workflow, and no credential is embedded in the canvas or export.

## Stage 4 — Harness and business-context nodes

- [x] `AFLOW-0401` Define signed harness manifests independent of model manifests.
- [x] `AFLOW-0402` Add versioned system instructions, schemas, examples and tool declarations.
- [x] `AFLOW-0403` Add domain packs for departments and approved industry use cases.
- [x] `AFLOW-0404` Add active person, organisation, workspace, role and purpose context nodes.
- [x] `AFLOW-0405` Add scoped AION memory and business-map query nodes.
- [x] `AFLOW-0406` Add explicit include, exclude, redact, summarize and minimum-context controls.
- [x] `AFLOW-0407` Show a preflight preview of fields disclosed to every downstream node.
- [x] `AFLOW-0408` Version, compare and roll back harnesses independently from models.
- [x] `AFLOW-0409` Sandbox harness tools and reject undeclared network, file or action access.

**Closure:** one task can run through several model/harness combinations while receiving the same
authorized business context and without exposing inaccessible map regions.

## Stage 5 — Evidence and validation nodes

- [x] `AFLOW-0501` Add approved file, email, calendar, CRM, accounting and database retrieval nodes.
- [x] `AFLOW-0502` Add public web evidence nodes with source, retrieval time and content hashes.
- [x] `AFLOW-0503` Add citation support and source-to-claim mapping.
- [x] `AFLOW-0504` Add deterministic JSON-schema, calculation, code, policy and business-rule validators.
- [x] `AFLOW-0505` Add contradiction, stale-evidence, missing-evidence and source-quality checks.
- [x] `AFLOW-0506` Keep retrieved evidence separate from model interpretation.
- [x] `AFLOW-0507` Add confidence and uncertainty outputs that cannot be silently promoted to fact.
- [x] `AFLOW-0508` Add bounded caching, retention and source-revocation propagation.
- [x] `AFLOW-0509` Add fail-closed behavior when required evidence cannot be acquired.
- [x] `AFLOW-0510` Add a reusable evidence pack output for review and downstream verification.

**Closure:** each material conclusion can be traced to permitted evidence or is explicitly labelled
as interpretation, unknown or unresolved.

## Stage 6 — Deliberation, consensus and refinement

- [x] `AFLOW-0601` Add parallel candidate-generation branches.
- [x] `AFLOW-0602` Add independent critic, red-team and assumption-check nodes.
- [x] `AFLOW-0603` Add compare, rank, score, vote and reconcile nodes.
- [x] `AFLOW-0604` Prefer diverse providers/models/harnesses where independence is required.
- [x] `AFLOW-0605` Add deterministic and evidence-based arbitration before model voting.
- [x] `AFLOW-0606` Add bounded refinement loops with explicit success and stop conditions.
- [x] `AFLOW-0607` Add maximum iterations, tokens, time, cost and energy controls.
- [x] `AFLOW-0608` Detect repeated outputs, oscillation, non-progress and correlated failure.
- [x] `AFLOW-0609` Add human arbitration for unresolved or high-consequence disagreement.
- [x] `AFLOW-0610` Preserve dissenting conclusions and uncertainty in the final review package.

**Closure:** a three-specialist workflow improves a measured task against a single-model baseline,
stops within budget and fails honestly when evidence cannot resolve disagreement.

## Stage 7 — Governance and privacy visualization

- [x] `AFLOW-0701` Draw the AION ingress and return boundary visibly around the intelligence graph.
- [x] `AFLOW-0702` Colour-code local, household, organisation, customer-cloud and external edges.
- [x] `AFLOW-0703` Show the exact data classification and destination on every boundary-crossing edge.
- [x] `AFLOW-0704` Add redaction, consent, residency and encryption gates.
- [x] `AFLOW-0705` Add identity, membership, role, purpose and separation-of-duty policy nodes.
- [x] `AFLOW-0706` Add private phone approval and designated human-review nodes.
- [x] `AFLOW-0707` Prevent a fallback route from silently crossing privacy or cost policy.
- [x] `AFLOW-0708` Add expiry, revocation and lost-authority handling during long-running flows.
- [x] `AFLOW-0709` Explain each blocked route in plain language without exposing restricted content.
- [x] `AFLOW-0710` Export an inspectable policy/disclosure plan before execution.

**Closure:** a non-technical reviewer can identify what will leave the brain, what may execute and
who must approve it before the workflow is permitted to run.

## Stage 8 — Simulation, execution and recovery

- [x] `AFLOW-0801` Compile the visible graph through the Sovereign Flow compiler.
- [x] `AFLOW-0802` Translate valid manifests into existing Workflow Capsule definitions.
- [x] `AFLOW-0803` Add static validation and simulated-data preview.
- [x] `AFLOW-0804` Add dry-run with no external writes and a predicted disclosure/cost report.
- [x] `AFLOW-0805` Require a final exact review before enabling consequential capabilities.
- [x] `AFLOW-0806` Execute through existing permissioned connectors, never directly from model output.
- [x] `AFLOW-0807` Show live per-node queued, running, waiting, blocked, failed and verified states.
- [x] `AFLOW-0808` Add idempotency, timeout, retry, circuit breaking and compensation steps.
- [x] `AFLOW-0809` Support pause, cancel, resume and safe recovery after mother/node restart.
- [x] `AFLOW-0810` Emit a normalized execution and Intelligence Route Receipt.

**Closure:** complete. Read-only routes execute locally; consequential routes cannot pass until the
exact compiled route is approved. Permissioned connector adapters remain the only external-action
boundary. Runs journal per-node state, reject unbounded graph cycles, apply bounded retries and
timeouts, preserve idempotency keys, pause/cancel/resume safely, recover interrupted runs into a
waiting state after restart, and issue normalized route receipts that distinguish connector
readiness from a verified external effect. The existing Boardroom Workflow Canvas exposes this as
**Run & receipts** beside **Execute workflow**.

## Stage 9 — Comparison, evaluation and learning

- [x] `AFLOW-0901` Add one-click duplicate-and-swap for model, harness or compute nodes.
- [x] `AFLOW-0902` Run variants against the same versioned test/evidence pack.
- [x] `AFLOW-0903` Compare quality, correctness, evidence coverage, latency, cost and energy.
- [x] `AFLOW-0904` Separate public benchmarks from customer-private outcome measures.
- [x] `AFLOW-0905` Add champion/challenger trials with bounded traffic and rollback.
- [x] `AFLOW-0906` Learn route preferences only from corrections and verified outcomes.
- [x] `AFLOW-0907` Detect regression, drift and provider behavior changes.
- [x] `AFLOW-0908` Show what AION learned, why it changed routing and how to reverse it.

**Closure:** a customer can compare two complete intelligence stacks, select a winner on measured
evidence and later replace it without losing the accumulated brain.

Implemented through the existing Workflow Canvas **Compare stacks** centre and a customer-owned
evaluation ledger. A model, harness or compute node is duplicated and exactly one declared value is
changed. Both immutable variants bind to one hashed evidence pack. Dry comparisons perform zero
external writes and cannot affect learning. Quality, correctness, evidence coverage, latency, cost
and energy are recorded separately for public benchmarks and customer-private outcomes. Promotion
requires the configured sample floor, better quality without correctness/evidence regression and no
detected drift. Only verified outcome receipts or explicit human corrections influence routing.
Every promotion and rollback retains its actor, reason, comparison hash and reversible decision hash.

## Stage 10 — Templates, sharing and capability ecosystem

- [x] `AFLOW-1001` Add signed reusable flow templates with no embedded credentials or customer data.
- [x] `AFLOW-1002` Add approved department templates for research, sales, finance, operations and support.
- [x] `AFLOW-1003` Add import-time dependency, licence, permission and compatibility review.
- [x] `AFLOW-1004` Separate global template logic from customer-local bindings and memory.
- [x] `AFLOW-1005` Add private organisation template libraries and role-based publishing.
- [x] `AFLOW-1006` Add revoke, quarantine, update, pin and rollback controls.
- [x] `AFLOW-1007` Keep third-party publishing and commercial settlement disabled until reviewed.

**Closure:** an organization can install, inspect, bind, dry-run, approve, update and remove a
template without granting it undeclared authority or copying its brain.

**Closure:** complete. The existing Workflow Canvas now exposes a **Templates** gallery with six
signed starting points: Local-first research, Gemini evidence analysis, Private business analysis,
Multi-model critic, Governed email drafting and Boardroom decision analysis. Every package is
immutable and signature-verified; dependency, licence and permission declarations are shown before
use. Loading creates a non-executing draft. Installation stores customer-specific bindings outside
the package as opaque Visual Vault references and explicitly grants no authority. Organisation
publishers can maintain private templates, while pin, rollback, quarantine, revoke and removal
controls retain version history. Third-party publishing and commercial settlement remain disabled.

## Stage 11 — Production and enterprise qualification

- [x] `AFLOW-1101` Add responsive desktop/tablet authoring and read-only mobile review.
- [x] `AFLOW-1102` Add large-graph navigation, grouping, reusable subflows and version diff.
- [x] `AFLOW-1103` Add collaborative editing with signed authorship and conflict resolution.
- [x] `AFLOW-1104` Add least-privilege multi-user, multi-workspace and multi-organisation access.
- [x] `AFLOW-1105` Add encrypted export/import and deterministic migration between schema versions.
- [x] `AFLOW-1106` Add zero-content operational telemetry and customer-owned observability.
- [x] `AFLOW-1107` Complete threat modelling, adversarial graph tests and dependency review.
- [x] `AFLOW-1107R1` Bind prepare, approve, execute, run access/control, evaluation and template lifecycle to canonical membership plus a signed trusted-device session; remove browser role authority.
- [x] `AFLOW-1107R2` Replace browser-supplied execution policy with a versioned, persisted customer policy and exact policy receipt.
- [x] `AFLOW-1107R3` Remove the development fallback encryption key from production startup and bind secrets to the customer keystore.
- [x] `AFLOW-1107R4` Produce a minimal hashed runtime lock and signed SBOM; isolate or replace the residual ECDSA and WeasyPrint paths.
- [x] `AFLOW-1108` Benchmark large graphs, parallel routes and long-running workflows.
- [ ] `AFLOW-1109` Complete accessibility, privacy, regulatory and enterprise field qualification.
  - [x] Internal keyboard, modal semantics, focus return, read-only mobile and privacy-boundary checks.
  - [ ] Independent WCAG 2.2 AA and assistive-technology audit.
  - [ ] Jurisdiction- and sector-specific privacy, employment, retention and AI-governance review.
  - [ ] Representative multi-organisation enterprise field trials and independent penetration test.

**Closure:** a representative medium business operates AION Flow with several teams, private
models and customer-cloud compute while preserving tenant, role, residency and approval boundaries.

**Current Stage 11 evidence:** the **Production** centre now provides responsive desktop/tablet
authoring checks and a read-only mobile review mode. Workflow commits use optimistic revision
checks, retain signed authorship receipts and reject stale concurrent edits. Password-protected
AES-256-GCM export/import uses scrypt key derivation, performs deterministic graph migration and
never restores execution authority. Operational telemetry contains hashes, counts, node families,
status totals and latency buckets only; it excludes workflow content, credentials and customer
identifiers. The local adversarial suite rejects dangling edges, duplicate identities, excessive
graph size and unauthorized editing. Production qualification, commits, history, diffs, encrypted
transfer, telemetry and benchmarks now resolve the person against the active canonical workspace
and Organisation Authority container. Browser role claims are ignored. Workflow revision keys are
workspace-scoped, so identical workflow identifiers in different organisations do not collide, and
legacy unscoped histories fail closed pending an explicit migration.

Stage 11's internal engineering qualification is recorded in
`AION_FLOW_STAGE_11_QUALIFICATION_RECORD.md`. Signed device sessions now bind exact requests to
canonical organisation membership; execution policy is signed and persisted; production secrets
fail closed without a customer keystore route; and the minimal hashed runtime lock has a signed
CycloneDX SBOM. Synthetic qualification passed a 1,500-node graph, 256 parallel routes and 250
atomic recovery checkpoints without model calls or external actions. The remaining Stage 11 item
cannot be self-certified: independent penetration and accessibility testing, jurisdictional review
and representative enterprise field trials remain release gates.

## Recommended build order

The strict execution sequence is:

**Stage 1 catalogue UX → Stage 2 model catalogue → Stage 3 compute → Stage 4 harness/context →
Stage 5 evidence → Stage 6 deliberation → Stage 7 governance visualization → Stage 8 execution →
Stage 9 comparison/learning → Stage 10 templates → Stage 11 production qualification.**

The immediate cursor is **`AFLOW-1109` independent qualification**. Stages 0--10 and Stage 11
engineering tasks 1101--1108 are implemented. Consequential execution remains fail-closed whenever
a permissioned connector, exact approval or provider verification is missing. Enterprise release
still depends on independent security and accessibility review, applicable legal and regulatory
assessment, release signing identities and representative customer field evidence.
