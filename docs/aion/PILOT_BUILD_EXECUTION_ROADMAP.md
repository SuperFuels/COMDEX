# Pilot Build Execution Roadmap

Status date: 30 August 2026  
Current Fabric release: 0.42.0

## Evidence-backed programme cast companion — implemented in 0.42.0

- “Who is in this?” and “show me the cast” use the stable programme identity
  and a bounded TVmaze main-cast record rather than model memory.
- “Who plays [character]?” requires an exact normalized character match.
- “Who is that actor?” explicitly refuses visible-person identification and
  provides the verified programme cast as a safe alternative.
- Face recognition, face embedding, biometric identity and scene-presence claims
  are not used.
- Cast evidence is cached for twenty-four hours, capped at fifty programme records,
  attributed and shown privately while playback remains untouched.
- 314 automated Fabric tests pass. Filming locations, original sources and
  broader person-credit exploration remain open.

## Programme identity and public catalogue evidence — implemented in 0.41.0

- Media-screen OCR produces bounded title candidates, but one frame cannot
  establish a programme identity.
- Repeated title agreement can trigger a bounded TVmaze public-catalogue query;
  only one normalized exact match is accepted as catalogue evidence.
- Ambiguous and approximate matches fail closed and remain visible as uncertainty.
- Signed provider telemetry, official provider metadata, public catalogue identity
  and repeated OCR are retained as different evidence classes.
- A catalogue match never claims current playback, regional availability,
  subscription entitlement or household access.
- Queries are cached for twenty-four hours, capped at one hundred records and
  contain no source pixels, audio, account identifier or credential.
- 310 automated Fabric tests pass. Signed-in provider adapters and broader film,
  episode, advertisement and live-event guides remain open.

## Resource-governed production perception — implemented in 0.40.0; native clients open

- Visible Observer Mode offers Detail, Balanced and Battery Saver capture
  profiles plus explicit two-, five- and ten-minute leases.
- The mother independently enforces effective frame intervals and bounded image
  dimensions rather than trusting browser timing.
- Low battery and elevated thermal state throttle capture; critical battery,
  critical thermal state or a hidden browser page pause it and reject frames.
- Pause, visible Resume and Stop controls close camera tracks immediately. Stop
  creates a content-free session receipt with frame count and no retained pixels.
- Two consecutive observations on a new application/input establish a fresh
  context window; previous programme/title evidence cannot leak across surfaces.
- 305 automated Fabric tests pass. Signed native iPhone and Android observers,
  OS background execution and real-device thermal/battery qualification remain.

## Governed voice interaction — implemented in 0.39.0; room qualification open

- “Pilot, cancel” stops active agent, conversation, autopilot and verified
  navigation state and cancels every reversible pending service proposal.
- Uncertain external actions are never falsely claimed cancelled and remain
  marked for reconciliation.
- The wake phrase must begin the utterance after an optional short greeting,
  reducing activation from programme dialogue that merely mentions Pilot.
- Owner-selected local voices and overnight quiet-hour schedules persist only on
  the mother brain.
- The trusted HTTPS phone controller provides explicit hold-to-speak. Bounded
  audio is transcribed locally, deleted immediately and routed through the
  private-persona channel.
- 301 automated Fabric tests pass. Accent, distance, television-echo,
  accessibility and full-duplex barge-in field qualification remain open.

## Multi-room television routing foundation — implemented in 0.37.0

- Enrolled television nodes map to unique mother-local household room names.
- “This TV”, exact named rooms and one explicit default resolve deterministically;
  missing or ambiguous targets fail closed.
- The private controller names the current TV and exposes available destinations.
- Cross-room handoff requires signed persona-bound title and active-playback facts.
- The private phone confirms an immutable handoff hash; confirmation does not
  claim destination playback.
- Credentials never enter room records, handoffs or audit entries; replay and
  cross-persona confirmation are rejected.
- A destination provider adapter must still open and verify playback. Multi-TV
  field testing and synchronized surfaces remain once a second TV is enrolled.

## Voice lifecycle and household quiet mode — implemented in 0.36.0

