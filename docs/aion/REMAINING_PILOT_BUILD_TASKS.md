# Remaining Pilot Build Tasks

Status: Pilot Fabric 0.51.0 — 31 August 2026

This record contains outstanding work only. Completed foundations are omitted.

## Execution status for master sections 1–6

The master numbering remains authoritative. Work must be closed in numerical
order unless a section contains a recorded external dependency that prevents
field completion. A later capability does not make an earlier section complete.

| Number | Current state | Meaning |
| --- | --- | --- |
| **1 — Consumer installation and operations** | **Open — partial foundation** | A developer bootstrap, package builder, local installer/uninstaller commands, QR/Bonjour discovery, TLS bootstrap and recovery foundations exist. The consumer product is not signed, notarized, self-updating or fresh-machine qualified. |
| **2 — Television platforms and multi-room** | **Open — partial foundation** | The LG gateway, discovery, schema-derived capability model, address recovery, room routing and handoff contracts exist. Multi-vendor adapters and multi-device field qualification remain. |
| **3 — Universal navigation and reliability** | **Closed — framework complete** | Observe → act → observe → verify transactions, bounded recovery, route memory, transport receipts and owner-camera verification are implemented and tested. Vendor expansion belongs to Number 2 and production perception belongs to Number 5. |
| **4 — Voice recognition and interaction quality** | **Open — partial foundation** | Local wake routing, sleep/off privacy, quiet mode, local voice selection, push-to-talk, bounded dialogue rejection and cancellation exist. Acoustic echo cancellation, full-duplex barge-in and real-room qualification remain. |
| **5 — Production screen perception** | **Open — partial foundation** | Local OCR, visible Observer Mode, multi-frame fusion, programme-title evidence, public catalogue identity and signed telemetry contracts exist. Native observers, broader content identity and real provider adapters remain. |
| **6 — Live Companion expansion** | **Locally closed — external qualification remains** | Every locally enforceable evidence, privacy, rights and interaction boundary is implemented. Licensed feeds, native overlay/audio authority and real provider qualification remain explicitly blocked and are tracked below. |

### Number 1 closure record — Consumer installation and operations

**Implemented foundation**

- Versioned preview archive and release manifest.
- Non-terminal double-click bootstrap for the developer preview.
- Local install and recoverable uninstall commands.
- Bonjour advertisement, rotating QR/phone code and LAN companion discovery.
- Mother-local TLS material, explicit phone-trust bootstrap and HTTP recovery route.
- Supervisor, address refresh and bounded recovery foundations.
- Existing COMDEX intelligence, memories, credentials and runtime state are excluded
  from the distributable preview.

**Remaining software work**

- Build a graphical first-run installer and guided setup flow.
- Make the distributable independent of an existing COMDEX checkout while retaining
  an optional, explicit governed bridge to a full AION mother brain.
- Implement signed update manifests, staged installation, health verification,
  automatic rollback and update history.
- Add permission guidance for local network, microphone, camera and notifications.
- Add non-technical health checks, one-click repairs and a redacted support bundle.
- Add explicit memory export, selective deletion, mother-identity deletion and secure
  uninstall choices that do not silently erase household data.
- Publish a generated compatibility report and supported-system matrix.

**External or field dependencies**

- Apple Developer identity for production code signing and notarization.
- Production native-phone trust flow to replace manual household-certificate setup.
- Clean-Mac and ordinary-user field tests across supported macOS versions and routers.

**Closure condition**

A non-technical user must install Pilot on a clean supported computer, grant the
required permissions, discover and pair a television and execute the first verified
command in under five minutes, with no terminal use. Update failure must roll back
automatically, diagnostics must expose a repair action, and uninstall/data choices
must be explicit and verified.

### Number 2 closure record — Television platforms and multi-room

**Implemented foundation**

- Real LG webOS discovery, pairing and governed command gateway.
- Capability acquisition, schema classification and least-privilege capsules.
- Television address refresh after DHCP/address changes.
- Persistent room identity, exact room resolution and a private handoff contract.
- Device-specific route memory and universal verified-navigation transactions.
- Restricted-device gateway model for televisions unable to host an AION node.

**Remaining software work**

