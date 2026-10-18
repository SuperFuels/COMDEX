# Pilot Unified Mobile App — Master Build Checklist

Status: canonical implementation programme — remaining executable hardening pass complete, 3 September 2026  
Scope: Personal Pilot + GlyphNet + Workspaces + Boardroom + TV/device continuity  
Supersedes for mobile-app execution: `PILOT_UNIFIED_APP_BUILD_CHECKLIST.md`

This is the single build checklist for creating the Pilot mobile product. It deliberately
reuses the existing AION, Pilot Fabric, GlyphNet and Boardroom systems instead of creating
parallel identity, messaging, task, approval or audit stacks.

The concise active queue is maintained in
`PILOT_UNIFIED_MOBILE_REMAINING_BUILD_TASKS.md`. This master file remains the authoritative
history and acceptance record; completed tasks are not deleted from it.

The application has one person identity and three primary modes:

1. **Personal** — private Pilot conversation, inbox, tasks, calendar, services, household,
   devices, television, learning, shopping and files.
2. **Workspace** — bounded access to an employer, client, project or professional engagement.
3. **Boardroom** — mobile review, briefing, delegation, intervention and approval for an
   owned or administered organisation. Detailed business creation and administration remain
   desktop-first.

## Status language

- `[REUSE]` — implementation exists and should be adapted rather than rebuilt.
- `[BUILD]` — new product or infrastructure work.
- `[HARDEN]` — existing development implementation must be made production-safe.
- `[VERIFY]` — requires executable or field evidence before closure.
- `[HIDDEN]` — preserve the code, but exclude it from production manifests and interfaces.
- `[EXTERNAL]` — depends on accounts, hardware, signing, provider approval or independent review.

A checked item must have an implementation reference, automated evidence and a dated acceptance
record. A visible screen, mocked response or locally queued request is not proof of completion.

## Current position against the original plan

The programme currently has **169 of 182 coded `MOB` tasks completed**.  This table preserves and
counts every coded task in the original checklist.  Closure gates, field trials
and external dependencies remain separately visible beneath each stage and are not hidden by the
percentage.

| Stage | Coded tasks complete | Current status |
| --- | ---: | --- |
| 0 — Product boundary and reuse map | 10 / 10 | Implementation complete; one runtime-wide economic-off startup receipt remains before formal closure. |
| 1 — Canonical contracts and migration | 18 / 18 | Closed. |
| 2 — Unified mobile shell | 16 / 16 | Coded implementation and representative responsive viewport verification complete. |
| 3 — Pairing and remote continuity | 14 / 14 | Coded implementation complete; a real Wi-Fi/mobile-data roaming exercise remains before formal closure. |
| 4 — GlyphNet Unified Inbox | 17 / 17 | Coded implementation complete. One real-phone reconnect qualification remains before formal stage closure. |
| 5 — Personal Pilot integration | 13 / 14 | Coded integration is complete through the provider-independent AION Native composer; real provider qualification remains external. |
| 6 — Workspace and Boardroom bridge | 13 / 13 | Coded implementation complete; representative multi-organisation field qualification remains. |
| 7 — Non-Pilot recipients | 9 / 10 | Official SMS adapter complete; provider-account field delivery and authorised WhatsApp remain external. |
| 8 — TV and device continuity | 10 / 10 | Coded implementation complete; a two-person presentation and expiry exercise remains a field gate. |
| 9 — Selective proof rail | 10 / 10 | Coded implementation and privacy, tamper, outage and task-lifecycle verification complete. |
| 10 — Self-hosting and deployment | 11 / 11 | Coded implementation complete; public infrastructure and two-host migration exercises remain field gates. |
| 11 — Native iOS and Android | 7 / 11 | Native source foundations, hardware-wrapped possession, biometric approval and private background delivery are coded; signed binaries and device qualification remain. |
| 12 — Calls and groups | 7 / 8 | Participant-authenticated WebRTC negotiation and adverse-network authority tests complete; independent media-encryption audit remains. |
| 13 — Optional radio/Wave transport | 6 / 10 | Legacy framing/queue reuse and authenticated serial/bridge boundary complete; BLE/Wi-Fi Direct, hardware/compliance and offline field proof remain. |
| 14 — Adoption and Pilot network | 8 / 10 | Coded adoption core complete; household/worker field pilots and independent security, privacy and legal review remain. |

The present strict-order cursor is **Stage 5, task `MOB-0514`**, a real-provider qualification gate.
Stage 11's signed native binaries are blocked on full platform toolchains, signing identities and
physical devices. Stage 7's authorised WhatsApp route remains provider-dependent, and Stage 5's provider
qualification remains an explicit external gate.  Stage 4's only remaining
closure gate is a field exercise proving text, voice-note and push-to-talk reconnect behavior on
real phones without duplication; it remains visible and must not be represented as passed until
that evidence exists.

## Latest implementation evidence

- **3 September 2026:** completed `MOB-0216`, `MOB-0702`, `MOB-1208`, `MOB-1302` and
  `MOB-1304`. The responsive mobile surface was exercised at 320x568, 360x800 and 430x932:
  every visible control met the 44x44 minimum target and no layout produced horizontal overflow.
- Added a persona-bound official Twilio adapter for SMS and the separately configured authorised
  WhatsApp route. It validates E.164 recipients, bounds content, carries idempotency, verifies signed
  status callbacks and never equates provider acceptance with carrier delivery or human reading.
  Actual provider-account delivery and the officially authorised WhatsApp account remain external.
- Call/group tests now exercise packet loss, jitter, out-of-order negotiation, reconnection epochs,
  removed participants and forged/stolen-device attempts. Group messages require possession-signed,
  nonce-protected payloads and a current membership/key epoch.
- The hidden Wave authority now reuses bounded fragmentation, integrity, priority/TTL/retry queues
  and store-and-forward explicitly. The legacy radio node has a real reconnecting serial driver,
  strict header-only replay-protected bridge authentication, no default secret, mock routes disabled
  unless explicitly enabled, Express 5.2.1 and zero reported production dependency vulnerabilities.
  No physical radio delivery is claimed; BLE/Wi-Fi Direct and disconnected two-mother proof remain open.
- **Verification:** all **588 AION Fabric tests** pass, the radio-node TypeScript build and production
  dependency audit pass, and the append-only hardening LaTeX section compiles cleanly. No external
  message, provider mutation, physical radio operation or live television restart occurred.

- **3 September 2026:** completed the coded platform-security portions of `MOB-1103`, `MOB-1104`
  and `MOB-1105`. The iOS core preserves the Ed25519 Pilot protocol while wrapping its private key
  through a non-exportable Secure Enclave P-256 key and `WhenUnlockedThisDeviceOnly` Keychain
  record. Android source wraps the same protocol key with an authentication-bound Android Keystore
  AES key that invalidates after biometric enrollment changes.
- Exact biometric challenges bind device, action reference, payload hash, nonce and expiry. The
  trusted phone signs only after local biometric or device-owner authentication; the mother treats
  this as possession confirmation and never as biometric identity inference. APNs/FCM tokens are
  encrypted, background events are idempotent, notification bodies contain no private content and
  provider acceptance remains distinct from human delivery.
- Swift native-core compilation and tests pass. SwiftUI and Android Compose source shells,
  permissions, deep links, background handlers and private notification policies are present.
  `MOB-1101` and `MOB-1102` remain open because this Mac lacks full Xcode/iOS and Android build
  toolchains and no authorized Apple/Android signing identities or physical-device evidence exist.
- **3 September 2026:** completed `MOB-1202`. Call participant keys now require possession-signed
  registration. Each WebRTC epoch requires both parties to sign fresh X25519 transport keys, DTLS
  fingerprints and nonces. Connect fails until both records match the current epoch; reconnect
  requires a new epoch and replay is rejected. The mother stores only a public handshake commitment
  and holds no media session key.
- **Verification:** all **579 AION Fabric tests** pass and the native Swift package adds two passing
  compiled tests. The append-only native/WebRTC LaTeX section compiles. Independent WebRTC media
  audit (`MOB-1201`), signed binaries, push-provider field delivery and physical-device tests remain
  explicitly open.

- **3 September 2026:** completed `MOB-0807`. A possession-signed phone can deliberately present
  a personal briefing or an authorized Workspace/Boardroom briefing, dashboard or repository file
  on the television. The mother revalidates the active persona, signed surface manifest,
  membership and provider capability before retrieving content.
- Private presentation bodies are bounded, secret fields are stripped, and content exists only in
  volatile mother memory for at most ten minutes and never beyond the shared-screen session.
  Durable evidence is hash-only. Dismissal, logout, identity change, authority expiry and surface
  lock purge the presentation; presentation grants no action or approval authority.
- **3 September 2026:** completed `MOB-1001`, `MOB-1003` and `MOB-1007`. The ownership authority
  builds signed, secret-free packages for personal-computer, home-server, private-VPS and business
  profiles. Runtime state, environment files, credentials and secret-named material are excluded,
  and every included file and configuration is integrity-bound.
- The existing `Connect to my Pilot` browser flow was verified as the customer-owned remote-access
  implementation: it discovers the entered HTTPS mother directly, pins its signed identity,
  compares trust words, completes local six-digit confirmation and retains the phone's private key
  locally. It does not require a Tessaris-held mother secret or readable customer-data copy.
- Complete-mother migration now emits a source-signed capsule containing an authenticated encrypted
  backup. Restore verifies the source identity, ciphertext, paths and regenerated file manifest,
  preserves identity, permissions, messages and proofs, and explicitly requires primary cut-over
  rather than silently authorizing two writable mothers.
