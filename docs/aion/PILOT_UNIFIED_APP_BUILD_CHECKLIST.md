# Pilot Unified App Build Checklist

Status: implementation baseline following the 2 September 2026 unified-product decision.

This checklist tracks remaining work for bridging Personal Pilot, external workspaces,
Boardroom, television, mobile, browser and desktop. A checked item must have executable
evidence. Interface presence alone does not constitute completion.

## Completion rules

- [ ] Every item has an owner, implementation reference, tests and dated evidence.
- [ ] External dependencies are marked `BLOCKED-EXTERNAL`, not represented as complete.
- [ ] Consequential actions have proposal, approval, execution, verification and receipt states.
- [ ] Personal, Household, Workspace and Boardroom boundary tests run on every release.
- [ ] No release claims native biometrics, delivery or provider execution without field evidence.

## Phase A — Canonical identity and workspace contracts

- [ ] `UA-001` Version the Person Identity schema.
- [ ] `UA-002` Version the Device Identity and possession-proof schema.
- [ ] `UA-003` Version Personal, Household, Workspace, Engagement and Boardroom space types.
- [ ] `UA-004` Version Membership, Invitation, Acceptance, Expiry and Revocation schemas.
- [ ] `UA-005` Version signed Capability Lease and constraint schemas.
- [ ] `UA-006` Version Conversation, Participant and Message schemas.
- [ ] `UA-007` Version Action Proposal, Approval and Receipt schemas.
- [ ] `UA-008` Version Surface Manifest and redaction policy schemas.
- [ ] `UA-009` Version Memory Item and Service Connection schemas.
- [ ] `UA-010` Define shared state language from draft through verified completion.
- [ ] `UA-011` Add migration tests from current Personal Pilot and Boardroom records.
- [ ] `UA-012` Add cross-space denial, confused-deputy and replay test suites.

### Phase A closure

- [ ] Personal and organisation records can coexist without identifier collision.
- [ ] A single person can join two businesses with incompatible roles without leakage.
- [ ] Every client receives authority from a signed manifest or lease, never button visibility.

## Phase B — Unified mobile shell

- [ ] `UA-020` Build the persistent Personal / Workspace / Boardroom switcher.
- [ ] `UA-021` Build Pilot, Inbox, Actions, Spaces and Me navigation.
- [ ] `UA-022` Build the persistent Pilot text and voice composer.
- [ ] `UA-023` Show active person, space, role, mother brain and connection state.
- [ ] `UA-024` Build contextual shortcut rows for Personal and professional spaces.
- [ ] `UA-025` Replace the long phone-controller stream with contextual panels.
- [ ] `UA-026` Build message, task, approval, decision, delegation and receipt cards.
- [ ] `UA-027` Build clear pending, failed, offline, cancelled and expired states.
- [ ] `UA-028` Build accessibility, dynamic type, screen-reader and reduced-motion support.
- [ ] `UA-029` Build safe notification previews with private-content suppression.
- [ ] `UA-030` Create design tokens and responsive specifications for iOS and Android.

### Phase B closure

- [ ] A user can reach any daily action within two navigational decisions.
- [ ] Personal, Workspace and Boardroom contexts are unmistakable at every width.
- [ ] The shell works at supported phone sizes without a permanent page-length controller.

## Phase C — Pairing and private remote connection

- [ ] `UA-040` Generate short-lived, one-time mother-brain pairing challenges.
- [ ] `UA-041` Build QR and human-verifiable code pairing.
- [ ] `UA-042` Generate platform-protected phone device keys.
- [ ] `UA-043` Issue, rotate and revoke device certificates.
- [ ] `UA-044` Pin or otherwise verify mother-brain identity.
- [ ] `UA-045` Use direct trusted-LAN connection when available.
- [ ] `UA-046` Implement encrypted peer-to-peer remote connection.
- [ ] `UA-047` Implement end-to-end encrypted relay fallback.
- [ ] `UA-048` Ensure the relay cannot decrypt message, action or memory content.
- [ ] `UA-049` Add automatic roaming, reconnection and duplicate-action prevention.
- [ ] `UA-050` Add lost-phone revocation and device inventory.
- [ ] `UA-051` Add owner recovery codes and key-recovery policy.
- [ ] `UA-052` Build connection diagnostics in non-technical language.

### Phase C closure

- [ ] A paired phone moves from home Wi-Fi to mobile data and reconnects automatically.
- [ ] A compromised relay test reveals no application content.
- [ ] A revoked phone cannot reconnect, activate a TV, approve or renew a lease.

## Phase D — Unified Inbox and Actions