- Generalize adapter health, latency, firmware-change and capability-change monitoring.
- Implement Samsung Tizen and Google/Android TV adapters against the shared contract.
- Investigate and document enforceable Roku, Fire TV and Apple TV boundaries.
- Add safe HDMI-CEC fallback controls and vendor-supported power control.
- Add multi-room status, destination selection and synchronized-surface coordination.
- Create hardware-independent protocol simulators and conformance suites for television
  models not locally available.

**External or field dependencies**

- Additional LG model years, at least one Samsung television, one Google/Android TV
  device and a second real television for room handoff testing.
- Vendor developer accounts, certificates and permissions for native television apps.
- Provider/device permission for synchronized playback and restricted controls.

**Closure condition**

Every claimed supported platform must pass discovery, pairing, capability change,
address change, restart, command verification and recovery tests. Two real televisions
must pass exact-room routing and verified handoff. Unsupported actions must fail closed
and appear as unsupported rather than silently degrading into guessed navigation.

### Number 3 closure record — Universal navigation and reliability

Number 3 is closed at the reusable framework level. Pilot records the initial device
and surface belief, success criterion, governed action, transport receipt and distinct
post-action evidence. It retries only bounded alternative routes, remembers successful
and failed paths per device and surface, and never treats button delivery as screen
success. Netflix search, profile selection, Home, Back, playback and owner-camera
verification exercised the contract on the available LG television. Cross-vendor
field coverage remains a Number 2 responsibility rather than reopening Number 3.

### Number 4 closure record — Voice recognition and interaction quality

**Implemented foundation**

- Local Pilot wake phrase and deterministic command routing.
- Sleeping and microphone-off states that physically close capture.
- Quiet mode, selectable allowlisted local voices and household quiet hours.
- Bounded television-dialogue rejection and follow-up windows.
- Private-phone hold-to-speak with immediate local audio deletion.
- Emergency cancellation across reversible active plans and navigation transactions.
- Visible listening, hearing, thinking, acting, speaking, completed and error states.

**Remaining software work**

- Implement true full-duplex barge-in while Pilot is speaking.
- Propagate cooperative cancellation through every long-running network and device adapter.
- Add household voice-output preferences without enabling voice biometrics by default.
- Add repeatable false-wake, missed-wake, latency and interruption measurement tools.

**External or field dependencies**

- Platform-native acoustic echo cancellation and microphone/speaker integration.
- Real-room testing across accents, children/adults, distance, background conversation,
  loud television audio and supported microphone hardware.
- Accessibility and privacy qualification with representative users.

**Closure condition**

Pilot must meet recorded false-wake, missed-command and latency thresholds in a real
room; support interruption and cancellation without duplicated actions; reject ordinary
programme dialogue; expose microphone state unambiguously; and preserve a reliable
private phone fallback.

### Number 5 closure record — Production screen perception

**Implemented foundation**

- Owner-initiated local Apple Vision OCR and classification with immediate pixel deletion.
- Visible Observer Mode leases, capture profiles, countdown, pause/resume and Stop.
- Battery/thermal throttling contracts and bounded source-pixel-free structured records.
- Multi-frame surface stability, context-transition isolation and duplicate rejection.
- Subtitle, scoreboard, product, game and scene evidence fusion.
- Repeated OCR programme identity and strict public TVmaze catalogue matching.
- Signed, persona/provider/scope-bound playback and entitlement telemetry contract.

**Remaining software work**

- Add measured bandwidth adaptation and platform-native lifecycle handling.
- Expand identity from television series into films, exact episodes, advertisements
  and live events with honest ambiguity handling.
- Implement permitted caption/subtitle adapter interfaces.
- Connect real signed-in provider metadata, playback-position and entitlement adapters.
- Complete privacy, child-safety and protected-content threat models and review records.

**External or field dependencies**

- Signed native iPhone and Android observer applications for production camera capture.
- Mobile operating-system permission for visible capture through sleep/suspension where allowed.
- Provider-authorized metadata, caption, playback and entitlement interfaces.
- Real iPhone and Android battery, thermal, bandwidth and background-lifecycle tests.

**Closure condition**

The signed native observers must preserve a continuous visible consent indicator,
recover safely from suspension and network changes and meet measured resource limits.
Programme, episode and live-event identity must carry provenance and confidence. Provider
playback and entitlement claims must originate only from authorized signed adapters.

### Number 6 closure record — Live Companion expansion

**Implemented foundation**