- **Verification:** all **571 AION Fabric tests** and the optimized mobile production build pass;
  both append-only LaTeX sections compile. The live television session was not restarted. Physical
  two-person presentation and two-host migration rehearsals remain field closure gates.
- **3 September 2026:** completed `MOB-1005` and the coded Stage 10 implementation. Advanced
  customers can run the opaque relay as a separate TLS 1.2+ service with signed mother-route
  registration, distinct phone-submission and mother-poll capabilities, bounded ephemeral queues,
  expiry, deduplication, request-size controls and per-address rate limiting.
- The operator holds no payload-decryption key and sees no plaintext fields. A complete live HTTPS
  request/response test proves that private input and result remain encrypted through the service;
  unsigned route registration is rejected. The relay is optional and its loss cannot remove local
  access or customer-owned mother data.
- **Verification:** the complete suite now contains **573 passing AION Fabric tests**. The expanded
  deployment/migration/relay LaTeX section compiles cleanly. Public-certificate, firewall,
  saturation, relay-restart and two-host migration exercises remain production field gates.

- **3 September 2026:** completed `MOB-0805`. The laptop dashboard and television canvas now
  render Personal, Household, Workspace and Boardroom tiles from the same mother-signed
  shared-surface authority. Personal and Household tiles require an active shared-screen persona;
  Workspace and Boardroom tiles additionally require a current signed membership whose scopes
  intersect the provider's declared capabilities.
- The locked screen shows disabled generic authority domains and does not disclose organisation
  names or attach launch operations. A second persona cannot inherit another person's business
  tiles. Workspace labels, roles and exact capabilities come from a short-lived signed provider
  manifest, and unchanged manifests are reused rather than written on every TV polling cycle.
- **Verification:** all **568 AION Fabric tests** pass. The append-only authority-derived tile
  LaTeX section compiles. A physical two-identity television exercise remains an explicit Stage 8
  closure gate; repository-backed presentation remains `MOB-0807`.

- **3 September 2026:** completed `MOB-0804`. The shared television now has independent
  five-minute inactivity and trusted-phone-presence deadlines. Real actions renew inactivity;
  a possession-signed heartbeat received directly on the local network renews presence without
  counting as activity. Either expiry locks the identity and records an auditable reason.
- The mobile controller proves presence every 30 seconds only while visible and online. Remote and
  opaque-relay routes remain valid for authorized commands but cannot prove household proximity.
  Explicit signed logout, device revocation and account recovery remain immediate lock paths.
- **Verification:** all **567 AION Fabric tests** and the optimized mobile production build pass;
  the append-only automatic-lock LaTeX section compiles. A physical two-person timeout and
  departure exercise remains an explicit Stage 8 closure gate.

- **3 September 2026:** completed the coded portion of `MOB-0309` with automatic online/offline
  and foreground network-change handling, LAN live-socket recovery and route-aware direct/relay
  snapshot fallback. Only one poll may run, stale requests are aborted, and independent jittered
  retry intervals are capped at 30 seconds.
- The phone persists a mother/device-scoped Inbox revision, rejects stale snapshots, retains
  existing idempotency keys and displays the active `lan`, `direct` or `relay` transport without
  changing the underlying identity or authority. The real carrier roaming exercise remains an
  explicit Stage 3 field gate.
- **Verification:** all **565 AION Fabric tests** and the optimized mobile production build pass;
  the append-only network-roaming LaTeX section compiles without warnings.

- **3 September 2026:** completed `MOB-0308` with a mother-signed opaque relay route and
  direction-separated X25519/HKDF/AES-256-GCM request and response envelopes. The requested path,
  phone authority and private body remain encrypted; the relay retains only bounded ciphertext
  and minimum routing metadata.
- The phone follows LAN, signed direct endpoints, then relay, and never treats a policy or
  application denial as a transport failure. The bounded reference queue rejects wrong
  capabilities, expires envelopes and deduplicates request identifiers without holding a
  decryption key.
- No Tessaris relay deployment is claimed. The optional route is issued only when an owner supplies
  `PILOT_RELAY_ENDPOINT`; automatic roaming is implemented by `MOB-0309`, with its physical-phone
  field exercise still open.
- **Verification:** all **564 AION Fabric tests** and the optimized mobile production build pass;
  the append-only relay LaTeX section compiles without warnings.

- **3 September 2026:** completed `MOB-0307` with a mother-signed, phone-cacheable direct
  remote-route descriptor. The phone always attempts its paired LAN endpoint first and tries a
  configured customer-owned HTTPS endpoint only after a network-level failure.
- Each candidate must appear in the unmodified signed descriptor and present a fresh descriptor
  for the original mother identifier and key fingerprint. Authorization and application errors do
  not trigger failover. Existing certificates, leases, request signatures, revocation and
  idempotency remain authoritative across both addresses.
- No relay, automatic router modification or public reachability is claimed. The current runtime
  reads optional endpoints from `PILOT_REMOTE_ENDPOINTS`; relay and roaming were completed
  separately in `MOB-0308` and `MOB-0309`.
- **Verification:** all **560 AION Fabric tests** and the optimized mobile production build pass;
  the append-only direct-route LaTeX section also compiles cleanly.

- **3 September 2026:** completed `MOB-0212` by replacing the cumulative phone-controller
  stream with one grouped, contextual panel router. The complete manifest remains available in
  a categorized selector; TV, Tasks, Calendar and Devices remain one-tap quick controls.
- Changing product mode or primary navigation now clears stale tool state. Inbox, Actions, Spaces,
  Me, Memory and Guardian no longer stack unrelated panels or generic cards beneath one another.
- **Verification:** all **557 AION Fabric tests** and the optimized mobile production build pass. The
  representative real iPhone/Android viewport exercise remains explicitly open as `MOB-0216`.

- **3 September 2026:** completed `MOB-1403` with one relationship-gated handoff contract for
  private messages, approval-gated tasks, scheduled reminders, encrypted files and rights-safe
  Moments. The phone Inbox exposes one compact composer; revoked or mismatched relationships are
  denied before encryption. Task delivery requires a second possession-signed approval, and
  encrypted-packet creation is not represented as human receipt or acceptance.
- **Verification:** all five object types traverse the existing encrypted Inbox contract; destination-
  mother receipt, task acceptance, idempotency, relationship revocation and protected-media denial
  have automated coverage. No Tessaris conversation store or relay is required.
- **3 September 2026:** implemented useful-request contact, employer, client and Boardroom
  invitations; household/family/friend/professional scopes; exact post-onboarding continuation;
  consent-gated unreadable contact-discovery tokens; aggregate activation metrics; portable
  relationship export; and bilateral revocation/deletion that denies future contact.
- Household, freelancer, employee and Boardroom field pilots plus independent
  security/privacy/legal review remain external closure gates.
- **Full regression:** all **555 AION Fabric tests pass** after Stages 9--14, and the append-only
  LaTeX sections compile.  The running household Pilot/TV session was not
  restarted or altered during this work.

- **3 September 2026:** added a hidden, hardware-gated Wave transport authority with signed and
  revocable bridge leases, bounded fragmentation, inbound sequence/hash/signature verification,
  TTL, idempotency, priority, retries, congestion bounds and duplicate suppression.  It reports
  queued, attempted and locally reconstructed states without claiming physical radio delivery.
- Existing GlyphNet radio-node/WirePack foundations still require a deliberate compatibility
  adapter; real BLE/Wi-Fi Direct/RF drivers, qualified hardware, regional compliance and a two-
  mother internet-disconnected field test remain open.  The ordinary product manifest continues
  to hide radio, wallet and PHO.

- **3 September 2026:** implemented the Stage 12 call lifecycle and group authority.  It covers
  invite, ring, answer, decline, cancel, connect, reconnect and end states; signed participant
  transitions; per-reconnect key epochs; owner/admin/member/child roles; guardian approval;
  removal-triggered group-key rotation; replies, mentions, reactions, bounded attachment
  references, blocks, reports and rate limits.
- Pilot still labels media encryption as not independently audited.  A native authenticated
  WebRTC implementation, external cryptographic audit and loss/jitter field qualification remain
  open rather than being inferred from the state-machine tests.

- **3 September 2026:** added the shared native-mobile security authority used by future iOS and
  Android shells: signed single-use links for pairing, invitations, tasks, approvals and TV
  takeover; lock-bound AES-GCM cache; protected notification previews; clipboard and screenshot
  policy; explicit camera/microphone/PTT indicators; and battery, thermal, network and lifecycle
  records that close sensitive surfaces on suspension.
- Actual Swift/Kotlin applications, platform hardware-keystore binding, background push delivery,
  representative accessibility/child tests and Apple/Google signing remain open and external.

- **3 September 2026:** implemented the Stage 10 customer-ownership core for personal-computer,
  home-server, private-VPS and business deployment choices.  Added signed direct connection
  descriptors, phone-sealed minimum-metadata rendezvous records, AES-256-GCM/scrypt encrypted
  backups with verified restore, a signed single-writable-primary lease, signed staged updates
  with health rollback, and redacted diagnostic reports.  No Tessaris data copy is required.
- Stage 10 deliberately remains open: clean distributable packages for all four targets, a complete
  browser remote transport, a deployable self-host relay, and a rehearsed whole-mother migration
  are larger release/infrastructure deliverables and have not been represented as complete.

