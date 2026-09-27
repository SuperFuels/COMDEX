# GlyphChain and Legal Incident-Response Playbook

Status date: 26 September 2026

## Purpose and release boundary

This playbook defines the production response for incidents spanning Tessaris
application accounts, Legal records and signing, delivery providers, Vault
credentials, GlyphChain consensus, validators, relays and local desktop nodes.
It preserves evidence without weakening workspace isolation or exposing Legal
document content.

The playbook is operational guidance. It does not grant unilateral authority to
rewrite finalized history, recover a user account, access a workspace, disclose
Legal content, replace validators or bypass an approval gate. Existing
cryptographic, workspace, role and quorum checks remain authoritative during an
incident.

## Roles and authority

Every production deployment must assign named people or on-call functions to
the following roles before launch:

| Role | Authority and responsibility |
| --- | --- |
| Incident commander | Declares severity, coordinates work and records decisions; cannot bypass technical authorization |
| Security lead | Directs containment, credential revocation and forensic preservation |
| GlyphChain operator | Performs signed node, relay, checkpoint and validator operations within the governance rules |
| Legal product owner | Decides product handling and customer impact; does not provide jurisdictional legal advice unless qualified |
| Privacy lead | Assesses personal-data exposure, minimisation and notification duties |
| Delivery owner | Coordinates Resend/Microsoft 365 evidence, suppression and recovery |
| Customer communications owner | Issues approved, evidence-based updates without exposing protected details |
| Evidence custodian | Maintains hashes, chain of custody, access log and retention/hold decisions |

One person may hold multiple roles in a small deployment, but the incident log
must say which role they were exercising. Validator-set changes still require
the configured current-validator quorum; role labels do not replace signatures.

## Severity model

- **SEV-1:** suspected private-key disclosure, conflicting finality, cross-
  workspace disclosure, unauthorized signature completion, destructive data
  loss, active compromise or widespread inability to verify evidence.
- **SEV-2:** contained credential exposure, delivery evidence corruption,
  persistent partition, failed recovery, sustained denial of service or a
  security control failing closed across multiple customers.
- **SEV-3:** isolated provider failure, bounded malformed input, single-node
  degradation or a recoverable operational error with no evidence of disclosure.
- **SEV-4:** suspected issue or policy deviation requiring investigation but no
  current security, integrity or availability impact.

When facts are incomplete, use the higher plausible severity until evidence
supports a downgrade. Record the reason, approver and time of every change.

## First 30 minutes

1. Create an incident identifier and append-only decision log. Record UTC time,
   reporter, observed symptoms, affected workspaces/systems and the evidence
   source without copying protected content into chat or tickets.
2. Appoint the incident commander, security lead and evidence custodian.
3. Preserve volatile facts: process state, software/build identifier, active
   role, peer/relay counts, consensus height/finality status, provider event IDs,
   affected record identifiers and relevant timestamps.
4. Stop harmful work through the narrowest existing control: pause delivery,
   revoke a device/session, disable elevated participation, isolate a relay,
   suspend a Vault connection or place affected Legal records under hold.
5. Do not rotate, delete, prune, reinstall, clear a safety halt, regenerate a
   token or restore a backup until the pre-action evidence is preserved.
6. Determine whether the event crosses workspace, customer, jurisdiction or
   provider boundaries and activate the relevant owners.
7. Begin the incident timeline. Every action records actor, role, exact command
   or control, object identifiers, result, timestamp and resulting evidence hash.

## Evidence-preservation contract

Preserve the minimum necessary evidence in three classes:

### Class A: content-free operational evidence

- signed release/baseline report and exact source manifest;
- node role/participation status, health snapshots and hash-chained history;
- protocol plan/journal, partition-recovery journal and validator-governance
  state/transition proofs;
- public checkpoints, independent pins, finality certificates and receipt IDs;
- relay/provider request IDs, response status, Internet Message-ID and delivery
  trace identifiers;
- application audit event identifiers, timestamps and hashes.