- The local voice node exposes listening, hearing, thinking, acting, speaking,
  completed, error, sleeping and off as distinct visible states.
- A bounded privacy history records timestamps and outcome classes but contains
  no transcript text and no audio.
- Quiet mode suppresses speech without disabling governed actions or visible
  results, and can be reversed from the trusted local dashboard.
- Local voice selection is allowlisted, speech rate is bounded, and preferences
  persist only in the mother runtime.
- Sleeping still closes the microphone and clears the ephemeral audio ring; it
  cannot falsely listen for a wake word while the capture device is closed.
- This advances the master-roadmap voice-quality and privacy section. True
  concurrent barge-in and platform-native acoustic echo cancellation remain.

## Production fact-check evidence record — implemented in 0.35.0

- Every live-news check is frozen as a versioned, content-hashed evidence record.
- Claims retain their own verdict, confidence, source indexes and date scope.
- HTTPS sources receive an outside-model class, quality score and human-readable
  quality rationale; the model cannot promote its own sources.
- Normalized claim comparison records conflicting verdicts and disputed claims.
- Research latency, source count and mean source quality are measured explicitly.
- “Show me the evidence”, “who disagrees?” and “explain the difference” are
  deterministic follow-ups over the frozen record and never invent opposition.
- The private phone exposes source quality, contradictions, latency and correction
  history while television playback remains visible.
- This advances master-roadmap Live Companion fact-checking. Native third-party
  programme overlays remain unavailable through the LG gateway.

## Signed provider playback telemetry — implemented in 0.33.0

- Native applications, account adapters and capable device nodes can register a
  locally approved Ed25519 telemetry identity for one provider and persona.
- Metadata, playback and entitlement are separate least-privilege scopes.
- Every signed packet has a bounded timestamp and one-use nonce; stale, future,
  replayed, forged and cross-persona packets fail closed.
- Fabric retains only normalized programme identifiers, title, playback state,
  position, duration and separately verified entitlement status.
- Raw provider responses, account identifiers, tokens and public-key material are
  excluded from phone snapshots and audit records.
- An HTTPS-only ingestion route feeds the private controller, exact entertainment
  execution reconciliation and multi-frame screen timeline.
- Signed playback position overrides OCR position while retaining explicit source
  provenance; unsigned screen evidence remains useful when no adapter exists.
- This completes the provider-independent trust and fusion boundary. Restricted
  providers still need an owner-authorized native or account adapter before live
  telemetry can be received; Fabric does not scrape credentials or fabricate it.

## Trusted private-phone HTTPS — implemented in 0.32.0

- The mother generates its own household CA and LAN leaf certificate using the
  bundled cryptography library rather than an external command or cloud service.
- Private keys are owner-only and mother-local; only the public CA is offered for
  deliberate phone installation.
- Leaf certificates cover the active LAN IP, mother hostname and localhost and
  rotate on address change without rotating the trusted household root.
- Port 8769 serves the token/CSRF controller over TLS 1.2+ with HSTS; port 8767
  remains the bootstrap and recovery controller.
- The laptop and onboarding page display the CA SHA-256 fingerprint for explicit
  comparison before trust is enabled.
- Pairing-code success redirects into HTTPS, enabling browser camera APIs after
  the owner completes platform trust.
- Pilot cannot silently install a root or enable trust. Unsupervised Apple devices
  require manual profile installation and full-trust activation.
- This advances original master-roadmap items 3 and 10. A signed native companion
  remains preferable for seamless consumer onboarding and background operation.

## Multi-frame production-perception foundation — implemented in 0.31.0

- Manual and explicit Observer Mode frames feed one bounded structured timeline.
- A single frame cannot establish a stable surface or programme title.
- Surface stability requires at least two frames and two-thirds recent agreement.
- Programme stability requires repeated provider-title support; official metadata
  verification remains separately labelled.
- Duplicate image hashes are ignored and only twelve structured frame records are
  retained; source pixels and raw audio are never retained.
- Subtitle changes, scene change and OCR playback position are exposed without
  falsely claiming protected provider telemetry.