- **3 September 2026:** completed Stage 9's versioned selective proof rail.  Structured Pilot
  tasks now emit authorization, delivery and acceptance commitments through an optional
  privacy-minimised adapter to the existing GlyphChain proof store.  The durable local rail stores
  only opaque object references, canonical hashes, policy versions, timestamps and bounded
  outcomes; source task and receipt content remains mother-private.
- Added idempotent proof emission, append-only corrections, deletion tombstones, signature and
  source-record verification, distinct application/chain health, and explicit best-effort,
  required and local-only publication policies.  PHO, wallets, tokens, payments and escrow remain
  disabled and are never imported as action dependencies.
- **Verification:** private-string inspection, altered-receipt, altered-commitment, duplicate,
  correction, deletion, chain-outage, required-publication and end-to-end task lifecycle tests pass.

- **3 September 2026:** created the isolated `backend.modules.pilot_unified` contract package.
- Added versioned identity, device, possession, space, membership, invitation, lease, active-context,
  conversation, attachment, message, action, approval, execution, receipt, surface, service and
  memory-reference contracts.
- Added read-only compatibility projections for current Pilot identity, devices, tasks, contacts,
  communication drafts, GlyphNet events and Boardroom workspaces.
- Legacy approvals are deliberately returned to awaiting approval when no production possession
  proof exists.
- Added a default mobile feature policy that removes PHO, PhotonPay, wallet, token, bond, staking
  and minting capabilities and rejects their direct routes and requests.
- Added one shared Personal/Workspace/Boardroom fixture for later clients.
- Added collision, stale authority, confused-deputy, cross-space, replay, malicious identifier,
  payload-bound, false-state-transition, legacy-approval and economic-feature isolation tests.
- **Verification:** all 422 AION Fabric tests passed. The live Pilot runtime and user stores were
  not migrated or restarted.
- **3 September 2026:** added the fixture-driven `/pilot/mobile` reference client to the existing
  Next.js application, with Personal/Workspace/Boardroom modes, contextual signed-manifest
  shortcuts, a persistent Pilot composer, grouped daily cards, protected notification previews,
  accessible controls and persistent bottom navigation.
- Added a scoped installable-web-app manifest, Pilot aircraft icon and network-first offline shell.
  The reference route and install assets return HTTP 200 locally. A narrow legacy-response typing
  correction removed the pre-existing Workflow Architect build blocker; the full optimized Next.js
  production build now compiles and statically generates `/pilot/mobile` successfully.
- Added mobile-surface regression checks and an append-only technical LaTeX section. The full
  AION Fabric suite now passes **427 tests**, and the LaTeX section compiles without warnings.
- **3 September 2026:** added mother-bound mobile pairing using signed HTTPS discovery,
  single-use five-minute challenges, mother-screen-only six-digit confirmation, Ed25519 phone
  possession, signed phone certificates and bounded renewable capability leases.
- Bound mobile trust to the existing Production Private Identity registry so lost-phone removal
  immediately terminates mobile validation and shared-screen authority rather than creating a
  second identity store.
- Added an exact-origin, rate-limited TLS service and protected browser-key implementation. The
  private key becomes non-extractable before it enters IndexedDB; exported setup bytes are erased.
- Added non-technical connection and repair states to the reference mobile shell. Remote P2P,
  unreadable relay transport and real Wi-Fi/mobile-data roaming remain open and are not simulated.
- **Verification:** all **437** AION Fabric tests pass, the optimized mobile production build
  compiles, and the append-only Stage 3 LaTeX section compiles without warnings.
- **3 September 2026:** implemented the first encrypted GlyphNet/Pilot Inbox transport bridge.
  Two isolated mother brains can exchange signed and X25519/AES-GCM-encrypted text and structured
  task packets without a development token or plaintext transport journal.
- A sender prepares an exact task, approves its unchanged scope from a possession-bound phone,
  and receives a private delivery receipt. The recipient mother verifies and decrypts the packet,
  imports one pending delegation into the existing Pilot Inbox authority, and requires the
  recipient's independently trusted phone to accept or decline it.
- Durable idempotency and packet-replay records prevent duplicate messages and tasks. Altered
  packets, changed idempotency content, cross-person reads and revoked phones fail closed.
- **Verification:** all **442** AION Fabric tests pass and the append-only Stage 4 LaTeX section
  compiles without warnings.
- **3 September 2026:** added the possession-authenticated TLS live Inbox with revision-cursor
  resume, bounded reconnect, strict origin control and no mutation authority. All **444** Fabric
  tests pass and the optimized mobile production build succeeds.
- **3 September 2026:** completed the bilateral structured-task lifecycle. Sender corrections and
  cancellations cross mothers as signed encrypted update packets; recipient read, acceptance,
  decline, snooze, completion, failure and expiry states return as signed content-free receipts.
  Durable idempotency prevents repeat phone actions from producing duplicate state changes, and
  both the Unified Inbox projection and authoritative personal task store reconcile together.
- **Verification:** all **446** AION Fabric tests pass and the optimized mobile production build
  compiles and statically generates the Pilot mobile route successfully.
- **3 September 2026:** added bounded encrypted Inbox attachments and one persona-authorized search
  surface across messages, tasks and files. Attachment bytes are hash-verified, encrypted before
  local storage, carried only inside authenticated peer packets and released only to a currently
  authorized participant. The phone can search the live mixed stream and securely download a
  verified attachment without creating separate message or file silos.
- **Verification:** all **449** AION Fabric tests pass, the optimized mobile production build
  succeeds, and the append-only Stage 4 LaTeX record compiles successfully.
- **3 September 2026:** completed the coded Stage 4 voice and structured-work surface. Voice notes
  are size-, duration- and retention-bounded, encrypted at rest and in peer packets, and become
  unavailable after expiry. Push-to-talk uses a mother-issued fifteen-second floor bound to the
  exact persona, signed phone device, active capability lease and conversation; another phone
  cannot steal or renew it, and an expired floor can be safely reacquired.
- Added reminder, follow-up, calendar and document-review cards with validated exact scope. These
  cards remain proposals: displaying or transporting one never implies provider execution.
- The phone now records only while the user holds the reply control, visibly indicates recording,
  renews the floor while held, stops local tracks on release or failure, and plays received notes
  only after a fresh authorized encrypted-attachment read.
- **Verification:** all **452** AION Fabric tests pass and the optimized phone build succeeds.
- **3 September 2026:** began Stage 5 with a phone-signed Personal Pilot projection over the
  existing Production Private Identity and Pilot Inbox authorities. It exposes the active adult,
  only that adult's guardian-controlled child profiles, and the persona's real lists, tasks,
  reminder summary and contact count. Other adults' private identity and work are filtered out.
- The unified phone now replaces its personal summary with live task data after secure pairing.
  The projection grants no shared-TV identity and creates no second personal database.
- **Verification:** all **455** AION Fabric tests pass, both append-only LaTeX sections compile,
  and the optimized mobile production build succeeds.
- **3 September 2026:** connected exact time, closing-time, daily, weekly and weekday reminders
  to the signed phone surface. Arrival, departure and journey reminders require a current
  `pilot_location` consent for `reminder.location` issued to that same phone. Raw location
  history is not retained.
- Reminder create, snooze, complete and cancel requests are persona-bound and idempotent. Completing
  a repeating timed reminder atomically creates its next scheduled occurrence instead of silently
  losing the recurrence.
- **3 September 2026:** completed `MOB-0504`, connecting the unified phone Calendar shortcut to
  the existing governed calendar and persona-specific Google OAuth authorities. The phone can
  inspect its private normalized schedule, query title-free availability, prepare create,
  reschedule and cancel proposals, review exact calendar, dates, time zone, attendees, travel and
  reminder scope, acknowledge private conflicts, approve the immutable hash and separately execute.
- Calendar preparation is idempotent, changed retry scope fails closed, and repeated execution
  returns the original verified receipt. Credentials and vault references remain on the mother;
  shared-TV context cannot choose a person or calendar. Without an authorized provider adapter,
  the operation remains prepared or approved and reports the missing connection honestly.
- **Verification:** all **457** AION Fabric tests pass, the optimized Next.js mobile build compiles
  and statically generates `/pilot/mobile`, and the append-only calendar LaTeX section compiles.
- **3 September 2026:** completed `MOB-0505`, exposing persona-owned contacts through a dedicated
  signed phone surface. Users can list, search, add, edit and softly remove email, WhatsApp and
  Pilot-to-Pilot routes; a browser contact picker is used only after an explicit selection and
  remains optional.
- Exact names resolve directly, one unique phonetic match is labelled, ambiguous names require a
  private choice, and missing contacts remain unresolved. General Personal summaries conceal route
  values, shared-TV surfaces receive no contact details, and resolving a contact has no external
  effect. Writes and removals are idempotent while historical task and receipt evidence is retained.
- **Verification:** all **458** AION Fabric tests pass, the optimized Next.js mobile build compiles
  and statically generates `/pilot/mobile`, and the append-only Contacts LaTeX section compiles.
- **3 September 2026:** completed `MOB-0506`, projecting the existing governed communication
  authority into a private Email and Messages surface. A person can select a private contact and
  route, prepare exact AION Native content, inspect recipient, subject and body, approve the
  immutable content hash, and separately request provider execution.
- Missing sender accounts remain honestly blocked. Verified delivery requires a provider message
  identifier; uncertain attempts enter reconciliation rather than being retried, and repeat
  execution returns the original receipt. Received summaries retain sender, freshness and source
  provenance without retaining raw bodies and can become task or calendar proposals. Verified sent
  messages support conditional no-reply follow-ups, while calls require a final explicit phone tap.