- [ ] `UA-060` Merge human, Pilot-to-Pilot, provider and workspace communication views.
- [ ] `UA-061` Preserve owning space and privacy label on every item.
- [ ] `UA-062` Implement structured Pilot-to-Pilot messages.
- [ ] `UA-063` Implement task proposal, recipient acceptance, decline and completion.
- [ ] `UA-064` Implement reminder and follow-up objects.
- [ ] `UA-065` Implement calendar proposal and availability objects.
- [ ] `UA-066` Implement document review and professional sign-off requests.
- [ ] `UA-067` Implement Boardroom decision and delegation objects.
- [ ] `UA-068` Implement idempotent delivery and reconciliation.
- [ ] `UA-069` Implement correction and cancellation propagation.
- [ ] `UA-070` Implement provider-independent verified receipts.
- [ ] `UA-071` Add search and filters without creating separate message silos.

### Phase D closure

- [ ] Two Pilot identities exchange and complete a structured task end-to-end.
- [ ] Both mothers reconcile the same accepted, declined, cancelled and completed states.
- [ ] Replayed delivery cannot duplicate a task, message or consequential action.

## Phase E — Personal Pilot integration

- [ ] `UA-080` Connect production private identities and guardian-controlled profiles.
- [ ] `UA-081` Connect personal tasks, reminders and household lists.
- [ ] `UA-082` Connect personal calendar and availability controls.
- [ ] `UA-083` Connect private contacts and recipient resolution.
- [ ] `UA-084` Connect authorised email and messaging adapters.
- [ ] `UA-085` Connect shopping, booking and service-action proposals.
- [ ] `UA-086` Connect files, saved items and research results.
- [ ] `UA-087` Connect television, device fabric and IoT controls.
- [ ] `UA-088` Connect memory inspection, correction, export, scope and deletion.
- [ ] `UA-089` Connect emergency and priority communication with existing safety boundaries.
- [ ] `UA-090` Complete Personal Pilot real-provider qualification.

### Phase E closure

- [ ] Personal Pilot completes daily communication and task journeys without Boardroom.
- [ ] Shared-TV speech cannot choose a private account, card, calendar or identity.
- [ ] Every real provider action returns an honest provider receipt or a clear failure.

## Phase F — Boardroom and external workspace bridge

- [ ] `UA-100` Implement the provider-independent Workspace Gateway.
- [ ] `UA-101` Expose Boardroom departments, agents, dashboards, files and decisions.
- [ ] `UA-102` Implement organisation invitations with exact role and requested scopes.
- [ ] `UA-103` Implement private invitation review and acceptance.
- [ ] `UA-104` Implement role changes, expiry, suspension and immediate revocation.
- [ ] `UA-105` Implement department-specific mobile briefings.
- [ ] `UA-106` Implement review, delegation, correction and approval flows.
- [ ] `UA-107` Implement accountant, auditor, adviser and director sign-off receipts.
- [ ] `UA-108` Implement desktop continuation for complex work and setup.
- [ ] `UA-109` Implement workspace-only files and redacted cross-space references.
- [ ] `UA-110` Add external participant and malicious-admin boundary tests.

### Phase F closure

- [ ] A freelancer can enter Marketing but cannot enumerate Finance, People or Board data.
- [ ] An accountant receives and signs one exact review package with a verified receipt.
- [ ] Expired access removes organisation data without affecting the person's other spaces.

## Phase G — Television convergence

- [ ] `UA-120` Replace hard-coded TV tiles with a signed Surface Manifest.
- [ ] `UA-121` Show active person, space and expiry on the television.
- [ ] `UA-122` Build phone-authorised TV takeover.
- [ ] `UA-123` Build explicit logout, inactivity lock and departure lock.
- [ ] `UA-124` Render Personal, Household, Workspace and Boardroom tiles by authority.
- [ ] `UA-125` Keep sensitive approval on the private phone.
- [ ] `UA-126` Redact messages, documents, finance and private details by default.
- [ ] `UA-127` Build deliberate full-screen document and dashboard presentation.
- [ ] `UA-128` Verify that TV session expiry deletes cached private presentation state.

### Phase G closure

- [ ] Two household identities receive different TV manifests on the same television.
- [ ] A workspace participant sees only their permitted business tiles.
- [ ] Five minutes of configured inactivity or explicit logout clears the private session.

## Phase H — tessaris.ai and browser access

- [ ] `UA-140` Build the `Connect to my Pilot` entry flow.
- [ ] `UA-141` Authenticate the personal device without centralising mother credentials.
- [ ] `UA-142` Select and verify a registered mother brain.
- [ ] `UA-143` Establish an encrypted session to the selected mother.
- [ ] `UA-144` Load data from the user's environment, not a default Tessaris replica.
- [ ] `UA-145` Build optional rendezvous with minimum metadata retention.
- [ ] `UA-146` Allow advanced users and businesses to self-host rendezvous and relay.
- [ ] `UA-147` Publish privacy, metadata, retention and jurisdiction documentation.

### Phase H closure

- [ ] Browser access works remotely while application data remains on the selected mother.
- [ ] A fake mother endpoint is rejected before private content is displayed.
- [ ] Disabling Tessaris rendezvous does not destroy the user's mother or local access.