- An observer frame lease survives same-tab phone suspension, while the user must
  visibly press **Resume after phone sleep** to restore camera capture.
- This advances original master-roadmap item 10. Trusted TLS/native mobile capture,
  background continuity and authenticated signed-in provider metadata remain.

## Universal verified navigation core — implemented in 0.30.0

- Phone navigation, media and app operations enter a persistent
  observe--act--observe--verify transaction.
- Every transaction binds the TV, current surface, goal, expected result,
  ordered route, before evidence and after evidence.
- A signed transport receipt proves delivery, not the visible screen outcome.
- Device-state criteria can verify without pixels; visual criteria wait for a
  structured manual capture or explicit Observer Mode frame.
- Failed checks select only a predeclared bounded recovery route and stop after
  three attempts.
- Success/failure memory is isolated by television, surface, goal and route, so
  proven routes rank ahead of failed ones later.
- The private phone exposes live state, expectation, attempt count, capture need
  and a user-triggered recovery button.
- This advances original master-roadmap item 9. Production continuous perception,
  richer safe route libraries and autonomous multi-step recovery remain next.

## Verified entertainment execution — implemented in 0.29.0

- Exact official Netflix, YouTube, Prime Video and Disney+ routes can be
  prepared from cross-service evidence on the private phone.
- Search pages, aggregators, unsafe URLs and ambiguous provider pages cannot be
  treated as executable title routes.
- Every route is persona-bound and requires an exact private confirmation.
- Subscription entitlement remains unknown until the signed-in provider itself
  or an authorized account adapter confirms it.
- Opening a provider and playing a title are separate receipt states.
- Playback is reported only with explicit title plus active-playing evidence.
- “Continue watching” uses only the same persona's last verified provider route
  and creates a new confirmation instead of silently resuming shared-TV history.
- This advances original master-roadmap item 8. Provider account adapters,
  entitlement checks, playback-position telemetry, household watchlists and
  verified cross-provider playback remain pending.

## Governed saved-item follow-through — implemented in 0.28.0

- Persona-owned programme saves can launch private category-specific research.
- Only HTTPS evidence links and bounded summaries enter the follow-through record.
- Local shortlist, task and learning drafts have no external effect.
- Product, destination and music saves can prepare fresh shopping, booking and
  music proposals with exact service scopes.
- The original save grants no execution authority; proposals require a separate
  private-phone decision.
- Missing trip dates are collected privately before approval unlocks.
- Approval stops at `approved_pending_adapter`; only an authorized persona adapter
  plus a verified receipt may later claim external execution.
- Cross-persona continuation, approval and proposal refresh are rejected.
- This advances original master-roadmap items 14 and 17 while preserving the
  Phase 1 television-to-private adoption path.

## Live Event Intelligence — implemented in 0.27.0

- Authenticated football score, goal-event and fixture adapter using an
  owner-supplied mother-local football-data.org token.
- Authenticated concert and event discovery adapter using an owner-supplied
  mother-local Ticketmaster key.
- Deterministic matching between provider fixtures and teams captured from the
  current television scoreboard.
- Provider facts, owner-captured screen evidence, and Pilot interpretation remain
  separate in the data contract and private phone interface.
- Conflicting scores are retained as an explicit conflict rather than merged.
- Scorer identity is reported only when supplied by the authenticated feed.
- Fixed HTTPS hosts, bounded responses, timeouts, result limits and no retained
  raw provider response.
- Provider keys remain on the mother brain and never enter the TV, phone, status,
  result URL, or audit ledger.
- Screen-only operation remains useful and honestly labels the missing live feed.
- This advances original master-roadmap items 5 and 6. Full multi-provider player
  statistics, election results, live award outcomes, alternate commentary and
  background notifications remain pending.

## Programme-to-private saving — implemented in 0.26.0

- “Save this product/recipe/destination/song/idea” prepares a bounded evidence
  card without interrupting the current programme.
- Shared-TV voice can prepare evidence but cannot choose the receiving household
  identity or write into a person's private memory.