- Explicit live-context capture that preserves television playback.
- Evidence-bounded spoiler-safe scene explanation.
- Local subtitle/dialogue translation with deterministic fallback.
- Captured-scoreboard interpretation and deterministic sports-rule explanation.
- Authenticated football/live-event connector boundaries and source reconciliation.
- Live-news fact checking with claims, source quality, contradictions and corrections.
- Evidence-backed programme main-cast and exact character-to-actor lookup.
- Explicit refusal to identify a visible actor or use face recognition.
- Private evidence display and rights-safe Moment preparation foundations.
- Strict exact-current-cast person matching and broader verified programme credits.
- Joke, reference and cultural-context explanation with selectable child, simple,
  normal and detailed modes.
- Descriptive accessibility summaries and age-appropriate science, history and
  language activities derived only from permitted observed evidence.
- Strict Wikidata-backed filming-location, narrative-location and original-source lookup.
- Bounded ingredients, techniques and object labels without inventing product identity.
- Advertising and product-claim fact-check routing through the same source-labelled engine.
- Authenticated goal, booking, substitution and supplied-lineup timelines.
- Explicit-range historical team statistics with ambiguous-team rejection.
- Private identity-bound close-event thresholds, local notification inbox, opt-in
  household predictions and commentary preferences with betting disabled.
- Repeatable fixed-case public fact-check benchmark measuring verdict match, HTTPS
  evidence coverage, latency and provider failures outside the model.
- Verified local private-phone delivery of signed fact-check Moments.
- Fail-closed authority gates for synchronized subtitles, native overlays, local dubbing,
  audio processing and official provider highlight routes.

**Remaining field/provider qualification**

- Qualify episode-level guest-cast and richer player-performance statistics against
  licensed provider feeds; current responses expose only the evidence actually supplied.
- Connect and qualify at least one authenticated election feed and additional awards,
  concert, fantasy and sports providers. Ticketmaster event discovery and football-data
  contracts exist, but absent credentials cannot be represented as live coverage.
- Field-run the public fact-check benchmark in air-gapped, public-evidence and optional
  provider modes and publish measured thresholds; the repeatable harness and cases exist.
- Field-test household commentary, predictions and threshold notifications with multiple
  private identities. External push remains disabled until a signed phone adapter exists.

**Platform, provider or rights dependencies**

- Synchronized subtitle projection and compact native-TV overlays require explicit
  television-platform authority.
- Local dubbing requires both content rights and a permitted audio route.
- Dialogue enhancement/background reduction requires supported hardware or authorized
  audio processing.
- Goals/highlights require authorized event feeds and provider-native clips.
- Elections, awards, concerts and richer player timelines require authenticated sources.

**Closure condition**

Every Live Companion answer must distinguish observed evidence, provider facts and Pilot
interpretation; preserve playback; expose uncertainty; and avoid face guessing, spoilers,
protected-media copying and unsupported overlays. Locally buildable items must pass the
full automated suite, while provider/platform-dependent items require explicit field
evidence before they can be marked complete.

## Strict next-action rule

Per the owner's current product sequence, God View is deferred. **Numbers 15 and 16
are locally closed at their governed adapter boundaries in 0.51.0.** Number 24 now
has its first safe local proof, but remains open for external safety qualification.
Numbers 13 and 14 are locally closed in 0.47.0;
their native-platform and authorized-provider field qualifications remain recorded in
`PILOT_SECTIONS_13_14_BLOCKER_REGISTER.md`.
Numbers 1, 2, 4 and 5 remain on the return register. Number 3 is closed.
Numbers 6, 6A, 7 and 8 are locally closed; their external provider/platform and field
qualification remains visible and cannot be silently relabelled as field-complete.

## Phase 1 — Finish the AI television product

### 1. Consumer installation and operations

- Produce a signed, notarized consumer installer with no terminal interaction.
- Package Pilot independently of an existing COMDEX installation while preserving
  an optional governed bridge to a full AION/COMDEX mother brain.
- Add automatic signed updates with rollback after a failed update.
- Complete guided network permissions, television discovery, pairing and phone trust.
- Replace manual iPhone certificate installation with a signed native companion or
  another production-grade trust flow.
- Harden recovery after television, router, computer, address and credential changes.
- Add non-technical diagnostics, repair actions and support bundles with secrets removed.
- Complete secure uninstall, mother-identity deletion, memory export and selective deletion.
- Publish the supported hardware, operating-system, television and network matrix.
- Achieve installation-to-first-command in under five minutes through field testing.