- **Verification:** all **460** AION Fabric tests pass, the optimized Next.js mobile build compiles
  and statically generates `/pilot/mobile`, and the append-only communication LaTeX section compiles.
- **3 September 2026:** completed `MOB-0507`, connecting shopping, booking, route and music
  proposals to the signed private phone through the existing provider-independent Service
  Execution Hub. When a mother has exactly one adult identity, that adult may safely adopt its
  earlier local service persona so existing proposals and opaque provider bindings survive.
  Multi-adult households and child identities receive isolated service personas and bindings.
- The phone now shows exact parameters, collects missing private details, approves the immutable
  parameter hash and requires a separate execution action. Raw passwords, tokens, private keys,
  card numbers, CVVs and PINs are rejected. Child profiles cannot approve or execute external
  service effects, shared screens cannot choose an account, and absent adapters fail honestly.
- **Verification:** all **463** AION Fabric tests pass and the optimized Next.js application
  compiles and statically generates `/pilot/mobile`. No purchase, booking, route or media-account
  action was executed against a real provider.
- **3 September 2026:** completed `MOB-0508`, unifying encrypted Inbox files, television-saved
  products, recipes, destinations, music, learning material and ideas, evidence-backed research
  and phone continuation inside the Personal Files shortcut. A television save remains unowned
  until claimed from a trusted phone; every read, claim, continuation and deletion is signed,
  capability-scoped and persona-bound.
- Research hands only public HTTPS evidence targets to the phone; local, private, loopback,
  link-local, multicast and reserved network targets are removed. Shortlist, task and learning
  continuations remain local drafts. Shopping, trip and playlist continuations create a new
  immutable service proposal and never inherit purchase, booking or account-write authority.
  Content-bound idempotency protects continuation and deletion retries while deletion preserves
  historical audit and independent approval records.
- **Verification:** all **464** AION Fabric tests pass, the optimized Next.js application compiles
  and statically generates `/pilot/mobile`, and the append-only Files and Continuation LaTeX
  section compiles. No external service action was executed.
- **3 September 2026:** completed `MOB-0509`, projecting the existing Fabric node ledger, rooms,
  signed capability summaries and local infrared status into dedicated Devices and TV mobile
  surfaces. Public keys, pairing secrets, local addresses, endpoints and raw infrared codes are
  removed. User-requested discovery remains observe-only and cannot enroll or control a node.
- TV mutation now requires an exclusive five-minute shared-screen session acquired with a nested
  signed possession proof from the same paired phone. Observation remains separately scoped and
  non-mutating. Directional, media and allowlisted application controls reuse the governed webOS
  adapter and verified-navigation idempotency; button delivery alone is never claimed as a visual
  outcome. Learned infrared presets require a separate signed IoT scope and remain explicitly
  labelled transport-delivered but device-state-unverified.
- **Verification:** all **465** AION Fabric tests pass, the optimized Next.js application compiles
  and statically generates `/pilot/mobile`, and the append-only Device Mesh and TV LaTeX section
  compiles without warnings. No live device was enrolled or controlled by the automated suite.
- **3 September 2026:** completed `MOB-0510`, connecting AION's existing local learning curriculum,
  governed GeForce NOW handoff, private game shortcuts, entertainment personalisation and verified
  provider execution to dedicated mobile panels. Game sessions are now persona-bound, television
  launches require the active shared-screen session, and prepared, provider-open, entitled and
  playing remain distinct states. Focused authority, privacy, gaming and mobile-surface tests and
  the optimized mobile production build pass; no provider login, stream or playback was changed.
- **3 September 2026:** completed `MOB-0511`, exposing the existing private-memory authority through
  signed, separately scoped read, write and export endpoints. The phone can inspect, explicitly add,
  correct, rescope, export and permanently delete its own records; an adult may manage only their
  guardian-linked child profiles. Other-adult access fails closed. Memory mutations are replay-safe,
  exported JSON excludes recovery hashes and device public keys, focused authority and surface tests
  pass, and the optimized mobile production build compiles successfully.
- **3 September 2026:** completed `MOB-0512`, connecting Pilot Guardian to a large private-phone
  priority surface under separate read, configure and alert scopes. Contacts require explicit
  emergency-interruption and optional location permission; requesting help sends nothing until a
  second large confirmation. Provider-verified delivery and connectivity fallback are distinct,
  every state denies ambulance dispatch, and confirmation/delivery retries are idempotent. All 27
  focused Guardian, identity and mobile tests and the optimized production build pass without
  sending a real alert.
- **3 September 2026:** completed `MOB-0513`. The mobile composer now sends signed private requests
  to AION rather than presenting a placeholder. AION Native is the default and local capability,
  memory, local model and public evidence precede Gemini or premium compute. The phone shows the
  active route and requires confirmation before enabling a cloud-capable ceiling. Provider keys and
  secret paths remain on the mother. All 29 focused intelligence, authority and mobile tests and the
  optimized production build pass.
- **3 September 2026:** completed `MOB-0601`, adding a provider-independent Workspace Gateway that
  binds canonical spaces to replaceable provider references without copying Boardroom records.
  Every mobile projection requires one active persona-bound membership and either the exact named
  surface scope or bounded workspace read authority. Wrong-person, suspended, expired,
  cross-client and unsupported-surface requests fail closed. Focused gateway and contract tests
  pass, and the append-only technical LaTeX section compiles independently.
- **3 September 2026:** completed `MOB-0602`. The mother now publishes a canonical, Ed25519-signed,
  short-lived workspace manifest binding one person, phone surface, workspace, membership and lease
  to bounded department, agent, dashboard, file, package and decision references. Permitted actions
  must be declared by both provider and membership. Tampering, scope expansion and excessive expiry
  fail closed; focused manifest and gateway tests pass and the append-only LaTeX compiles.
- **3 September 2026:** completed `MOB-0603`, adding exact, expiring and revocable Workspace and
  Boardroom invitations. An inviter can offer only scopes already held under an active membership;
  discovery creates no membership. Constraints use a bounded allowlist, creation is content-bound
  and replay-safe, and cross-space or overbroad grants fail closed. Focused invitation tests pass.
- **3 September 2026:** completed `MOB-0604`. The unified phone Spaces view now privately displays
  organization, inviter, role, scopes, constraints and expiry, then signs an exact accept or decline
  response. Acceptance creates only the offered membership and a possession-bound decision receipt;
  decline grants nothing. Forged, cross-person, expired and conflicting responses fail closed.
  Focused tests and the optimized mobile build pass.
- **3 September 2026:** completed `MOB-0605`, enforcing role changes, suspension, restoration,
  expiry and revocation against the live membership revision on every workspace read and manifest.
  Administrators require same-workspace management authority and cannot grant scopes they do not
  hold. Each mutation returns a hashed immediate-enforcement receipt; lifecycle and abuse tests pass.
- **3 September 2026:** completed `MOB-0606`. A read-only AION Boardroom adapter now projects the
  existing business repositories into signed, membership-gated mobile briefings, department work
  and dashboard summaries. Recursive allowlists remove credentials, tokens, keys and contact fields;
  raw business containers remain authoritative and local. Focused tests and the optimized app pass.
- **3 September 2026:** completed `MOB-0607`. The phone now sends possession-signed, membership-
  scoped turns to the selected Workspace or Boardroom Pilot. Finance reuses its permanent,
  evidence-grounded conversation authority; other departments expose only bounded work-record
  briefings until a specialist conversation engine exists. Every response is read-only, labels its
  reliability and provider, and is rejected if a provider claims an external write. Fifteen focused
  gateway tests and the optimized Next.js mobile build pass.
- **3 September 2026:** completed `MOB-0608`. Existing departmental work becomes bounded private
  review cards with a deterministic scope hash. Review, correction, prepared delegation and exact
  approval require current membership plus separately scoped phone authority. Stale cards fail
  closed, retries are content-bound and idempotent, and approval is explicitly not execution.
  Seventeen focused gateway tests and the optimized mobile build pass.
- **3 September 2026:** completed `MOB-0609`. Accountant, auditor, adviser and director packages
  bind one unchanged review card, exact statement, declared professional capacity, organization
  membership and possession-signed phone request. Role-specific scopes prevent substitution;
  changed or previously decided packages fail closed. Receipts preserve only a phone-signature
  hash, claim no external write, and are independently hash-verifiable. Twenty-two focused tests
  and the optimized mobile build pass.
- **3 September 2026:** completed `MOB-0610`. The AION Boardroom adapter exposes a bounded file
  catalogue from the existing workspace cabinet without paths or contents. A cross-space handoff
  creates only a redacted reference after both source and target memberships authorize it; no
  bytes are copied and opening it must reauthorize against the source organisation. Unknown files,
  same-space misuse and missing target authority fail closed. Twenty-four focused tests and the
  optimized mobile build pass.
- **3 September 2026:** completed `MOB-0611`. The phone can explicitly hand complex setup and deep
  work to the existing desktop Boardroom route using a five-minute, mother-signed context ticket.
  The ticket binds person, membership, workspace, provider and purpose, but grants no workspace
  access and requires desktop authentication. Its token is hash-bound, expiry is bounded and
  retries are content-idempotent. Twenty-six focused tests and the optimized mobile build pass.