- The current private phone must explicitly press **Save to my Pilot** within a
  thirty-minute claim window.
- Product, location, subtitle, recent-dialogue and official-provider evidence is
  confidence-labelled and hashed; raw programme pixels and audio are excluded.
- Saved collections are persona-isolated. A different identity cannot view,
  claim after binding, or delete another person's items.
- Preparation and saving never purchases, messages, books, or creates a calendar
  action; those remain separate governed service flows.

## Evidence-bounded Live Sports — implemented in 0.25.0

- Captured scoreboard and match-clock reading with structured teams and scores.
- “Who is winning?” based only on the latest owner-captured scoreboard.
- Deterministic explanations for football offside, handball, penalties, fouls,
  cards and VAR; basketball travelling/contact; and tennis tie-breaks.
- Commentary and subtitle cues remain explicitly observed evidence; a rule
  explanation remains inference.
- No unseen player identification and no unsupported claim that a referee was
  correct or incorrect.
- Spoken summary and private evidence panel preserve match playback.

## Local Live Translation — implemented in 0.24.0

- Dialogue and captured-subtitle translation into English, Spanish, French,
  German, Italian, or Portuguese.
- Bounded local evidence only; no plot lookup, web search, or paid AI route.
- Local Gemma translation plus a deterministic offline phrasebook fallback.
- Numbers and URLs must survive an outside-model validation step.
- Language-aware installed macOS voices speak the short translation.
- Confidence, uncertainty, source evidence, target language, and hashes remain
  visible on the private phone while television playback continues.

## Spoiler-aware Live Companion — implemented in 0.23.0

- “What just happened?”, dialogue clarification, and scene explanation intents.
- Observed-evidence-only boundary using recent local dialogue, captured subtitles,
  screen observations, and owner corrections.
- No internet plot search, programme synopsis, unseen character knowledge, ending,
  or future-event evidence is supplied to the explanation model.
- Deterministic future-event leakage rejection outside the local model.
- Honest insufficient-evidence response and private confidence/uncertainty display.
- Spoken response preserves playback; the Canvas no longer replaces the programme.

## Private Pilot Moment sharing — implemented in 0.22.0

- A completed fact-check can be bound to a signed, rights-aware Moment.
- Statement, verdict, confidence, sources, and evidence hash are frozen together.
- Recipient selection is private-phone-only and persona-bound.
- The exact preview requires a separate Send confirmation; changes invalidate it.
- Delivery is adapter-gated and can never claim success without a verified receipt.
- Twenty-four-hour expiry, replay protection, three-attempt rate limiting, revoke,
  delete, and privacy-preserving audit receipts are enforced.
- Protected programme pixels and audio are never copied.

## Consumer reliability foundation — implemented in 0.21.0

- Persistent private phone and TV Canvas connections across restarts.
- Automatic paired-TV address recovery and plain-language connection health.
- One-click macOS installation, start-at-login, and crash restart.
- Recoverable uninstall that does not silently erase household data.
- Live LG verification plus 176 passing Fabric checks.

This roadmap fixes the product order: win adoption through a remarkable
AI-television experience first; then expand the already-installed intelligence
into private personal agency and a contact-driven network.

## Pilot God View — implemented in 0.20.0

- [x] God View launch control beside Ask Pilot on the dashboard and TV home.
- [x] Signed television capability route; the feature does not bypass Fabric.
- [x] Token-protected full-screen CesiumJS planet with keyless OpenStreetMap imagery.
- [x] Bounded mother-brain geocoding through OpenStreetMap Nominatim.
- [x] Current conditions and five-day forecasts from Open-Meteo.
- [x] Nearby live aircraft signals from the adsb.lol ODbL point API.
- [x] LIVE and FORECAST provenance, source, freshness, and honest failure states.
- [x] LG remote and gamepad globe movement.
- [x] F-16-inspired Pilot Mode HUD and low-altitude viewing-camera controls.
- [x] Explicit simulation language: Pilot Mode is not represented as a real
      aircraft cockpit feed.