### 2. Television platforms and multi-room field support

- Field-test discovery, pairing, reconnection and capability changes across multiple
  LG webOS models and model years.
- Build a signed native LG webOS application where LG grants the required scopes.
- Build Samsung Tizen support.
- Build Google TV and Android TV support.
- Investigate Roku, Fire TV and Apple TV gateway boundaries.
- Add HDMI-CEC fallback controls for safe common actions.
- Add safe, permissioned power control where a supported vendor route exists.
- Generalize dynamic capability detection and schema resolution across vendors.
- Monitor adapter health, latency, firmware changes and vendor API changes.
- Field-test exact room routing and verified handoff with at least two real televisions.
- Add verified synchronized surfaces where providers and devices permit them.

### 4. Voice recognition and interaction quality

- Field-tune wake recognition across supported accents, distances and room acoustics.
- Add platform-native acoustic echo cancellation and qualify it against television audio.
- Complete full-duplex barge-in while speech is playing and propagate cooperative
  cancellation into every long-running external device adapter.
- Add household voice preference profiles without enabling voice biometrics by default.
- Run the real-room accessibility, false-wake, missed-command and privacy matrix.

### 5. Production screen perception

- Ship a signed native iPhone and Android observer for production camera capture.
- Support continuous visible Observer Mode through phone sleep and application suspension.
- Qualify the implemented capture profiles, visible indicator, countdown, pause/resume
  controls and adaptive battery/thermal policy on real iPhone and Android hardware.
- Add measured bandwidth adaptation and platform-native background-execution handling.
- Extend the implemented repeated-OCR and exact public-catalogue programme
  identity to films, episodes, advertisements and live events.
- Ingest provider captions and subtitles only through permitted interfaces.
- Connect signed-in provider metadata adapters and expand the public programme
  guide beyond TV series.
- Extend signed playback-position and entitlement telemetry to real provider adapters.
- Complete production privacy, child-safety and protected-content review.

### 6. Live Companion expansion

The locally buildable Section 6 scope is complete in 0.43.0. The exact unresolved
provider, platform, rights and field dependencies are maintained in
`PILOT_SECTION_6_BLOCKER_REGISTER.md`; they remain release claims that Pilot must not
make until the listed evidence exists.

### 6A. Contextual companion and wellbeing

The locally enforceable Section 6A scope is complete in 0.44.0. It includes private
opt-in profiles, frequency and quiet-time gates, approved interests/topics, advert and
programme activities, transparent loneliness support, a Guardian escalation boundary,
large phone controls, trusted-call preparation and persona-bound TV/phone/car handoff
contracts. Real call placement, car execution, multi-person field qualification and
wellbeing safety review remain in `PILOT_SECTION_6A_BLOCKER_REGISTER.md`.

### 7. Entertainment intelligence

The locally enforceable Section 7 scope is complete in 0.45.0. It includes strict official
provider routes, private confirmation, signed playback/entitlement reconciliation,
persona-private continuation, private/shared watchlists, identity-claimed viewing history,
deterministic contextual recommendations, exact-metadata local episode reminders,
service-health recovery and existing room/Moment handoff contracts. Real provider account
adapters, native push and per-service field qualification remain in
`PILOT_SECTION_7_BLOCKER_REGISTER.md`.

### 8. Games and learning polish

The locally enforceable Section 8 scope is complete in 0.46.0. It includes a staged
gaming evidence model, provider-owned sign-in boundary, Gamepad API controller profiling,
input-event qualification, persona-private verified-title shortcuts, honest continuation,
expanded adaptive Spanish, local mathematics and science, original vector illustrations,
transcript-free local pronunciation scoring and guardian-private progress/corrections.
Provider telemetry, game-specific deep links, controller hardware qualification and
independent pedagogy, accessibility and child-safety review remain in
`PILOT_SECTION_8_BLOCKER_REGISTER.md`.

### 9. God View completion

- Add an optional owner-supplied photorealistic 3D map provider.
- Build a provenance-labelled public-camera catalogue with calibrated view projection.
- Add earthquake, wildfire, vessel, traffic and selected live-event layers.
- Carry natural place, flight and layer parameters directly from speech into the
  already-open God View session.
- Add verified flight search, route tracking and aircraft detail panels.
- Improve restricted-TV rendering, gamepad navigation and graceful stream fallback.

## Phase 2 — Finish Moments and provider-native sharing