- **3 September 2026:** completed `MOB-0612`. Workspace surface names cannot address Personal
  Pilot, and the gateway now recursively rejects a provider projection containing Personal memory,
  identity, calendar, tasks, child, home-device, location or payment namespaces. Organization
  administrator scope never substitutes for a persona-bound phone certificate or Personal scope.
  Forty-two combined Workspace and Personal authority tests pass.
- **3 September 2026:** completed `MOB-0613` and the coded Stage 6 implementation. Adversarial tests
  cover malicious provider payloads, cross-workspace administration, overbroad role grants, wrong
  professional role, stale hashes, and immediate expiry across every Stage 6 surface. The complete
  AION Fabric regression now passes all **499 tests**; the optimized mobile build and all seven new
  append-only Stage 6 LaTeX sections compile. Representative real multi-organisation field
  qualification remains visible as a closure gate.
- **3 September 2026:** completed the provider-independent portion of Stage 7. Persona-bound Gmail
  authority, exact attachment scope, honest provider-accepted and delivered states, reply
  conversion, no-reply follow-ups, bounded non-user invitations, invitation claims, blocking,
  reporting and child controls are coded. Official SMS and WhatsApp providers remain external.
  The complete Fabric suite passes **502 tests**, the mobile build succeeds and the append-only
  Stage 7 LaTeX section compiles.
- **3 September 2026:** completed seven of ten Stage 8 tasks. The live dashboard launcher now comes
  from a short-lived mother-signed surface manifest; private tiles follow the active phone-bound
  identity, locked rendering purges private presentation cache records, and existing LG control,
  observer, Devices and room-routing authorities are reused. Automatic trusted-phone departure,
  fully membership-derived workspace tiles and repository-backed full-screen presentation remain
  open. The expanded Fabric suite contains **504 tests**.
- **Stage 6 regression receipt:** all **481** AION Fabric tests pass after `MOB-0601` through
  `MOB-0605`; the optimized Next.js mobile build and all five append-only LaTeX sections compile.
  The active Pilot and television session were not restarted.

---

## Release targets

### Target A — Unified App Demonstrator

- [x] One responsive mobile application switches between Personal, Workspace and Boardroom.
- [x] A user pairs the app with their existing mother brain.
- [ ] Pilot conversation, Inbox, Actions, Spaces and Me use real local data.
- [x] Two local Pilot identities exchange a structured task with acceptance and receipts.
- [ ] Personal tasks and the existing TV controller work from the new shell.
- [ ] A Boardroom fixture supplies a real mobile briefing and one governed delegation.
- [x] Personal and organisation data remain isolated in automated boundary tests.

### Target B — Private Network Alpha

- [ ] A paired phone roams between trusted Wi-Fi and mobile data without manual re-entry.
- [ ] GlyphNet text, voice notes and push-to-talk use production Pilot identity.
- [ ] A real Personal Pilot service and a real Boardroom instance connect through adapters.
- [ ] Provider and non-Pilot messages stop honestly at prepared, approved, sent or verified states.
- [ ] Consequential actions produce private receipts and selective GlyphChain proof commitments.
- [x] Revoked phones, expired roles and replayed messages fail closed in automated boundary tests.

### Target C — Native Consumer and Business Beta

- [ ] Signed iOS and Android applications use hardware-protected keys where supported.
- [ ] Biometric approval, background delivery, safe notifications and deep links work on devices.
- [ ] A non-technical household installs, pairs and completes a useful action without a terminal.
- [ ] A professional accepts a bounded workspace invitation and cannot enumerate other departments.
- [ ] Backup, restore, update rollback and mother migration pass production exercises.
- [ ] Security, privacy, child-safety and business deployment reviews are complete.

---

## Stage 0 — Freeze the product boundary and reuse map

Goal: establish exactly which existing implementation is authoritative before new app work begins.

- [x] `MOB-0001` `[BUILD]` Declare this file the canonical mobile implementation checklist.
- [x] `MOB-0002` `[BUILD]` Create a component inventory covering Pilot Fabric, Personal Pilot,
  GlyphNet Browser, GlyphNet backend, Boardroom, AION identity, tasks, approvals, services,
  device control, memory and audit records.
- [x] `MOB-0003` `[BUILD]` Assign every overlapping schema an authoritative owner and version.
- [x] `MOB-0004` `[BUILD]` Mark old duplicate routes, stores and UI experiments as legacy without
  deleting evidence or historical data.
- [x] `MOB-0005` `[REUSE]` Record the existing Pilot persona, trusted-phone, shared-TV session,
  task, contact, approval and service-connection foundations.
- [x] `MOB-0006` `[REUSE]` Record GlyphNet chat, voice note, PTT, WebSocket, thread journal,
  transport and radio bridge foundations.
- [x] `MOB-0007` `[REUSE]` Record Boardroom departments, agents, dashboards, files, packages,
  decisions, evidence and approval foundations.
- [x] `MOB-0008` `[HIDDEN]` Put PHO, PhotonPay, wallets, balances, TESS, wrapped GLYPH, bonds,
  minting and development chain controls outside the default application manifest.
- [x] `MOB-0009` `[HIDDEN]` Ensure dormant economic routes cannot be invoked by voice, agent,
  deep link, browser manipulation or a hidden client button.
- [x] `MOB-0010` `[BUILD]` Publish the first dependency and risk register.

### Stage 0 closure

- [x] There is one owner for each identity, message, task, approval, receipt and space schema.
- [x] Reused, replaced, hidden and discarded components are explicitly recorded.
- [ ] The normal Pilot runtime starts and operates with the complete economic layer disabled.

---

## Stage 1 — Canonical contracts and migration layer

Goal: give every client and server one stable language before building the new interface.

### Identity and authority

- [x] `MOB-0101` `[BUILD]` Version Person, Persona, Guardian Profile and Household schemas.
- [x] `MOB-0102` `[BUILD]` Version Mother, Device, Surface and possession-proof schemas.
- [x] `MOB-0103` `[BUILD]` Version Personal, Household, Workspace, Engagement and Boardroom spaces.
- [x] `MOB-0104` `[BUILD]` Version Membership, Invitation, Role, Acceptance, Expiry and Revocation.
- [x] `MOB-0105` `[BUILD]` Version signed Capability Lease and constraint schemas.
- [x] `MOB-0106` `[BUILD]` Define an active-context object containing person, space, role, mother,
  device, lease, privacy level and expiry.

### Communication and action

- [x] `MOB-0110` `[BUILD]` Version the normalized GlyphNet/Pilot message envelope.
- [x] `MOB-0111` `[BUILD]` Version Conversation, Participant, Thread and Attachment references.
- [x] `MOB-0112` `[BUILD]` Version message types for text, voice note, PTT, call signalling,
  task proposal, approval, reminder, calendar, document review, delegation and provider handoff.
- [x] `MOB-0113` `[BUILD]` Version Action Proposal, Approval, Execution and Receipt records.
- [x] `MOB-0114` `[BUILD]` Define one state language: draft, needs-details, prepared, awaiting-approval,
  approved, queued, delivered, accepted, declined, executing, verified, failed, cancelled and expired.
- [x] `MOB-0115` `[BUILD]` Add idempotency, replay, correction, cancellation, expiry and supersession.
- [x] `MOB-0116` `[BUILD]` Version Surface Manifest, redaction rule, Memory Item, Service Connection
  and Provider Receipt contracts.

### Compatibility and migration

- [x] `MOB-0120` `[BUILD]` Add readers for existing Pilot persona, task, contact and approval records.
- [x] `MOB-0121` `[BUILD]` Add readers for existing GlyphNet threads and event journals.
- [x] `MOB-0122` `[BUILD]` Add Boardroom workspace and capability adapters without copying its database.
- [x] `MOB-0123` `[BUILD]` Preserve source identifiers and provenance during migration.
- [x] `MOB-0124` `[VERIFY]` Add identifier-collision, cross-space denial, confused-deputy,
  malicious-message, stale-lease and replay tests.

### Stage 1 closure

- [x] One person can hold unrelated Personal, Workspace and Boardroom roles without leakage.
- [x] Existing records load through adapters without irreversible migration.
- [x] No client obtains authority merely because it renders a button.
- [x] Contract fixtures are shared by mobile, mother brain, Boardroom gateway and TV surface.

---

## Stage 2 — Unified mobile shell and interaction design

Goal: make the product as understandable as a messaging application while retaining deep capability.

- [x] `MOB-0201` `[BUILD]` Create the responsive reference client as an installable mobile web app.
- [x] `MOB-0202` `[BUILD]` Create shared design tokens and accessible components ready for native reuse.
- [x] `MOB-0203` `[BUILD]` Build a clear Personal / Workspace / Boardroom swipe or segmented switcher.
- [x] `MOB-0204` `[BUILD]` Build persistent Pilot, Inbox, Actions, Spaces and Me navigation.
- [x] `MOB-0205` `[BUILD]` Build one persistent text and hold-to-speak Pilot composer.
- [x] `MOB-0206` `[BUILD]` Show active person, space, role, mother and connection state at all times.
- [x] `MOB-0207` `[BUILD]` Build Personal shortcuts for Calendar, Tasks, Devices, TV, Games, Learning,
  Shopping and Files without turning the app into a permanent long page.
- [x] `MOB-0208` `[BUILD]` Build Workspace shortcuts from the signed workspace manifest.
- [x] `MOB-0209` `[BUILD]` Build Boardroom shortcuts for Board, Sales, Marketing, Finance, Operations,
  Support, People, Products and Files when authorized.