Class A may be collected centrally under the incident access policy because it
contains no Legal document body or private key. Peer addresses and personal
identifiers remain minimized or pseudonymized where they are not essential.

### Class B: protected customer or Legal evidence

- encrypted workspace records, exact signed documents, signer certificates,
  delivery evidence and portable proof packages;
- encrypted full-state recovery packages and ledger snapshots;
- provider messages or callbacks that contain personal or business content.

Class B remains encrypted and workspace-scoped. Export requires the existing
authorized Legal/full-state procedure, an incident reason and chain-of-custody
entry. Do not paste it into ordinary tickets, email or messaging systems.

### Class C: secret material

- Legal, device, session, provider, relay and validator private keys;
- recovery codes/passwords, bearer tokens, signing secrets and unredacted Vault
  credentials.

Never collect Class C into an incident archive. Record only the custody system,
key identifier/version, rotation/revocation status and proof of the action.
Deployment-managed validator finality keys remain in approved secret custody.

For every retained artifact record: incident ID, source, collector, UTC capture
time, byte length, SHA-256 digest, classification, workspace/chain scope,
storage location, encryption/custody method and every subsequent access or
transfer. A later export never replaces the original digest entry.

## Scenario playbooks

### Application account or trusted-device compromise

1. Revoke the affected device and active leases/sessions; preserve its device
   identifier, public key identifier and last accepted nonce/timestamp.
2. Suspend affected connected-service consents and high-impact approval routes.
3. Use the account-recovery authority only after the claimant proves the
   configured recovery factors. A local whole-device backup alone is not proof
   of application-account ownership.
4. Rotate application/session credentials and re-enrol replacement devices.
5. Review actions since the last trusted event. Re-authorize only the minimum
   workspace and provider scope.
6. If the account-recovery authority is unavailable or cannot establish
   ownership, keep the account locked and escalate; do not create a replacement
   owner locally.

### Legal signing-link or signer-verification abuse

1. Void or rotate the affected envelope token; do not edit the approved document
   version or signer history.
2. Preserve token-index/audit identifiers, rate-limit result, verification
   method, timestamps and delivery event IDs without recording the plaintext
   token or verification code.
3. If completion is suspected unauthorized, place the envelope and matter under
   hold, export the exact evidence package and prevent delivery of a replacement
   until review.
4. Issue a new envelope/version only through the ordinary authorization path.
   Never overwrite or relabel the disputed evidence.

### Delivery credential, callback or provider incident

1. Pause new external delivery for the affected provider and preserve pending
   outbox state.
2. Revoke/rotate Vault credentials or webhook signing secrets through the
   provider and Vault; never store replacement secrets in the incident log.
3. Preserve exact provider event IDs, webhook signature-verification outcome,
   Internet Message-ID and Exchange trace evidence.
4. Classify every item as accepted, delivered, delayed, bounced, rejected or
   unknown. Provider acceptance is not recipient delivery.
5. Re-authorize and retry only idempotently. Keep prior attempts and evidence.

### Suspected malicious or compromised validator

Follow the dedicated validator procedure in
`GLYPHCHAIN_RELAY_VALIDATOR_OPERATOR_RUNBOOK.md`. In summary: isolate the node,
preserve evidence, disable its local elevated role, propose a later-epoch
`emergency_removal`, exclude the accused and joining validators from approval
power, collect unaffected current-validator quorum, verify the transition proof
and publish/pin the successor through separate channels. Never unfinalize or
silently rewrite historical receipts.

### Conflicting finality or partition safety halt

1. Preserve both certified views, the sticky halt record, peer/relay health and
   the last independently pinned checkpoint.
2. Stop proposals/votes and isolate untrusted routes. Do not choose a history by
   node count, recency or administrator preference.
3. Resolve the trusted history through quorum evidence and incident governance.
4. Restore/repair to the exact verified history, then clear the halt using the
   signed administrative route and exact displayed halt identifier.

### Relay compromise or metadata abuse