### 10. Remaining Moment lifecycle work

- Add explicit forwarding permissions and recipient-specific opening access.
- Add verified opening receipts separately from creation and delivery receipts.
- Connect at least one real authorized delivery adapter.
- Add sender-approved reaction text without copying protected programme media.
- Complete recipient-side expiry, revoke, delete and abuse behavior in field tests.

### 11. Provider-native sharing

- Build a YouTube timestamp-sharing adapter.
- Add Netflix Moments handoff only where officially supported.
- Build a Twitch native clip adapter.
- Add authorized live-event clipping adapters.
- Create a copyright-safe Pilot Moment Card and official watch-link resolver.
- Add “open at this moment” where the provider supports timestamps.
- Support export only for user-owned or licensed media.
- Record why each sharing method was selected.
- Explicitly refuse unauthorized recording or protected-stream extraction.

### 12. Viral television flow

- Connect “clip that” and “share the last thirty seconds” to provider-native or
  rights-safe artifacts rather than raw protected capture.
- Resolve ambiguous recipients on the private phone.
- Deliver useful expiring web Moments to non-users.
- Add “Watch on TV with Pilot” continuation from a received artifact.
- Preserve the incoming Moment through optional onboarding.
- Attribute activation without exposing sender or recipient viewing history.
- Add “send this product/restaurant/destination/explanation to my friend” from live context.
- Add family voting, watch invitations and shared programme quizzes as rights-safe artifacts.
- Let an existing Pilot recipient open a Moment directly on their chosen television.
- Let a non-user receive value, respond and decline before seeing an optional installation prompt.
- Measure the complete Screen → Understanding → Action → Person funnel.

## Phase 3 — Reveal the personal Pilot

### 13. Production private identity

**Locally closed in 0.47.0.** Pilot now provides explicit adult and guardian-controlled
child onboarding, one-time recovery material, Ed25519 phone-possession binding,
replay-protected time-bounded shared-screen activation, a clear active-person indicator,
lost-device revocation, account recovery, private/household memory scopes, correction,
export and selective deletion, and service consents containing exact visible scopes.

**Remaining external qualification:** native iOS/Android signing, hardware-backed key
attestation and biometric authorization must be implemented and field-qualified before
Pilot describes an approval as biometric. Consumer recovery and child-profile policy also
require native notification and product/privacy qualification.

### 14. Tasks, lists and reminders

**Locally closed in 0.47.0.** Pilot now provides persona-private and household lists,
completion and snooze state, direct Pilot inbox messages, recipient-accepted task
delegation, time/arrival/departure/journey/closing-time reminders, repetition rules,
explicit location-permission receipts, TV-context source references, phone and authorized-car
continuation contracts, route-stop suggestions that cannot silently alter a route, and
privacy-safe shared-TV summaries. Spoken commands can read counts, add a self-task,
delegate an exact task or send an agent message once a signed identity is active.

A Google Tasks adapter uses the official task insertion endpoint and requires a
persona-bound provider credential plus a verified provider response. Cross-person list
modification is rejected. Email, WhatsApp and SMS handoffs for non-users remain
`prepared_not_sent` until Number 15 supplies an authorized adapter, exact private approval
and delivery receipt.

**Remaining external qualification:** authorize a real Google account and record a live
provider receipt; qualify native background notifications/geofences; and connect a real
car platform before route continuation can be called field-complete.

### 15. Communication

**Locally closed at the governed adapter boundary in 0.51.0.** AION Native drafting,
exact contact/content approval, verified delivery receipts, received-message provenance,
task/calendar conversion, child guardian gates, call preparation and no-reply follow-up
state are implemented. The private phone now exposes the communication workflow.

**External qualification still required:** register and verify production Google OAuth;
connect a real persona-authorized Gmail account; qualify an official WhatsApp Business
or equivalent messaging route; ship native authorized call placement; connect inbox push
or polling; and field-test child/teen safeguarding. Consumer WhatsApp session automation
or contact scraping is not an acceptable substitute.

- Connect authorized email and messaging accounts.
- Draft messages and email replies through AION Native first.
- Resolve contacts privately and show exact recipient and content before sending.
- Require private approval and verify delivery with provider receipts.
- Summarize received messages with sender and freshness provenance.
- Convert messages into tasks and calendar proposals.
- Add child and teenager communication protections.
- Add authorized WhatsApp or equivalent handoff where the platform officially permits it.
- Add call preparation and explicit call placement through an authorized phone surface.
- Add sender-requested follow-up such as “remind me if they have not replied tomorrow.”