- [x] `MOB-0210` `[BUILD]` Design message, task, reminder, approval, decision, delegation and receipt cards from manifest fixtures; live data binding remains Stage 4.
- [x] `MOB-0211` `[BUILD]` Add unmistakable prepared, pending, offline, expired, failed and verified states.
- [x] `MOB-0212` `[BUILD]` Replace the existing phone controller stream with grouped, contextual panels. *(One manifest-driven grouped selector now opens one tool at a time; changing mode or primary destination clears stale panels, while TV, Tasks, Calendar and Devices remain direct quick controls.)*
- [x] `MOB-0213` `[BUILD]` Keep universal controls such as TV remote and camera observer easy to reach.
- [x] `MOB-0214` `[BUILD]` Add dynamic type, screen-reader labels, contrast, keyboard and reduced motion.
- [x] `MOB-0215` `[BUILD]` Add private notification previews that hide protected content by default.
- [x] `MOB-0216` `[VERIFY]` Test representative small and large iPhone and Android viewports. *(Verified at 320x568, 360x800 and 430x932 with no horizontal overflow and all visible controls at least 44x44.)*

### Stage 2 closure

- [x] The user can reach every represented daily action within two navigational decisions.
- [ ] Personal, Workspace and Boardroom are unmistakable in usability tests.
- [x] The reference shell operates entirely from Stage 1 fixtures with no hard-coded household names.
- [x] Empty, loading, locked, offline, denied and expired states are designed rather than omitted.

---

## Stage 3 — Private pairing, mother discovery and remote continuity

Goal: make the phone a secure key and client of a user-selected mother brain.

- [x] `MOB-0301` `[REUSE]` Adapt rotating QR and human-verifiable pairing codes.
- [x] `MOB-0302` `[BUILD]` Create short-lived single-use mother pairing challenges.
- [x] `MOB-0303` `[BUILD]` Generate a device key in platform-protected storage where available.
- [x] `MOB-0304` `[BUILD]` Verify mother identity and resist QR substitution and fake endpoints.
- [x] `MOB-0305` `[BUILD]` Issue, rotate, expire and revoke phone certificates and capability leases.
- [x] `MOB-0306` `[BUILD]` Prefer direct trusted-LAN access and discover the mother locally.
- [x] `MOB-0307` `[BUILD]` Add an encrypted peer-to-peer remote route. *(A bounded mother-signed set of customer-owned HTTPS endpoints is cached during pairing; the phone prefers LAN and accepts a remote candidate only after it proves the original mother identity.)*
- [x] `MOB-0308` `[BUILD]` Add an end-to-end encrypted relay fallback whose operator cannot read content. *(The phone encrypts the complete operation to the paired mother's X25519 key; a bounded relay sees only opaque routing metadata and ciphertext, and the mother encrypts the response to the phone's one-use ephemeral key.)*
- [x] `MOB-0309` `[BUILD]` Add automatic Wi-Fi/mobile-data roaming and bounded reconnection. *(The phone reacts to online/offline and foreground changes, resumes from its persisted revision, uses single-flight polling while the LAN socket recovers, aborts stale work and caps jittered retry intervals at 30 seconds.)*
- [x] `MOB-0310` `[BUILD]` Resume direct subscriptions without duplicating messages or actions. *(The persisted revision now spans LAN, direct and relay reconnection; real-network field qualification remains open.)*
- [x] `MOB-0311` `[BUILD]` Add device inventory, lost-phone revocation and active-session termination.
- [x] `MOB-0312` `[BUILD]` Add recovery codes and an explicit key-recovery policy.
- [x] `MOB-0313` `[BUILD]` Explain connection and repair states in non-technical language.
- [x] `MOB-0314` `[VERIFY]` Prove that a revoked phone cannot reconnect, activate a TV or approve work.

### Stage 3 closure

- [ ] A paired phone moves from home Wi-Fi to mobile data and reconnects automatically.
- [ ] A malicious relay cannot decrypt application content or substitute a mother brain.
- [x] Lost-device revocation terminates messages, approvals and shared-screen authority.

---

## Stage 4 — GlyphNet Unified Inbox vertical slice

Goal: deliver the first complete useful journey before expanding every service.

### Core messaging

- [x] `MOB-0401` `[REUSE]` Adapt GlyphNet typed conversation and optimistic delivery, including the live persona-bound mobile stream.
- [x] `MOB-0402` `[HARDEN]` Replace `dev-token` and static Wave identities with Pilot possession and leases.
- [x] `MOB-0403` `[REUSE]` Adapt WebSocket live delivery, subscriptions and reconnect telemetry. *(Implemented with signed phone possession, revision cursors, bounded exponential reconnect and zero duplicate replay.)*
- [x] `MOB-0404` `[BUILD]` Encrypt message content and attachments at rest on the mother brain.
- [x] `MOB-0405` `[HARDEN]` Authenticate payload encryption with audited key establishment and rotation.
- [x] `MOB-0406` `[BUILD]` Keep sender, recipient, active space and privacy label on every item.
- [x] `MOB-0407` `[BUILD]` Add delivery, read, accepted, declined, failed and expired receipts.
- [x] `MOB-0408` `[BUILD]` Add correction, cancellation, retry and duplicate suppression.
- [x] `MOB-0409` `[BUILD]` Add inbox search and filters without separate message silos.

### Voice and structured work

- [x] `MOB-0410` `[REUSE]` Adapt voice notes with local recording indicators and bounded retention.
- [x] `MOB-0411` `[REUSE]` Adapt PTT press/release, floor ownership, renewal and expiry.
- [x] `MOB-0412` `[HARDEN]` Bind PTT ownership to the production device and persona rather than browser tabs.
- [x] `MOB-0413` `[BUILD]` Implement structured Pilot-to-Pilot task proposals.
- [x] `MOB-0414` `[BUILD]` Require recipient acceptance before a delegated task becomes assigned.
- [x] `MOB-0415` `[BUILD]` Synchronize accept, decline, snooze, completion and cancellation on both mothers.
- [x] `MOB-0416` `[BUILD]` Add reminder, follow-up, calendar and document-review message cards.
- [x] `MOB-0417` `[HIDDEN]` Exclude all PHO, wallet and PhotonPay controls from Inbox routes.

### First vertical-slice acceptance

- [x] Alice asks Pilot to send Bob a named task.
- [x] Pilot privately resolves the exact Bob identity and shows the exact proposal.
- [x] Alice approves once; retry cannot create a duplicate task.
- [x] Bob receives an encrypted structured request through another mother brain.
- [x] Bob accepts or declines it; both sides reconcile the same state.
- [x] The accepted task appears in Bob's correct private or workspace task list.
- [x] Delivery and acceptance create private receipts and no plaintext chain or log content.
- [x] Revoking either participant's authority stops later unauthorized changes.

### Stage 4 closure

- [x] The complete vertical slice passes across two isolated test mothers.
- [x] Cross-person and cross-space mutation tests fail closed.
- [x] The phone verifies the mother, completes possession-bound pairing and loads only its persona's live Inbox stream.
- [ ] Text, voice-note and PTT delivery survive reconnect without duplication.

---

## Stage 5 — Personal Pilot integration

Goal: turn the new shell into a complete daily personal agent rather than a messenger alone.

- [x] `MOB-0501` `[REUSE]` Connect adult identities and guardian-controlled child profiles.
- [x] `MOB-0502` `[REUSE]` Connect personal and household task lists, delegation and acceptance.
- [x] `MOB-0503` `[REUSE]` Connect time, repetition and permitted location reminder proposals.
- [x] `MOB-0504` `[REUSE]` Connect calendar proposals, conflicts, availability and exact approvals.
- [x] `MOB-0505` `[REUSE]` Connect private contacts and recipient resolution.
- [x] `MOB-0506` `[REUSE]` Connect governed email and messaging drafts and receipts.
- [x] `MOB-0507` `[REUSE]` Connect shopping, booking and service-action proposals.
- [x] `MOB-0508` `[REUSE]` Connect files, saved items, research results and phone continuation.
- [x] `MOB-0509` `[REUSE]` Connect TV, device mesh and IoT status and control.
- [x] `MOB-0510` `[REUSE]` Connect learning, games and entertainment continuation.
- [x] `MOB-0511` `[REUSE]` Connect memory inspection, correction, scope, export and deletion.
- [x] `MOB-0512` `[REUSE]` Connect Guardian priority requests under separate emergency permissions.
- [x] `MOB-0513` `[BUILD]` Make AION Native the default intelligence route; keep premium providers optional.
- [ ] `MOB-0514` `[VERIFY]` Qualify at least one real task, calendar and communication provider.

### Stage 5 closure

- [ ] A user can run useful personal tasks without joining or owning a Boardroom.
- [ ] Shared-TV speech cannot choose a card, calendar, contact, account or identity automatically.
- [ ] Every provider action has an honest exact state and a verified receipt or clear failure.
- [ ] Removing all paid AI keys leaves core communication and task flows useful.

---

## Stage 6 — Workspace Gateway and Boardroom bridge

Goal: expose existing business intelligence without copying the Boardroom into the phone.

- [x] `MOB-0601` `[BUILD]` Implement the provider-independent Workspace Gateway.
- [x] `MOB-0602` `[BUILD]` Publish a signed workspace manifest of departments, agents, dashboards,
  files, packages, decisions and permitted actions.
- [x] `MOB-0603` `[BUILD]` Implement invitations with organization, inviter, role, requested scopes,
  constraints, expiry and revocation route.