- [x] Recent NASA DSCOVR EPIC natural-colour Earth imagery with capture-time
      provenance and SEN STV-1's embedded 4K Earth stream from the ISS.
- [x] Local rendered-Earth fallback plus mother-proxied OpenStreetMap tiles for
      real location navigation on restricted television browsers.
- [x] Separate `Live View from Space` and `Track ISS` modes; a telemetry marker
      is never presented as camera footage.
- [x] Fabric-native private controller channel, including direct Lapland, home,
      NASA Earth, live-camera and ISS-tracker controls, for televisions whose
      browsers do not expose gamepad or remote key events.
- [x] Direct voice routing for “fly to”, NASA Earth and ISS Live commands so
      geographic navigation cannot fall through to trip planning.
- [ ] Optional owner-supplied Google Photorealistic 3D Tiles visual upgrade.
- [ ] Public-camera catalogue and calibrated view projection.
- [ ] Earthquake, fire, vessel, traffic, and live-event layers.
- [ ] Natural place/flight/layer parameters carried directly from speech into
      the active God View session.

## AION Native intelligence substrate — implemented in 0.19.0

- [x] OpenAI removed from the primary research route.
- [x] Three explicit policies: AION Native, AION + Gemini, and Pilot Boost.
- [x] Bounded public-evidence acquisition remains useful without paid AI.
- [x] Local Gemma synthesis before optional cloud providers.
- [x] User-key Gemini synthesis separated from optional Search grounding.
- [x] Local provider-usage ledger and configurable Gemini safety allowance.
- [x] Result provenance labels and non-secret route traces.
- [x] HTTPS source enforcement, claim-index checks, and contradiction detection
      outside the model.
- [x] Air-gapped, internet/no-paid-AI, and premium-enabled routing tests.

## Phase 1 — The television wedge

### 1. Live Companion foundation — implemented in 0.15.0

- [x] Bounded 30-second in-memory audio context; no raw audio persistence.
- [x] Fresh webOS application/audio-state observation after an explicit request.
- [x] Structured, hashed `pilot.live.context.v1` evidence object.
- [x] “Pilot, fact check that” intent and evidence-labelled Canvas result.
- [x] “Pilot, explain that” intent with honest insufficient-context handling.
- [x] Mirrored live evidence panel on the private phone controller.
- [x] Signed `pilot.moment.v1` context card.
- [x] Rights boundary: no protected programme audio or video copied.
- [x] Real LG field verification for state observation and Moment preparation.

### 2. Real screen understanding — active

- [x] Provider reference normalization for YouTube, Netflix, and Twitch.
- [x] Optional official YouTube Data API metadata enrichment.
- [ ] Authenticated native metadata adapters for each supported signed-in service.
- [x] Owner-visible phone-camera observation with local pixel deletion.
- [x] Positioned OCR and confidence-labelled fusion with cached webOS metadata.
- [x] OCR, objects, faces-as-unknown-entities, subtitles, scoreboards, products,
      locations, and scene-change detection.
- [x] Confidence fusion across webOS state, service metadata, transcript, and
      owner-provided pixels.
- [x] Never infer unseen pixels; always label source and confidence.
- [x] Private correction mechanism bound to the current observation and persona.
- [x] Explicit ten-minute Observer Mode lease with visible start, frame-rate limit,
      token validation, immediate pixel deletion, and persona-bound stop.
- [ ] Production TLS or native phone shell required for continuous mobile camera use.
- [ ] Observe → act → observe → verify loop for every third-party navigation.

### 3. Live Companion experiences

- [ ] Actor/person lookup without exposing household identity.
- [x] Spoiler-aware observed-scene explanation with playback preservation.
- [x] Playback-preserving local translation of recent dialogue and captured subtitles.
- [ ] Optional synchronized dubbed or subtitle projection.
- [x] Captured scores and clocks plus evidence-bounded incident/rule explanation.
- [ ] Authenticated player statistics, live event feeds, and alternate commentary.
- [x] News-claim extraction, claim decomposition, source-labelled fact checking,
      correction timeline, playback-preserving spoken verdict, and grounded
      evidence-provider failover (0.18.1).