## Phase I — Self-hosting, appliance and business deployment

- [ ] `UA-160` Package clean installers for supported desktop/server platforms.
- [ ] `UA-161` Package a dedicated-appliance image and recovery process.
- [ ] `UA-162` Publish supported NAS, VPS, private-cloud and on-premises profiles.
- [ ] `UA-163` Build guided service, model and storage selection.
- [ ] `UA-164` Build advanced retention, backup, relay and network controls.
- [ ] `UA-165` Build encrypted backup with owner-visible last-success state.
- [ ] `UA-166` Build complete mother-brain export and migration.
- [ ] `UA-167` Prevent split-brain writable primaries during migration.
- [ ] `UA-168` Build signed update, staged activation and automatic rollback.
- [ ] `UA-169` Build one-click diagnostics and redacted support bundles.
- [ ] `UA-170` Publish business hardening and administrator guidance.

### Phase I closure

- [ ] A non-technical user installs and pairs Pilot without terminal use.
- [ ] A business deployment passes backup, restore, revocation and update rollback tests.
- [ ] A mother migrates to a new host without losing identity, permissions or audit continuity.

## Phase J — Native mobile production

- [ ] `UA-180` Build signed native iOS application.
- [ ] `UA-181` Build signed native Android application.
- [ ] `UA-182` Add hardware-backed device keys where supported.
- [ ] `UA-183` Add OS biometric approval without using biometric identity inference.
- [ ] `UA-184` Add background connection and safe notification delivery.
- [ ] `UA-185` Add deep links for invitations, actions and TV takeover.
- [ ] `UA-186` Add secure local storage, screenshot/privacy policy and app lock.
- [ ] `UA-187` Complete accessibility and child/guardian qualification.
- [ ] `UA-188` Complete app-store privacy declarations and release review.
- [ ] `UA-189` Complete real-device battery, network and lifecycle testing.

### Phase J closure

- [ ] Production apps pass signed-device, lost-device and biometric approval tests.
- [ ] Background reconnection does not duplicate messages or actions.
- [ ] Notification previews do not expose protected Personal or Boardroom content.

## Phase K — Adoption and Pilot network

- [ ] `UA-200` Add trusted-contact invitation and acceptance.
- [ ] `UA-201` Add useful structured invitations for non-Pilot recipients.
- [ ] `UA-202` Add Pilot-to-Pilot task, message and Moment handoffs.
- [ ] `UA-203` Add household and family coordination with recipient acceptance.
- [ ] `UA-204` Add employer, client and professional workspace invitations.
- [ ] `UA-205` Add safe follow-up when a recipient has not responded.
- [ ] `UA-206` Measure conversion from TV, personal usefulness and workspace invitations.
- [ ] `UA-207` Add abuse reporting, contact blocking, rate limits and child protections.

### Phase K closure

- [ ] Every invitation delivers immediate utility rather than an empty signup.
- [ ] Blocking or revocation stops future agent-to-agent contact.
- [ ] Network growth does not require central ownership of user conversations or memory.

## Release-wide field scenarios

- [ ] Clean household installation and first phone pairing.
- [ ] Local-to-remote phone roaming and reconnection.
- [ ] Personal-to-Pilot structured task with acceptance.
- [ ] Pilot-to-non-Pilot email/message with verified delivery state.
- [ ] Employer invitation to a restricted employee workspace.
- [ ] Freelancer participation across two unrelated clients.
- [ ] Accountant bounded review and human sign-off.
- [ ] Boardroom mobile briefing, delegation and approval.
- [ ] Shared-TV takeover, redaction, timeout and logout.
- [ ] Lost-phone revocation.
- [ ] Mother-brain backup, restore and migration.
- [ ] Failed update and automatic rollback.

## External dependencies register

- [ ] `BLOCKED-EXTERNAL` Apple developer signing, entitlements and App Store review.
- [ ] `BLOCKED-EXTERNAL` Google Play signing and release review.
- [ ] `BLOCKED-EXTERNAL` Production background-network and notification permissions.
- [ ] `BLOCKED-EXTERNAL` Official provider permissions for WhatsApp or equivalent channels.
- [ ] `BLOCKED-EXTERNAL` Real OAuth/service accounts for field execution tests.
- [ ] `BLOCKED-EXTERNAL` Business security, privacy, regulatory and jurisdiction review.
- [ ] `BLOCKED-EXTERNAL` Representative household, freelancer and business field participants.

## Recommended immediate execution order

1. Close Phase A contracts and boundary tests.
2. Build the Phase B app shell against fixture data.
3. Implement Phase C pairing and remote transport.
4. Close one Phase D Pilot-to-Pilot communication journey.
5. Integrate Personal Pilot in Phase E.
6. Integrate Boardroom and external workspaces in Phase F.
7. Converge the television in Phase G.
8. Add browser, self-hosting and native production in Phases H-J.
9. Expand the invitation and contact network in Phase K.