- [x] `MOB-0604` `[BUILD]` Present invitation review and acceptance privately on the phone.
- [x] `MOB-0605` `[BUILD]` Add role changes, suspension, expiry and immediate revocation.
- [x] `MOB-0606` `[REUSE]` Adapt Boardroom briefings and departmental dashboards for mobile summaries.
- [x] `MOB-0607` `[REUSE]` Adapt Boardroom Pilot and departmental Pilot conversations.
- [x] `MOB-0608` `[BUILD]` Implement review, correction, delegation and approval cards.
- [x] `MOB-0609` `[BUILD]` Implement accountant, auditor, adviser and director sign-off packages.
- [x] `MOB-0610` `[BUILD]` Keep files organization-owned with redacted cross-space references.
- [x] `MOB-0611` `[BUILD]` Add explicit `Continue on desktop` handoff for complex setup and deep work.
- [x] `MOB-0612` `[BUILD]` Prevent an organization administrator from reading a participant's Personal Pilot.
- [x] `MOB-0613` `[VERIFY]` Add malicious-admin, overbroad-role and expired-membership tests.

### Stage 6 closure

- [ ] A freelancer enters one client's Marketing workspace but cannot enumerate Finance or People.
- [ ] The same freelancer joins an unrelated client without data or identity collisions.
- [ ] An accountant receives and signs one exact package with an independently verifiable receipt.
- [ ] A Boardroom owner reviews a briefing, delegates work and approves one governed decision.
- [ ] Expiry removes organization data while leaving Personal and other Workspace modes intact.

---

## Stage 7 — Non-Pilot recipients and connected services

Goal: make Pilot useful before every contact has Pilot and turn utility into a natural invitation.

- [x] `MOB-0701` `[REUSE]` Connect authorized email sending through persona-bound OAuth.
- [x] `MOB-0702` `[BUILD]` Add official SMS or equivalent delivery where permitted. *(Persona-bound Twilio SMS adapter with exact approval scope, idempotency and signed delivery callbacks; live account qualification remains an external exercise.)*
- [ ] `MOB-0703` `[EXTERNAL]` Connect WhatsApp only through an officially authorized platform route.
- [x] `MOB-0704` `[BUILD]` Display exact channel, recipient, content and attachments before approval.
- [x] `MOB-0705` `[BUILD]` Distinguish prepared, approved, provider-accepted and delivered states.
- [x] `MOB-0706` `[BUILD]` Convert replies into task, reminder and calendar proposals.
- [x] `MOB-0707` `[BUILD]` Add sender-requested follow-up such as no-reply reminders.
- [x] `MOB-0708` `[BUILD]` Create useful invitation artifacts that work for a non-user.
- [x] `MOB-0709` `[BUILD]` Deep-link an invited user to the exact pending request after onboarding.
- [x] `MOB-0710` `[BUILD]` Add blocking, reporting, contact limits and child protections.

### Stage 7 closure

- [ ] A non-user receives immediate utility without installing Pilot.
- [ ] Pilot never reports provider acceptance as human delivery or acceptance.
- [ ] Joining Pilot reveals the intended request but no unrelated sender or household data.

---

## Stage 8 — Television and connected-device continuity

Goal: make the phone the private key and controller for room-scale Pilot surfaces.

- [x] `MOB-0801` `[REUSE]` Connect existing LG controller, verified navigation and camera observer.
- [x] `MOB-0802` `[BUILD]` Replace hard-coded television tiles with signed Surface Manifests.
- [x] `MOB-0803` `[BUILD]` Add phone-authorized TV takeover and explicit active-person display.
- [x] `MOB-0804` `[BUILD]` Add logout, inactivity expiry and trusted-phone departure lock.
- [x] `MOB-0805` `[BUILD]` Render Personal, Household, Workspace and Boardroom tiles by authority.
- [x] `MOB-0806` `[BUILD]` Keep sensitive messages and approvals private unless deliberately presented.
- [x] `MOB-0807` `[BUILD]` Add deliberate full-screen document, dashboard and briefing presentation.
- [x] `MOB-0808` `[BUILD]` Verify that logout deletes cached private television presentation state.
- [x] `MOB-0809` `[REUSE]` Put device discovery and topology behind the Devices/IoT experience.
- [x] `MOB-0810` `[BUILD]` Route controls by room, capability, owner and active session.

### Stage 8 closure

- [ ] Two household identities receive different signed manifests on the same television.
- [ ] Five minutes of configured inactivity or explicit logout removes the private session.
- [ ] A Workspace participant sees only permitted business tiles and redacted data.
- [ ] A TV can disappear or change address without leaving stale approval authority behind.

---

## Stage 9 — GlyphChain selective proof rail

Goal: create tamper-evident proof without putting private life or business content on-chain.

- [x] `MOB-0901` `[REUSE]` Adapt existing AION proof commit and lookup foundations.
- [x] `MOB-0902` `[BUILD]` Define versioned authorization, delivery, acceptance and outcome commitments.
- [x] `MOB-0903` `[BUILD]` Commit opaque identifiers, hashes, policy versions, timestamps and outcomes only.
- [x] `MOB-0904` `[BUILD]` Keep message bodies, voice, files, contacts, memory, calendar, location,
  credentials and payment data off-chain.
- [x] `MOB-0905` `[BUILD]` Make proof emission idempotent and link corrections without rewriting history.
- [x] `MOB-0906` `[BUILD]` Verify a commitment from an authorized mother-private record.
- [x] `MOB-0907` `[BUILD]` Define deletion behaviour when an immutable non-identifying hash remains.
- [x] `MOB-0908` `[BUILD]` Separate chain health from app availability; messaging must fail safely or
  continue locally according to policy when proof publication is unavailable.
- [x] `MOB-0909` `[HIDDEN]` Keep PHO and all economic functions disabled during proof-rail testing.
- [x] `MOB-0910` `[VERIFY]` Prove through log and chain inspection that private payloads never leak.

### Stage 9 closure

- [x] A structured task produces authorization, delivery and acceptance proof commitments.
- [x] Independent verification detects modified local receipt data.
- [x] Chain unavailability cannot result in a false sent, accepted, paid or completed claim.
- [x] The proof rail operates without enabling a wallet or token balance.

---

## Stage 10 — Self-hosting, browser access and deployment choice

Goal: let individuals and organizations own the mother brain and data location.

- [x] `MOB-1001` `[BUILD]` Package clean personal-computer, home-server, VPS and business deployments.
- [x] `MOB-1002` `[BUILD]` Build guided local, private-cloud and customer-selected cloud setup.
- [x] `MOB-1003` `[BUILD]` Build `Connect to my Pilot` browser access without centralizing mother secrets.
- [x] `MOB-1004` `[BUILD]` Add optional minimum-metadata rendezvous and relay services.
- [x] `MOB-1005` `[BUILD]` Allow advanced users and businesses to self-host relay and rendezvous.
- [x] `MOB-1006` `[BUILD]` Add encrypted backups with visible last-success and restore verification.
- [x] `MOB-1007` `[BUILD]` Add complete mother export and migration.
- [x] `MOB-1008` `[BUILD]` Prevent two writable primaries during migration or recovery.
- [x] `MOB-1009` `[BUILD]` Add signed staged updates, health verification and automatic rollback.
- [x] `MOB-1010` `[BUILD]` Add one-click diagnostics and redacted support bundles.
- [x] `MOB-1011` `[BUILD]` Publish plain-language and technical ownership/privacy documentation.

### Stage 10 closure

- [ ] Local, remote and browser clients operate against the selected mother, not a Tessaris data copy.
- [ ] A mother migrates without losing identity, permissions, messages or proof continuity.
- [ ] Disabling Tessaris rendezvous does not destroy local access or customer-owned data.

---

## Stage 11 — Native iOS and Android applications

Goal: replace browser limitations with production device identity, notifications and lifecycle support.

- [ ] `MOB-1101` `[BUILD]` Build and sign the native iOS application.
- [ ] `MOB-1102` `[BUILD]` Build and sign the native Android application.
- [x] `MOB-1103` `[BUILD]` Use Secure Enclave, Keychain, Android Keystore or equivalent where supported.
- [x] `MOB-1104` `[BUILD]` Add Face ID, Touch ID or Android biometric approval as local possession
  confirmation, not biometric identity inference.
- [x] `MOB-1105` `[BUILD]` Add background inbox delivery and safe notification previews.
- [x] `MOB-1106` `[BUILD]` Add deep links for pairing, invitations, tasks, approvals and TV takeover.
- [x] `MOB-1107` `[BUILD]` Add app lock, secure local cache, clipboard and screenshot privacy policy.
- [x] `MOB-1108` `[BUILD]` Add camera observer, microphone and PTT permissions with clear indicators.
- [x] `MOB-1109` `[BUILD]` Add battery, thermal, network and background lifecycle instrumentation.
- [ ] `MOB-1110` `[VERIFY]` Complete accessibility, guardian/child and representative-device testing.
- [ ] `MOB-1111` `[EXTERNAL]` Complete Apple and Google signing, privacy declarations and review.

### Stage 11 closure

- [ ] Production devices pass possession, revocation, biometric approval and recovery tests.
- [ ] Background reconnect cannot duplicate a message, approval or action.
- [ ] Notification, task switcher and lock-screen states do not expose protected content.

---

## Stage 12 — Calls, groups and communication hardening

Goal: complete the communications product after the core Inbox is trustworthy.