- [ ] Native-TV compact overlay while another application remains visible; the
      LG gateway cannot obtain this system-only authority.
- [ ] Products, recipes, destinations, music, and learning concepts detected from
      the current programme and privately saved.
- [ ] Accessibility: dialogue enhancement, background-sound reduction when the TV
      supports it, descriptive summaries, and reading-level control.

### 4. Pilot Moments and sharing

- [x] Provider-aware, rights-aware signed Moment foundation.
- [x] Fact-check evidence binding, private recipient selection, immutable preview,
      separate Send confirmation, adapter gating, verified receipts, expiry,
      replay protection, rate limits, revoke, and delete.
- [ ] YouTube timestamp links and provider-native clip adapters.
- [ ] Native Netflix/streaming share mechanisms where officially available.
- [ ] Context-card fallback containing title, timestamp, reaction, and official link.
- [ ] Recipient picker on the private phone; never resolve a person from shared-TV
      speech alone.
- [ ] Private preview and explicit Send confirmation.
- [ ] Delivery receipts, revoke/delete controls, abuse reporting, and rate limits.

### 5. Entertainment and discovery

- [x] Cross-service evidence-labelled title search and household preferences.
- [ ] Verified deep links and playback continuation for each supported service.
- [ ] Account entitlement checks without credential projection.
- [ ] Natural requests based on mood, time, people present, duration, and history.
- [ ] Shared recommendations that do not leak one persona’s private watch history.

### 6. TV product quality

- [ ] Native signed webOS application and equivalent Samsung/Android TV shells.
- [ ] Stable focus model, universal Back/Home behavior, and automatic recovery.
- [ ] Fast wake, interruption, cancellation, barge-in, and TV-dialogue rejection.
- [ ] Natural local speech with selectable voice and household quiet modes.
- [ ] Multi-TV routing: “this TV”, room names, handoff, and synchronized surfaces.
- [ ] Consumer installer, TLS, automatic updates, crash recovery, and diagnostics.
- [ ] Accessibility and child-safety review.

## Phase 2 — Personal Pilot

### 7. Private identity and continuity

- [x] One universal device node can lease capabilities to multiple trusted mothers.
- [x] Persona-separated preferences, approvals, calendars, accounts, and payment references.
- [ ] Native phone identity with biometrics and signed device possession.
- [ ] Clear active-person indicator on every shared screen.
- [ ] Memory controls: inspect, correct, forget, export, and household/private scope.
- [ ] Cross-device task continuation with minimum necessary disclosure.

### 8. Life Concierge

- [ ] To-dos, reminders, calendar, email, messaging, maps, shopping, booking, and music.
- [ ] Research → prepare → private review → approve → execute once → verify → receipt.
- [ ] Voice and TV requests hand off sensitive details to the correct private phone.
- [ ] Car continuation for reminders, navigation, calls, and safe voice capture.
- [ ] Emergency and elderly-safety mode with explicit setup, location, trusted contacts,
      escalation policy, false-alarm handling, and regional emergency-service review.

## Phase 3 — The natural network

### 9. Contact graph and household coordination

- [ ] Add/invite a trusted contact by private phone confirmation.
- [ ] Pilot-to-Pilot structured requests with sender identity and requested outcome.
- [ ] Recipient chooses whether a request becomes a reminder, route, task, or message.
- [ ] Examples: pickup coordination, calendar proposals, shared lists, arrival-aware
      reminders, family logistics, and shared viewing Moments.
- [ ] No silent task assignment, location disclosure, purchase, booking, or message send.

### 10. Viral loop

- [ ] A delightful TV action produces a useful private artifact.
- [ ] The owner chooses a contact and previews exactly what will be shared.
- [ ] Non-users receive a useful web artifact plus an optional Pilot invitation.
- [ ] New users inherit no private data; trust begins with a new signed identity.
- [ ] Measure activation through usefulness, not forced invitations or dark patterns.

## Immediate next engineering sprint

Expand authenticated sports statistics and live-event feeds, then add private
follow-through from saved items into separately approved research and services.