### 16. Calendar and planning

**Locally closed at the governed adapter boundary in 0.51.0.** Create, reschedule and
cancel are separate scope-hashed approvals; private conflict detection, travel and reminder
parameters, detail-free availability, normalized receipts, PKCE state validation and opaque
vault references are implemented. Google insert, reschedule and delete adapters require
verified provider outcomes.

**External qualification still required:** create the production Google Cloud clients,
complete consent-screen and sensitive-scope review where applicable, provide an authorized
token vault, connect real persona calendars, exercise free/busy against real accounts, and
field-test time zones, recurring events, invitations and provider reconciliation.

- Complete persona-specific Google OAuth and connect real calendars.
- Execute event creation after private approval and verify the provider receipt.
- Reschedule and cancel events through new exact approvals.
- Add travel time, reminders and conflict detection.
- Query availability without exposing private event details.
- Retain normalized modification receipts without provider secrets.

### 17. Shopping, booking and procurement

- Compare price, suitability, delivery, returns and evidence freshness.
- Identify sponsored, affiliate and uncertain information.
- Connect authorized basket adapters.
- Add biometric private payment confirmation without storing raw card data.
- Verify orders, delivery changes and cancellations.
- Execute travel, restaurant, appointment and household-service bookings.
- Store receipts and warranties under the correct persona.
- Add disputes, refunds and failed-execution recovery.
- Add bill review and payment preparation with biometric confirmation and verified receipt.
- Add delivery rescheduling and provider-confirmed outcome verification.
- Send evidence-labelled product shortlists to a chosen private phone, television or contact.

### 17A. Unified Life Concierge and connected-home control

- Build one cross-service action engine rather than separate calendar, shopping and messaging demos.
- Preserve the universal workflow: research → prepare exact scope → private review →
  approve → execute once → verify outcome → receipt.
- Add a personal action inbox showing waiting questions, approvals, failures and completed outcomes.
- Support multi-step requests spanning maps, contacts, messages, calendars, shopping and devices.
- Resume long-running objectives across restart, television, phone and car without duplicating actions.
- Add explicit correction, cancellation, rollback and recovery for every multi-service plan.
- Route private details to the correct persona even when the request begins on a shared television.
- Add maps, navigation, local-business research and route-stop preparation as first-class adapters.
- Add service health, quota, authentication and degraded-mode status to every plan.
- Add a connected-home control centre for enrolled lights, climate, audio, entry and other devices.
- Require schema-derived capabilities and least-privilege leases for every home control.
- Add household scenes and automations with visible ownership, schedules and emergency overrides.
- Never let a language-model plan itself constitute authority to pay, send, unlock, book or purchase.

## Phase 4 — Activate the Pilot network

### 18. Pilot Contacts

- Add contacts manually, by QR or secure invitation link.
- Offer phone-contact selection only with explicit permission and minimum disclosure.
- Verify recipient identities and support private aliases.
- Add per-contact permissions, block, mute, remove and capability revocation.
- Prevent unsolicited mass invitations.
- Add abuse reporting and rate limits.

### 19. Pilot Relay

- Define signed typed envelopes for tasks, recommendations, Moments, reminders,
  events, invitations, products, documents and decisions.
- Require recipient evaluation and acceptance before creating local obligations.
- Add expiry, replay protection and completion acknowledgements.
- Hide recipient location and private state from senders.
- Maintain independent sender and recipient audit receipts.
- Support payment requests, emergency alerts, introductions and shared-plan proposals as
  distinct high-trust envelope types with stricter policies.
- Let the recipient convert an accepted proposal into a reminder, task, calendar proposal,
  route stop or private message without exposing their private context to the sender.
- Add recipient policies such as always allow reminders from a contact, never disclose
  location, ask before calendar changes and permit emergency interruption.
- Return only recipient-approved completion acknowledgement, never hidden location,
  calendar, messages or activity state.
- Add transparent age-appropriate guardian policies and a visible child sharing record.

### 20. Value-first invitation flow