- [ ] `MOB-1201` `[HARDEN]` Replace demonstration call encryption with audited end-to-end encryption.
- [x] `MOB-1202` `[BUILD]` Authenticate WebRTC participants and rotate session keys.
- [x] `MOB-1203` `[BUILD]` Add call invitation, ringing, answer, decline, cancel, end and reconnect states.
- [x] `MOB-1204` `[BUILD]` Add group membership, roles, removal, history and key-rotation policy.
- [x] `MOB-1205` `[BUILD]` Add reactions, replies, mentions and bounded attachment delivery.
- [x] `MOB-1206` `[BUILD]` Add abuse prevention, reporting, blocking and rate limits.
- [x] `MOB-1207` `[BUILD]` Add child-safe contact approval and guardian controls.
- [x] `MOB-1208` `[VERIFY]` Test loss, jitter, reconnection, participant removal and compromised devices. *(Deterministic adverse-network and authority tests cover incomplete/out-of-order negotiation, fresh reconnect epochs, removal, replay and forged possession signatures.)*

---

## Stage 13 — Optional radio and offline Wave transport

Goal: preserve the sovereign communications path without blocking the mainstream release.

- [x] `MOB-1301` `[HIDDEN]` Keep radio controls outside ordinary setup unless supported hardware exists.
- [x] `MOB-1302` `[REUSE]` Adapt radio framing, fragmentation, queues and store-and-forward foundations.
- [x] `MOB-1303` `[HARDEN]` Complete inbound RF application-payload reconstruction and integrity checks.
- [x] `MOB-1304` `[HARDEN]` Replace mock radio drivers and bridge authentication. *(Real reconnecting serial and authenticated WebSocket bridge paths are retained; no default secret, header-only credentials, v2 nonce/HMAC replay protection, explicit mock-route gate and mock auto-disable on a real link.)*
- [x] `MOB-1305` `[BUILD]` Enroll a bridge as a signed, revocable Fabric device capability.
- [x] `MOB-1306` `[BUILD]` Add TTL, deduplication, congestion, priority and retry rules.
- [ ] `MOB-1307` `[BUILD]` Add BLE and Wi-Fi Direct adapters only when genuinely implemented.
- [ ] `MOB-1308` `[EXTERNAL]` Qualify compatible ESP32/Raspberry Pi and radio hardware.
- [ ] `MOB-1309` `[EXTERNAL]` Verify regional frequency, power and duty-cycle compliance.
- [ ] `MOB-1310` `[VERIFY]` Deliver text and PTT between two mothers with internet physically disabled.

### Stage 13 closure

- [ ] Pilot distinguishes IP, relayed, queued and radio-delivered messages truthfully.
- [ ] Removing or revoking a bridge cannot silently reroute private traffic through an unsafe path.
- [ ] No radio capability is advertised without a real internet-disconnected field receipt.

---

## Stage 14 — Adoption, Pilot network and public launch

Goal: grow through useful coordination rather than an empty social-network invitation.

- [x] `MOB-1401` `[BUILD]` Add trusted-contact invitation, review and acceptance.
- [x] `MOB-1402` `[BUILD]` Add household, family, friend and professional relationship scopes.
- [x] `MOB-1403` `[BUILD]` Add Pilot-to-Pilot message, task, reminder, file and Moment handoffs. *(One relationship-gated, possession-signed composer routes all five types through the existing encrypted Inbox. Tasks require a separate exact approval; Moment cards reject protected media.)*
- [x] `MOB-1404` `[BUILD]` Add employer, client and Boardroom invitations.
- [x] `MOB-1405` `[BUILD]` Let an invitation continue the exact useful request after onboarding.
- [x] `MOB-1406` `[BUILD]` Add consent-based contact discovery without uploading readable address books.
- [x] `MOB-1407` `[BUILD]` Measure TV-to-mobile, task-recipient and workspace-invitation activation.
- [x] `MOB-1408` `[BUILD]` Add account deletion, portable export and relationship revocation.
- [ ] `MOB-1409` `[VERIFY]` Conduct household, freelancer, employee and Boardroom field pilots.
- [ ] `MOB-1410` `[EXTERNAL]` Complete independent security, privacy, legal and regulatory review.

### Stage 14 closure

- [x] Every invitation has immediate recipient value and an unambiguous sender.
- [x] Blocking, leaving a workspace or revocation stops future agent-to-agent contact.
- [x] Network growth does not require Tessaris to own conversations, private memory or Boardroom data. *(The handoff contract runs mother-to-mother over customer-held keys and returns an encrypted packet for any permitted transport; no Tessaris store is in the data path.)*

---

## Production-wide invariants

- [ ] Private content is encrypted in transit and at rest.
- [ ] Shared television and peripheral nodes never receive mother-private keys or provider tokens.
- [ ] Personal, Household, Workspace and Boardroom are independent policy and encryption domains.
- [ ] A model cannot grant itself identity, capability, recipient, provider or payment authority.
- [ ] External content is untrusted evidence, never executable instruction.
- [ ] Every consequential action follows research/prepare, exact scope, private approval, one
  execution, verification and receipt.
- [ ] Queued, prepared and simulated work is never called sent, booked, paid or completed.
- [ ] AION Native and deterministic routing remain useful without OpenAI or another paid model.
- [ ] GlyphChain stores proofs, not plaintext private life or business data.
- [ ] PHO and the experimental economic layer remain disabled independently of messaging.
- [ ] Radio is optional and never required for ordinary Pilot use.
- [ ] Revocation and expiry propagate to mobile, mother, relay, TV and Workspace Gateway.

---

## Required end-to-end field scenarios

- [ ] Clean mother installation and first phone pairing.
- [ ] Local Wi-Fi to mobile-data roaming and reconnection.
- [ ] Personal Pilot conversation and task creation.
- [ ] Pilot-to-Pilot task with accept, decline, cancel and complete paths.
- [ ] Voice note and PTT after phone sleep and reconnection.
- [ ] Pilot-to-non-Pilot email/message with verified provider state.
- [ ] Household shared list with recipient acceptance and private-list denial.
- [ ] Employer invitation to a restricted employee workspace.
- [ ] Freelancer participating in two unrelated clients.
- [ ] Accountant bounded package review and human sign-off.
- [ ] Boardroom mobile briefing, delegation, correction and approval.
- [ ] Shared-TV takeover, redaction, timeout, logout and lost-phone revocation.
- [ ] Real task/calendar/provider authorization and exact receipt.
- [ ] Mother backup, restore and migration.
- [ ] Failed update and automatic rollback.
- [ ] Optional radio text/PTT with the internet disabled.
- [ ] Complete operation with every PHO/economic feature disabled.

---

## External dependency register

- [ ] `EXT-001` Apple developer account, signing, entitlements and App Store review.
- [ ] `EXT-002` Google Play signing and review.
- [ ] `EXT-003` Native background networking, notifications, microphone and camera permissions.
- [ ] `EXT-004` Official WhatsApp or equivalent business-messaging permission.
- [ ] `EXT-005` Real OAuth accounts for calendar, email, tasks and other service qualification.
- [ ] `EXT-006` Additional households, freelancers, employees and businesses for field trials.
- [ ] `EXT-007` Independent application, cryptographic and infrastructure security assessment.
- [ ] `EXT-008` Privacy, child safety, employment, business and jurisdiction-specific legal review.
- [ ] `EXT-009` Optional radio hardware and regional compliance work.
- [ ] `EXT-010` Separate future financial, custody, regulatory and economic review before PHO activation.

External dependencies remain open and visible. They must never be converted into checkmarks by a
mock, interface demonstration or unsupported product claim.

---

## Immediate build sequence

The original order and present position are:

1. **Stage 0 — implementation complete:** inventory and freeze the reuse boundary; one runtime
   closure receipt remains.
2. **Stage 1 — closed:** canonical contracts and compatibility readers.
3. **Stage 2 — coded implementation complete:** the responsive shell, contextual controller
   grouping and representative responsive viewport qualification pass.
4. **Stage 3 — partially complete:** secure local phone pairing works; remote continuity remains.
5. **Stage 4 — coded implementation complete:** retain the real-phone reconnect qualification as
   an explicit field gate.
6. **Stage 5 — external gate:** `MOB-0514` requires user-authorized live task, calendar and communication provider accounts for real provider qualification; it cannot be honestly closed by mocks.
7. **Stage 6:** coded implementation complete with 499-test regression evidence; retain its real multi-organisation field gate.
8. **Stage 7:** core non-Pilot recipient delivery and official SMS adapter complete; live account
   qualification and officially authorised WhatsApp access remain external.
9. **Stage 8:** core television continuity complete; repository-backed deliberate presentation remains visible.
10. **Stage 9 — complete:** privacy-minimised selective proof rail and lifecycle evidence.
11. **Stage 10:** ownership core complete; installers, remote transport, self-host relay and migration rehearsal remain.
12. **Stage 11:** shared native security boundary complete; signed iOS/Android applications remain external build work.
13. **Stage 12:** call/group policy and adverse-network authority qualification complete; independent
   audit of WebRTC media encryption remains.
14. **Stage 13:** hidden Wave core, legacy framing reuse and hardened serial/bridge boundary complete;
   BLE/Wi-Fi Direct, hardware, compliance and offline field proof remain.
15. **Stage 14:** coded adoption and universal handoff core complete; field/security/legal review remains.

The first coding sprint ends only when Stages 0 and 1 are closed and the Stage 2 shell can render
Personal, Workspace and Boardroom fixtures from the same versioned contracts. The first product
sprint ends when the Stage 4 two-person task journey works end-to-end with PHO disabled.