1. Remove the relay from advertised routes and stop its process/credentials.
2. Preserve content-free connection, authentication and routing metadata.
3. Verify that no Legal document content or application plaintext traversed the
   relay. Treat contrary evidence as SEV-1.
4. Rotate relay transport credentials and publish a new signed route set. A
   relay never becomes a validator or trust anchor by being available.

### Workspace disclosure, record corruption or destructive loss

1. Lock affected workspace operations and place relevant records under hold.
2. Preserve encrypted files, metadata, hashes and audit history before repair.
3. Determine whether isolation failed or a correctly authorized user exported
   data; do not infer disclosure merely from file presence.
4. Preflight the encrypted full-state backup in an isolated clean root. Verify
   its manifest, workspace/chain binding, checkpoint/pin consistency and ledger
   snapshot before restoration.
5. Restore only to the intended workspace/chain and retain the pre-restore state.

### Resource exhaustion or denial of service

1. Preserve limit errors, request class, source aggregation and health metrics;
   do not retain raw malicious bodies unless specifically approved and isolated.
2. Confirm that body, queue, peer, record, storage and verification limits failed
   closed. Isolate the exposed route if a bound did not hold.
3. Apply deployment-level traffic controls without raising application limits
   beyond reviewed maxima during the incident.
4. Drain/retry durable queues idempotently after capacity is restored.

## Recovery and return to service

Return a component to service only when:

- the containment action is verified and the attack path is closed;
- exact source/build, configuration and trust material are identified;
- retained state passes integrity verification and workspace/chain binding;
- restored data is tested in isolation before promotion;
- revoked credentials, devices and routes cannot authenticate;
- delivery/proof retries are idempotent and prior evidence remains retained;
- the incident commander, security lead and relevant system owner record an
  approval with residual risks and monitoring conditions.

Finality safety takes precedence over availability. A node that cannot verify
its checkpoint, pin, transition proof or restored history stays halted.

## Communications, privacy and legal escalation

- Communicate known facts, affected service, user action and next update time;
  distinguish suspicion from verified impact.
- Do not claim a document is invalid, a person signed, a provider delivered or
  a validator acted maliciously unless the retained evidence supports it.
- The privacy lead records affected data categories, people, jurisdictions,
  processors and notification deadlines. Qualified advisers decide statutory
  notification duties.
- Customer-specific evidence is shared only through the approved secure channel
  and only with authorized recipients.
- Public statements and regulator/customer notices require the incident
  commander, privacy/legal owner and communications owner to approve the exact
  wording and evidence basis.

## Closure and post-incident requirements

An incident closes only after the timeline, evidence index, containment,
recovery verification, affected-party decision, residual risk and follow-up
owners/dates are complete. Record which safeguards detected the event and which
failed. Convert remediation into tracked release work and update the relevant
test or exercise before considering it resolved.

Retain the incident record under the approved retention/Legal-hold policy.
Deletion requires the same governed destruction process as other protected
Legal records; never delete evidence merely because service has recovered.

## Exercise schedule and acceptance criteria

Before production and at least annually thereafter, run:

- lost-device/application-account lockout and recovery;
- delivery-secret compromise with delayed/bounced/rejected retries;
- compromised-validator emergency removal;
- relay outage/compromise and route replacement;
- conflicting-view partition halt and verified recovery;
- clean-root encrypted full-state restore;
- sustained resource-exhaustion and queue recovery.

Each exercise must retain an incident ID, participants, topology, exact build,
inputs, evidence hashes, observed timings, pass/fail against this playbook,
findings, owners and retest evidence. Tabletop discussion alone does not satisfy
a technical recovery exercise. The repeatable local synthetic recovery and
lost-validator exercise is recorded in
`GLYPHCHAIN_LEGAL_DISASTER_RECOVERY_EXERCISE_REPORT.json`. Its pass result does
not satisfy application-account recovery or production validation. Production
release remains blocked until the separate representative-device,
live-provider, soak and independent-review checklist items pass.