- Deliver a useful temporary artifact before installation.
- Allow acceptance or rejection without registration.
- Preserve the item through optional onboarding and continue from it after activation.
- Explain the additional value of installing Pilot without dark patterns.
- Measure value delivered and recipient activation without contact scraping or surveillance.
- Make a sender-created useful task, Moment, shortlist or invitation the recipient’s first experience.
- Allow non-users to accept into the phone’s native reminders/calendar where possible
  without requiring Pilot installation.
- Continue directly from the accepted artifact if the recipient later activates Pilot.
- Test the core adoption message: “Add Pilot to the television you already own.”
- Keep “personal autonomous agent” out of first-run positioning; reveal personal agency through use.

### 20A. Adoption funnel and product proof

- Measure hook activation, first delight, first private action, first useful share,
  recipient value, recipient activation and thirty-day retained use.
- Test whether live intelligence creates conversation, Moment sharing creates acquisition,
  Actions creates daily retention and Relay creates network growth.
- Attribute growth to useful artifacts rather than forced invitations, contact harvesting or dark patterns.
- Field-validate that the single-user product remains valuable before network effects exist.

### 21. Pilot Circles

- Add household, friends, trip, school, care and work circles.
- Add temporary event circles.
- Define per-circle data, capability and notification policies.
- Extract accepted tasks, decisions and unresolved questions.
- Add independent leave and mute controls.
- Avoid recreating an unfiltered group-chat stream.
- Support shared chores, shopping, deliveries and emergencies in Household circles.
- Support research, voting, bookings, payments and updates in Trip circles.
- Support collections, events, homework and permission requests in School circles.
- Support medication reminders, appointments, check-ins and escalation in Care circles.
- Support documents, decisions, responsibilities and follow-ups in Work circles.

## Phase 5 — Pilot Everywhere

### 22. Native phone continuity

- Ship native-quality iPhone and Android applications.
- Add persistent secure pairing and signed device identity.
- Add background reminders, push notifications and expiring offline queues.
- Add private approvals, task continuation and production camera perception.
- Add phone voice interaction, Moment receiving and Relay controls.
- Add device-loss revocation and recovery.

### 23. Car continuity

- Complete CarPlay and Android Auto feasibility and platform review.
- Build a car-safe conversational interface.
- Add navigation, route-stop and audio continuation.
- Add location-triggered reminders, message/call preparation and to-do capture.
- Block complex approvals while moving and enforce driver-distraction limits.
- Maintain a reliable phone fallback when the car integration is unavailable.
- Carry the same persona, objective, memory and permissions from the home rather than
  creating a separate car assistant.
- Add safe petrol, charger, parking and other route-stop discovery with live availability provenance.
- Add “read important messages,” reply preparation and trusted-contact calling within platform restrictions.
- Continue permitted podcasts, music and spoken briefings from another Pilot surface.

## Phase 6 — High-trust expansion

### 24. Pilot Guardian

**First safe local proof implemented in 0.51.0; not safety- or field-complete.** Explicit
help speech, large phone confirmation, false-alarm cancellation, separately authorized
emergency contacts, optional consented location, verified alert receipts, connectivity
fallback, two-way response records and non-diagnostic wearable/sensor signals are built.

**External safety blockers:** no emergency-service dispatch adapter is connected; no
ambulance claim is permitted. Regional emergency integration, clinical and legal review,
telecom and safeguarding review, resilient notification/SMS/voice providers, native
background operation, power/network fallback, accessibility trials, continuous path
monitoring, false-positive studies, and authorized entry/light coordination remain.

- Design emergency-help and fall-response flows with trusted-contact escalation.
- Build large emergency TV and phone interfaces and two-way communication.
- Define explicit location-sharing and authorized entry/light coordination.
- Add connectivity fallback, continuous path monitoring and false-positive handling.
- Research regional emergency-service integration.
- Complete regulatory, clinical, legal and safety review.
- Never claim ambulance dispatch until a tested authorized route verifies it.
- Build the first safe proof: spoken fall/help request → large confirmation surface →
  urgent trusted-contact alert and authorized location → live response page.
- Add optional authorized wearable and room-sensor signals without claiming medical diagnosis.
- Define emergency interruption permissions separately from ordinary contact permissions.

### 25. Pilot Work and Boardroom

- Build the shared research wall, company briefing and document-review experience.
- Add meeting preparation, operational dashboards and scenario planning.
- Extract decisions and proposed actions with explicit human ownership.
- Add multi-person private identity and work-service adapters.
- Add enterprise permissions, retention and audit controls.
- Enforce strict household/company memory separation.
