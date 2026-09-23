# AION Device Fabric — Developer Preview

This additive preview represents one governed AION across a capable mother node,
installable edge nodes, and gateway representations for restricted devices.

Current packaged release: **Pilot Fabric 0.47.0**.

## Production private identity and Pilot stream (0.47)

Pilot now separates people at the mother-brain boundary rather than treating a household
as one account. Adults onboard independently; child profiles require an active adult
guardian. A browser phone can generate an Ed25519 key locally, prove possession through a
one-time signed challenge and activate one identity on shared screens for a bounded
session. Activation nonces cannot be replayed. The television receives only the active
display name and never receives memory, device keys or service credentials.

Each identity can inspect, correct, export, rescope or selectively delete its memory;
grant or revoke exact service scopes; revoke a lost device; or recover the account with
one-time recovery material that revokes previous phones. Browser possession is not
mislabelled as biometric: hardware-backed native-phone attestation remains a production
qualification.

The Pilot stream is a private agent inbox rather than an unfiltered group chat. It holds
personal and household lists, direct messages, tasks and reminders. A task sent to another
person remains `awaiting_recipient_acceptance`; it cannot become their obligation until
they accept. Arrival, departure and journey reminders require an explicit location
permission reference. Suggested route stops remain `suggested_not_added` until accepted.
Shared television voice can reveal summary counts but not private task titles.

The Google Tasks adapter posts an approved task through the official Tasks v1 insertion
endpoint and accepts success only when Google returns a verifiable task identifier and
reference. A real persona-bound OAuth connection is intentionally still required.

## Private entertainment personalization and follow-through (0.45)

Viewing feedback spoken in the shared room now creates an unassigned preference. The
private phone must claim it before it enters one persona's history, with a separate choice
required to expose it to household recommendations. Private and explicitly shared
watchlists use the same boundary. Another persona cannot read private history or watchlist
items.

The deterministic recommendation layer ranks provider-supplied candidates by an explicit
mood, maximum duration, time of day, presence and catalogue family-safety label. It excludes
watched, disliked or avoided titles only from the active persona or from history deliberately
shared with the household. Entitlement always remains unknown until an authenticated provider
adapter confirms it, and no paid model is required.

Episode reminders require exact provider, content and episode metadata and a future time.
They remain in the local private inbox; native push is not claimed. Provider-health records
can distinguish available, degraded, outage, sign-in-required and unknown states. Sign-in
recovery opens the official provider surface for owner action and never reads or stores raw
credentials. Existing exact official deep links, private execution confirmation, signed
playback/entitlement telemetry, continue-watching preparation and room handoff contracts
complete the locally enforceable execution path.

## Contextual companion and wellbeing boundary (0.44)

Contextual Companion is disabled until a private persona opts in. Its saved profile
controls offer frequency, quiet hours, reading level, larger controls, approved interests,
humour preferences and conversation topics. A deterministic cadence gate enforces quiet
time, minimum intervals and a daily proactive limit. It explicitly disables engagement
optimization, exclusivity language, covert persuasion and claims of human consciousness.

Advert-break quizzes require advert-break evidence; discussion and explanation offers are
dismissible and do not interrupt playback. A shared-room loneliness request receives a
transparent neutral response and remains unassigned until claimed on the private phone.
Urgent fall, breathing, danger or self-harm language crosses into the Guardian boundary:
Pilot advises use of local emergency services and may prepare a trusted-contact alert, but
never claims diagnosis or that help has been dispatched.

Cross-surface continuation creates a persona-bound, replay-protected handoff containing a
bounded objective and summary rather than a raw transcript. The destination phone or car
must accept it. Trusted-contact calling is preparation-only until a signed phone or TV-call
adapter returns an explicit receipt. The private phone can switch to a genuinely larger,
simpler control presentation through the same persona settings.

## Live Companion local completion and authority boundaries (0.43)

The locally enforceable Section 6 scope now spans exact-current-cast person credits,
strict Wikidata programme origins, joke/reference/cultural context, child and selectable
detail modes, descriptive accessibility summaries and scene-derived science, history and
language activities. Screen fusion retains bounded ingredient, technique and object
labels without claiming product identity. Advertising and product statements route
through the same evidence-labelled fact-check engine.

Authenticated live-event responses may expose goals, bookings, substitutions and
lineups; Pilot reports only fields the feed supplies. Historical team comparisons require
an explicit one-to-365-day range and reject ambiguous team identity. Close-match alerts
remain unassigned on a shared television until claimed on the private phone. Predictions
are persona-bound and cannot enable money or betting. The repeatable public fact-check
benchmark fixes expected verdicts before execution and measures HTTPS evidence coverage,
latency and provider failure outside the model. A signed fact-check Moment can be delivered
with a verified receipt to the local private-phone inbox.

Platform and rights operations fail closed. Synchronized subtitle projection requires
native overlay authority, caption projection authority and explicit subtitle rights.
Local dubbing requires an authorized audio route and content rights. Dialogue/background
processing requires a signed hardware DSP preset. Highlight requests return only official
HTTPS routes marked provider-verified and rights-authorized; Pilot never downloads or
copies protected programme video. External qualification remains recorded separately in
the Section 6 blocker register.

## Evidence-backed programme cast companion (0.42)

Live Companion can now answer cast and exact character questions after production
perception has established a stable programme identity. Main-cast evidence comes
from TVmaze rather than model recollection. Exact character questions require an
exact normalized character match. When asked “who is that actor?”, Pilot refuses
to infer the visible person's identity and instead provides the verified programme
cast. It never claims that a cast member is present in the current scene.

The cast response is bounded to normalized names, characters and official public
references, cached for twenty-four hours, capped at fifty programmes and labelled
with TVmaze attribution. No pixels, face embeddings, audio, credentials, account
identifiers or protected media are transmitted or retained. Playback stays visible
and the fuller evidence list appears on the private phone.

## Programme identity and catalogue evidence (0.41)

Pilot can now turn repeated owner-captured title evidence into a bounded public
programme identity without confusing recognition with playback. Media-screen OCR
produces title candidates; the multi-frame timeline requires repetition before a
candidate may leave the mother brain as a text-only TVmaze catalogue query. Pilot
accepts only one normalized exact title match. Multiple exact records and fuzzy
results remain unverified.

Evidence types remain explicit. Signed provider telemetry can establish current
playback. Official provider metadata can establish a provider record. A TVmaze
match establishes only a public catalogue identity. Repeated OCR remains a local
observation. None of the latter three proves subscription, regional availability
or household entitlement. Queries contain no pixels, audio, tokens or account
identifiers; results are cached for twenty-four hours in an owner-only bounded
cache and retain the required TVmaze attribution.

## Universal television reliability qualification (0.38)

Pilot now applies one persistent reliability contract to governed television
operations. Every operation binds a device, goal, bounded route, pre-action
evidence, action receipt, explicit success criterion and terminal evidence.
Button delivery is never promoted to screen success. Device read-after-write,
structured owner-camera observations, signed provider telemetry, local
idempotency proofs and tightly bounded owner visual confirmation are accepted
for field closure. Owner confirmation is eligible only when Pilot already holds
a verified transport receipt and a distinct post-action observer-image hash.

The private controller now supplies a Home control, an exact Netflix title test,
named Netflix profile switching and a visible qualification report. Profile labels
are learned from an explicitly captured chooser observation and retained as local
metadata; credentials are neither read nor retained. Netflix search waits
for local OCR containing the requested title; directional navigation, Back,
Home, pointer, profile and playback actions wait for an after-observation unless
an independently trusted device/provider state can prove the outcome. Source
camera frames remain locally processed and immediately deleted.

Browser retries carry one request identifier. Repeated delivery of the same
identifier is suppressed before another television action is emitted and is
recorded as a separate local idempotency proof. Superseded, failed and unverified
transactions remain visible in bounded history rather than disappearing.

Section 3 closes for an adapter only after at least 20 real field cases, a 95\%
verified-or-bounded-recovery rate and successful evidence in connection recovery,
state observation, reversible audio, application launch, directional navigation,
Back/Home/Exit, focus/pointer, in-app search, profile selection, playback and
duplicate suppression. Simulations and transport-only acknowledgements are
excluded. The paired LG adapter completed 24 of 24 eligible field cases across
all eleven areas, for a 100\% verified-or-recovered rate. Section 3 is therefore
closed for this LG adapter. This release does not claim Samsung or Sony support
without a vendor adapter and corresponding field evidence.

## Multi-room television routing foundation (0.37)

Pilot now maintains a mother-local registry that binds each enrolled television
node to one unique household room name, current endpoint and explicit default.
The private controller can name the present TV and displays its room beside the
current surface. “This TV” resolves only when the current node is known; named
rooms require an exact unique match, and ambiguous or missing targets fail closed.

Cross-room continuation is a two-stage private operation. Pilot requires signed,
persona-bound evidence containing a title and active playback state before it can
prepare a handoff. The prepared record contains provider, content identifier and
position but no account credentials. The owner then confirms the immutable hash
on the private phone. Confirmation advances only to
`approved_pending_destination_adapter`; Pilot does not claim playback on the
destination until that TV's authorized adapter observes and verifies it.

The registry and handoff history survive restarts, prevent duplicate room names,
isolate the requesting persona, reject confirmation replay and record metadata-
only audit receipts. One installed node remains reusable by multiple authorized
mother brains through the pre-existing universal-node lease boundary; room names
and private playback remain local to each mother/persona relationship.

## Voice lifecycle, privacy history and quiet mode (0.36)

The local microphone service now publishes an explicit operational lifecycle:
`listening`, `hearing`, `thinking`, `acting`, `speaking`, `completed`, `error`,
`sleeping` and `off`. The dashboard updates this state live so the household can
distinguish audio detection from reasoning and action. Background speech rejected
without the wake phrase returns the service to listening and is labelled as such.

A bounded activity history stores only state, timestamp and outcome class. Each
entry asserts that it contains neither transcript content nor audio. Existing
ephemeral transcription diagnostics remain in volatile service memory; microphone
sleep clears the audio ring and closes the device stream.

Quiet mode suppresses spoken replies while retaining governed command execution
and visible results. The owner can restore spoken responses locally. Voice name
and rate are allowlisted and bounded to installed macOS voices and 120--240 words
per minute. These preferences persist only inside the mother runtime and are
never sent to television nodes. Preference changes are audit events without
speech content.

## Production fact-check evidence record (0.35)

Pilot's live-news path now freezes every completed check as a versioned,
content-hashed evidence record. It retains the bounded statement, decomposed
claims, per-claim verdict and confidence, date scope, sanitized HTTPS sources,
correction timeline, provider route and measured end-to-end research latency.
Raw microphone audio, source pixels and raw provider responses remain excluded.

Source quality is calculated outside the language model. Primary government and
intergovernmental sources, academic institutions and established editorial
publishers receive explicit classifications and quality rationales; unknown
organizations remain usable but lower confidence. This is a provenance signal,
not a claim that any institution is automatically correct.

Pilot normalizes claims and detects conflicting verdicts for the same statement.
`Disputed` claims and contradictions are recorded separately from the model's
summary. Follow-ups such as **show me the evidence**, **who disagrees?** and
**explain the difference** are generated deterministically from the frozen
record. If no named disagreement, definition change, date difference or
measurement difference is established, Pilot says so rather than manufacturing
one. These follow-ups preserve television playback and expose full evidence on
the private phone.

The companion interface now presents source class, source-quality rationale,
mean source quality, research latency, contradiction count, individual claims
and the correction timeline. Every follow-up has its own evidence hash and is
audited against the original fact-check identifier.

## Signed provider playback telemetry (0.33)

Pilot now has a provider-independent trust boundary for real programme and
playback facts. A native provider application, authorized account adapter or
capable device node is registered locally with an Ed25519 public identity, one
provider, one private household persona and explicit `metadata.read`,
`playback.read` and/or `entitlement.read` scopes. Registration requires local
approval; a shared television cannot choose the persona.

Every `pilot.provider-telemetry-envelope.v1` packet is signed over canonical
JSON and includes a bounded UTC observation time and one-use nonce. Fabric
rejects unknown sources, invalid signatures, provider/persona mismatches,
timestamps older than two minutes, future packets and nonce replay. The
ingestion route is available only through the trusted HTTPS companion and still
requires its tokenized path and CSRF boundary.

Accepted data is normalized to provider, content identifier, title, series and
episode labels, playback state, position, duration and separately scoped
entitlement status. Raw provider responses, account handles, OAuth tokens and
credentials are never retained. Public adapter keys remain in the mother-local
trust registry and are excluded from phone/status snapshots.

A matching persona/provider/title execution can be upgraded from an attempted
route to provider-open or playback-verified. The signed title, playing state and
position also enter multi-frame screen fusion. Signed position outranks OCR
position but keeps its `signed_provider_adapter` provenance. Unsigned owner
camera evidence continues to work when no adapter exists and is never silently
promoted to provider telemetry.

This release implements the secure contract and fusion path, not unauthorized
access to closed providers. Netflix and other restricted services still require
an owner-authorized native or account adapter that is permitted to expose those
facts. Pilot neither scrapes sign-in credentials nor treats catalogue metadata
as entitlement or playback.

## Trusted private-phone HTTPS (0.32)

Pilot now runs a second private companion on LAN port 8769 using TLS 1.2 or
later. The existing port 8767 service remains a bootstrap and recovery route.
The mother generates a private household root and a 397-day server certificate
with the bundled Python cryptography library. The server Subject Alternative
Name binds the current LAN address, the mother hostname, localhost and the
loopback address. Address changes rotate the leaf certificate while preserving
the household root, so a previously trusted phone does not need a new root for
ordinary DHCP changes.

The CA and server private keys are created inside the mother runtime directory
with owner-only permissions. They are never returned by an API, projected to the
TV, included in status, or written to the audit ledger. Only the public root
certificate is available from the local pairing page. The laptop dashboard and
pairing page display its SHA-256 fingerprint; the owner must compare that value
before enabling trust, protecting the unauthenticated LAN bootstrap from silent
certificate substitution.

After the rotating code is accepted, the bootstrap redirects to the HTTPS
controller. Secure responses add HSTS while retaining tokenized paths, CSRF,
rate limits, no-store caching, frame denial, restricted content security policy,
and `camera=(self), microphone=()` permissions. Camera access remains visible
and user initiated.

On an unsupervised iPhone, downloading a root does not automatically trust it for
TLS. The owner must review installation and separately enable full trust in
Certificate Trust Settings. Pilot does not automate either step. Apple recommends
Configurator or device management for automatic organizational trust; consumer
Pilot therefore keeps manual trust explicit. Removing the Pilot profile revokes
phone trust. If TLS creation fails, Fabric keeps the HTTP recovery controller
and records only the error class.

## Multi-frame production-perception foundation (0.31)

Owner-submitted phone captures and visible Observer Mode frames now enter a
bounded `pilot.multi-frame-perception.v1` timeline after local Apple Vision and
screen-fusion processing. A single image can no longer establish a stable
surface or programme. Surface stability requires at least two recent frames and
two-thirds agreement. Programme titles require repeated provider-metadata
support; official metadata verification is retained as a separate boolean.

The timeline ignores repeated identical image hashes, keeps at most twelve
structured frame records, and evaluates a rolling ninety-second observation
window. It records surface support, stable programme evidence, recent subtitle
changes, scene-change evidence and an optional OCR playback position. An OCR
position is labelled `owner_camera_ocr` and never represented as provider-
verified playback telemetry. Raw source pixels and audio remain excluded.

The private controller now displays the multi-frame surface, programme stability,
confidence, subtitle timeline and playback-position evidence. The Observer Mode
frame lease survives normal page suspension in the same tab through browser
session storage. Camera tracks and timers stop on page hide; restoration requires
the user to press **Resume after phone sleep**, preventing invisible camera
restart. The backend token remains hashed, rate-limited, persona-bound and
ten-minute limited.

This closes the multi-frame and reconnection protocol foundation, but local LAN
HTTP is not a production camera transport. Continuous iOS/Android capture through
lock, backgrounding or a closed page still requires trusted TLS or a signed
native Pilot companion. That deployment boundary is shown explicitly rather
than bypassed.

## Universal verified navigation (0.30)

Private-phone navigation, media and application actions now execute inside a
persistent `pilot.verified-navigation.transaction.v1` record. The transaction
binds television node, believed surface, user goal, expected result, ordered
routes, bounded attempts, pre-action evidence and post-action evidence. A signed
webOS receipt establishes only that the transport or device operation completed;
button delivery is explicitly excluded as proof of the visible result.

Device-observable goals can close from permitted structured state, such as the
foreground application. Visual goals enter `awaiting_after_observation` until an
owner-visible Observer Mode frame or manual phone capture supplies a structured
surface, view and evidence hash. Profiles and consent-screen exits use semantic
view criteria; focus movement and generic navigation require an actual changed
screen hash. Raw source frames remain deleted after local analysis.

Failed verification either enters `recovery_ready` with the next bounded route
or ends `not_verified`. At most three device attempts are permitted. The phone
shows the goal, expected outcome, attempt count, remembered route count, and a
recovery button only when a specific alternative is available. Route memory is
scoped by television, surface, goal and route identifier, recording successes
and failures so proven routes are ranked first on the next transaction.

The current release provides automatic verification closure and user-triggered
bounded recovery for the private phone. Full autonomous multi-step recovery for
every third-party application remains dependent on the production perception
stage and application-specific safe route libraries.

## Verified entertainment execution (0.29)

Pilot now separates entertainment discovery, entitlement, provider opening and
playback into four different evidence states. A discovery result is eligible
for execution only when it is an exact credential-free HTTPS route on a bounded
official Netflix, YouTube, Prime Video or Disney+ host. Search pages, catalogue
aggregators, arbitrary domains, credentials, non-standard ports and ambiguous
provider pages fail closed. Canonical route hashes are retained for audit while
raw URLs are excluded from the shared audit ledger.

The selected title and provider are bound to the active private-phone persona in
`awaiting_private_confirmation`. Confirmation moves it only to
`approved_for_device_attempt`; it does not establish subscription access or
playback. Netflix uses the television's governed numeric title contract. Other
supported providers open their canonical public route through the restricted TV
browser policy. The signed phone app-launch capability and existing webOS
pairing remain mandatory.

Receipts deliberately distinguish `provider_open_verified` from
`playback_verified`. A provider-open result needs a verified device receipt and
an observed foreground/app effect. Playback requires separate explicit evidence
containing both the title and an active playing state; the current LG integration
does not expose that generally, so the developer preview honestly stops at
provider-open verification. “Continue watching” re-prepares the last verified
route for the same persona and demands a new confirmation. Shared-TV speech
never chooses private history, and entitlement remains
`unknown_until_provider_confirms` until an authorized provider adapter exists.

## Governed saved-item follow-through (0.28)

The private phone can continue a persona-owned television save through three
strictly different routes. Research sends a category-specific bounded query
through the provider-independent AION research router and stores sanitized HTTPS
evidence links with no external effect. Local shortlist, task and learning
routes create private drafts and do not contact a service. Shopping, trip and
playlist routes create a new `aion.service-execution.v1` proposal with an exact
scope, missing-field state and independent approval.

The originating save is reloaded by identifier and checked against the active
phone persona before any continuation. Cross-persona access is rejected. A trip
proposal remains `needs_details` until its private date is supplied. Complete
proposals enter `awaiting_private_approval`; approval changes the state only to
`approved_pending_adapter`. It cannot imply purchase, booking or account change.
Real execution still requires a separately authorized persona adapter, execute-
once reconciliation and a verified receipt.

Follow-through records bind the source item hash, persona, exact scope, research
route, proposal state and a new record hash. Audits omit raw private content and
record `external_action_executed: false`. The phone explicitly explains that a
saved item is memory and evidence, not standing authority.

## Live Event Intelligence (0.27)

Pilot now routes score, scorer, statistics, fixture, concert and live-event
questions through a provider-independent evidence layer. The first authenticated
adapters implement football-data.org v4 using a mother-local `X-Auth-Token`, and
Ticketmaster Discovery v2 using a mother-local API key. The provider endpoints,
authentication patterns and bounded resources follow the providers' published
documentation: [football-data.org v4](https://www.football-data.org/documentation/quickstart)
and [Ticketmaster Discovery v2](https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/).

Football match responses are normalized to competition, teams, status, clock,
score, update time and supplied goal events. Team names extracted from the latest
owner-captured scoreboard are matched deterministically against candidate
provider fixtures. The output preserves three separate fields: authenticated
provider fact, owner-captured screen observation, and Pilot rule interpretation.
A score disagreement becomes `screen_provider_conflict`; the two values are
never silently merged. Scorer identity is spoken only when the authenticated
feed supplies the goal record. Unsupported player statistics produce an honest
provider-tier limitation.

Both adapters enforce HTTPS fixed hosts, twelve-second timeouts, a 512-kilobyte
response limit, bounded result counts and normalized output. Raw provider
responses are discarded. Keys remain on the mother brain and are excluded from
the TV, phone, returned request URL, status record and audit ledger. Without a
configured key, Pilot retains the captured-screen answer and explicitly labels
the authenticated feed unavailable. No paid AI is required and playback remains
visible.

## Programme-to-private saving (0.26)

An explicit “save this” request creates a short-lived evidence card for a
product, recipe, destination, song, learning concept, or general idea. Candidate
details are assembled deterministically from the bounded live-context record,
the latest owner-initiated screen observation, and provider metadata. Each card
contains confidence, provenance lines, an evidence hash, and explicit negative
claims for purchase, messaging, retained raw audio, and retained source pixels.

The shared television is not an identity boundary. It may prepare the card but
cannot assign it to a persona. A pending card expires after thirty minutes and
enters private memory only when the active phone identity presses **Save to my
Pilot**. Persona-filtered snapshots prevent another household identity from
viewing the saved collection or even the identity-bound current item; deletion
also requires the owning persona. Audit records retain identifiers and hashes,
not the raw programme-derived content. This is a memory action only: shopping,
messaging, booking, and calendar execution remain separate approval-gated flows.

## Evidence-bounded Live Sports (0.25)

Sports interpretation consumes the latest structured scoreboard and clock from
the owner-initiated screen observation, plus recent local commentary and
captured subtitles. Score parsing can structure the opposing team labels and
values and derive the current leader. It always labels the result as a captured
snapshot that can become stale.

Named incident questions route through a deterministic local rule library.
Observed commentary cues and inferred rule explanations occupy separate fields.
When no incident cue exists, Pilot may explain the named rule but cannot claim
what occurred; an entirely ambiguous referee question produces an explicit
insufficient-evidence response. Player identity is never inferred and the
referee decision is never marked verified. The record retains evidence hashes,
confidence and limitations while the spoken summary preserves playback.

## Local Live Translation (0.24)

The translation intent selects the most recent bounded local dialogue or, when
explicitly requested, the latest owner-captured subtitle. It never treats
programme dialogue as an instruction. Local Gemma receives only the quoted line
and target ISO language under a translation-only schema that prohibits
explanation, continuation and added context. A validator outside the model
requires numbers and URLs to remain intact. Common phrases retain an offline
deterministic fallback; otherwise Pilot reports that the local route is
unavailable rather than invoking a paid provider.

The persisted record labels source evidence, detected and target languages,
provider, confidence, uncertainty, privacy properties, and evidence and record
hashes. No raw audio or pixels are retained. The television remains on the
programme while a language-appropriate installed system voice speaks the short
translation and the detailed record appears on the private phone.

## Spoiler-aware scene explanation (0.23)

Pilot separates scene clarification from general web research. The explicit
phrases “what just happened?”, “what did they just say?”, and “explain this scene
without spoilers” construct an observed-evidence envelope from the bounded local
dialogue window, owner-captured subtitles, structured screen observation, and
owner corrections. Programme titles and public plot summaries are deliberately
excluded from the local model prompt.

The explanation schema contains the answer, observed facts, uncertainty,
playback boundary, evidence types, provider, confidence, and hashes. A
deterministic guard rejects forward-looking phrases commonly associated with
future plot disclosure. If current evidence is absent—or a safe local result is
unavailable—Pilot preserves the captured line or refuses to guess. The TV keeps
playing while the concise result is spoken; full provenance remains on the
private phone.

## Private confirmed sharing (0.22)

The first production-shaped Pilot Moment path binds a completed fact-check's
evidence record into a signed card. Shared-TV speech may request preparation but
cannot select a recipient or cause delivery. The private phone displays the
statement, verdict, confidence, source links, delivery route, and recipient.
Recipient selection creates an immutable preview hash; Send is a second action
and fails if the preview changed. Delivery executes only through an authorized
persona-bound adapter and requires a verified receipt. Without one, the state is
`approved_pending_adapter` and the interface says that nothing was sent.

Each Moment expires after 24 hours, is limited to three adapter attempts, rejects
replayed or mismatched previews, and supports revoke and private-data deletion.
Audit records retain identifiers, state, and a recipient hash rather than the
raw address. Protected television audio and pixels remain excluded.

## Consumer reliability and recovery (0.21)

Pilot now stores the private phone, CSRF, Canvas, and learning-session bearer
values in an owner-readable-only file inside the mother runtime. They are
generated once and reused after service or machine restarts, so an installed
phone controller does not silently expire. These values remain outside the TV,
the audit ledger, release archives, and COMDEX intelligence sources.

A bounded watchdog checks only the paired webOS control sockets. If DHCP changes
the television address, the existing signed device evidence is matched against
fresh discovery observations, candidate addresses are tested, and the pairing
key is migrated to the reachable endpoint. Playback is not interrupted and the
Canvas is not forced over the programme. The dashboard exposes a simple
Connected/Reconnecting state and an owner-triggered retry endpoint.

The preview bundle includes `Install Pilot.command`. It copies the immutable
application payload to the user's Application Support folder, creates the
isolated environment, and registers a per-user macOS launch agent with
start-at-login, `KeepAlive`, throttled restart, and local logs. Uninstallation
first removes automatic startup and deliberately retains the data directory so
accidental removal is recoverable; erasing retained user data is a separate,
explicit action.

It does not modify or automatically start HexCore, Boardroom, Mission Mode,
GlyphNet, the existing Local Node runtime, or any AION learning service. The
preview uses its own runtime directory and SQLite ledger.

## Safety model

- Discovery records visibility only.
- Enrollment requires an explicit approver identity.
- Capabilities can be issued only to enrolled nodes.
- High-risk capabilities must require approval.
- Nodes sign state deltas with Ed25519 device identities.
- Repeated device observations can be batched into one signed template+delta
  Glyph stream, reducing signature and framing overhead for constrained links.
- The mother verifies sequence, ancestry, payload hash, signature, and resulting
  state before accepting a delta.
- Restricted devices are represented as gateways; the preview never attempts to
  install software onto a discovered device.
- Autonomous discovery is bounded to Bonjour advertisements, one SSDP request,
  the existing neighbor cache, and known macOS Bluetooth records.
- Advertised local descriptors may be downloaded with URL, size, redirect, and
  local-address restrictions; each artifact is hashed before schema inference.
- Inferred controls remain disabled until enrollment. Live actions require a
  signed capability capsule, a paired device adapter, bounded arguments, and a
  verified action receipt.

## Run the proof

```bash
.venv/bin/python -m backend.modules.aion_fabric.cli \
  --runtime-dir .runtime/aion_fabric_test demo
```

The proof creates an isolated mother node, a small fridge edge node, and a
restricted-TV gateway. It enrolls them, issues a signed capability capsule,
accepts two signed fridge deltas, and prints the reconstructed mother state and
ledger counts. It then accepts a 1,000-update signed Glyph stream and reports
the measured reduction against repeatedly sending full raw state snapshots.

## Start the local mother

```bash
.venv/bin/python -m backend.modules.aion_fabric.cli serve --demo --open-browser
```

The visual dashboard opens at `http://127.0.0.1:8765/`. Machine-readable status
remains available at `http://127.0.0.1:8765/status`. The terminal window must
remain open because it is the running mother process.

### Real discovery and read-only field test

1. Select **Discover nearby devices**. AION listens for Bonjour and SSDP,
   inspects the existing ARP neighbor cache and known Bluetooth records, and
   resolves advertised services.
2. For devices that advertise local descriptors, AION downloads bounded copies,
   stores their hashes, parses device/service XML, and constructs a control
   schema. The device remains **discovered**.
3. Select **Enroll read-only gateway** for a device with evidenced query
   actions. This creates a local gateway identity and a mother-signed capsule
   containing only low-risk read capabilities. No mutating action is granted.
4. Select **Run permitted read-only probe** to send one schema-backed UPnP
   status query. Its request and response are hashed into a probe receipt.

### LG webOS intelligence surface

After the owner approves the LG pairing prompt, the governed adapter can read
volume and device state and execute a bounded set of signed capabilities:
volume up/down/set (capped at 50), mute, playback, mapped HDMI inputs, Netflix,
YouTube, and the AION TV Canvas. Power, purchases, accounts, security settings,
firmware, credential discovery, and permission escalation remain blocked.

The private dashboard and all control endpoints remain on localhost. A second
server exposes only a token-protected, read-only Canvas on LAN port 8766. The
Canvas receives a sanitized state projection—node counts, audit status, TV
name/volume, and the last local voice exchange—and accepts no POST requests.
The token is regenerated whenever AION starts.

Voice commands require the local AION wake phrase. Raw microphone audio is
processed locally and discarded. TV-native views include Home, Device Mesh,
Boardroom, and Briefing. Movie Mode is an explicit two-action scene that opens
Netflix and sets volume to 20, recording and verifying each action separately.
Directional, select, and back commands use a bounded pointer socket sequence.
Netflix profiles can be selected by position; saying “remember the second
profile” stores only that numeric preference inside the isolated Fabric runtime.
When the chooser is visibly present, “select my Netflix profile” recalls it.
Movie Mode does not blindly navigate because AION does not yet observe the
third-party app screen.

### TV Autopilot v0.4

Autopilot maintains a persistent, confidence-labelled belief about the active
TV surface. AION-controlled Canvas state is high confidence; LG-acknowledged
third-party app launches are lower confidence because their pixels are not
observed. Multi-action scenes are represented as named plans with explicit
steps, verification methods, evidence, completion state, and failure summaries.
The latest belief and plan are projected live onto the TV Canvas.

Voice dialogue can open a bounded 30-second follow-up window. For example,
after Movie Mode asks which Netflix profile to use, “the second one” is resolved
as the pending profile choice without requiring another wake phrase. The window
accepts only the expected constrained answer and then closes.

A metadata-only read bridge projects the number and identifiers of existing
local Boardroom sessions and the presence of COMDEX intelligence modules. It
does not load Boardroom contents into the TV response, expose credentials, or
write to existing COMDEX files.

### Private iPhone controller and phone-assisted perception v0.7

The LAN companion on port 8767 is now an installable private controller rather
than an approval page alone. After entering the restart-scoped six-digit code,
the owner can use a D-pad, volume, mute, playback, Netflix/YouTube/AION launch,
typed natural-language requests and one-task approvals. Commands carry a second
CSRF token, are rate-limited, return to the mother, require signed capabilities,
and produce audit receipts. The phone never receives the LG client key.

The owner can explicitly capture the television screen with the phone camera.
The Mac analyses JPEG, PNG or HEIC data locally using Apple Vision, deletes the
pixels immediately, and retains only bounded OCR/classification evidence, a
payload hash and inferred screen state. Supported cues include the Netflix
profile chooser, Netflix search/title surfaces, Google consent, YouTube and the
AION Canvas. A subsequent capture is matched to the pending remote action so
AION can record verified or unverified navigation rather than trusting button
delivery. LG webOS TV exposes no supported general screenshot API; this visible,
consent-driven phone observation is therefore the current lawful perception
path for third-party screens.

### Persistent conversational task context v0.8

AION now stores a compact, local conversation state containing the active
objective, explicit corrections, the bound agent task, recent user/assistant
turns and interrupted task references. “Make it cheaper”, “not that one” and
“open the second hotel” refine the active objective instead of becoming
unrelated searches. A new objective is kept separate, while “pause this task”
and “resume the previous task” provide durable interruption and resumption.

The private-phone and shared-TV channels are separated. Private turns are not
included in the television projection. The store contains text and task state,
not microphone audio or hidden model reasoning. Wake-free answer windows now
reject common background-TV phrases rather than silently appending them to a
plan.

### Cross-service entertainment intelligence v0.9

AION now maintains an evidence-labelled entertainment layer above individual
applications. Requests such as “where can we watch Dune Part Two?”, “search all
streaming services for Severance” and “recommend something funny under 90
minutes” query current Spain-facing evidence across Netflix, Prime Video,
Disney+ and YouTube, then project a single shortlist onto the TV Canvas.

Household watch memory records only explicit statements such as watched, liked,
disliked or avoid. Those titles are included as constraints in later discovery.
Provider pages and regional catalogue results are not treated as proof of
subscription entitlement, price or immediate availability; AION requires final
confirmation inside the signed-in provider before claiming playback can begin.

### Universal nodes and persona-bound service execution v0.10

An installable AION device runtime now has one durable node identity independent
of any particular mother brain. A mother that has connected before resumes its
stored public-key trust relationship. An unknown mother receives a generated
ten-minute pairing challenge that must be confirmed locally; proximity on the
same Wi-Fi is never sufficient authorization. After pairing, the node issues
short-lived, signed, replay-protected capability leases scoped to that mother
and its private principal. Multiple mothers therefore share one installed node
without sharing credentials, preferences or authorization state.

The service-execution boundary supports calendar, email, messaging, shopping,
booking, maps and music adapters. AION prepares structured parameters, binds the
proposal to an abstract household persona, requests approval on that persona's
private phone surface, and permits an adapter to execute only after the same
persona approves. The adapter must return a verified receipt. Raw passwords,
tokens, card numbers, security codes, PINs and private keys are rejected;
runtime state contains only opaque `vault://` or `provider://` references.
Until a real account adapter is connected, an approved proposal truthfully
remains `approved_pending_adapter` and creates no external effect.

### Visual and local-discovery phone bootstrap v0.12

The mother now renders a rotating local QR pairing beacon and six-digit
confirmation code. Scanning the beacon opens the mother-hosted controller entry
surface, avoiding manual IP entry while preserving explicit household consent.
On macOS the same controller is advertised as `_aion-fabric._tcp` through
Bonjour. A future signed native iOS client can therefore discover mothers on
the local network, show their identities, and request a handshake without an IP
address. Discovery never constitutes enrollment: the user must still confirm
the relationship and the resulting capability scope.

Bluetooth remains a native-app transport rather than a silent web bootstrap.
iOS requires an application and permission for Bluetooth or local-network
discovery, so Fabric does not claim that an unknown phone can be opened or
enrolled invisibly. A pre-existing account could later deliver a universal link
by push notification or message, but that is a return-user convenience rather
than the first trust ceremony.

### Google Calendar and Gmail execution adapters v0.11

The service hub now includes provider implementations for Google Calendar
`events.insert` and Gmail `users.messages.send`. Both resolve an opaque
persona-specific provider reference only at execution time; OAuth tokens are
never stored in Fabric proposals, projected to the TV or retained in receipts.
Calendar creation uses a deterministic provider event ID. Gmail adds a
deterministic Message-ID. Before a provider call, the proposal is durably marked
`executing`; a timeout or ambiguous failure becomes
`execution_failed_unknown_effect` and requires reconciliation instead of a
blind duplicate retry.

A shared-screen request cannot immediately authorize a personal action. The
private companion first offers “Prepare privately as this identity”, binds the
task to that mother's local persona, and renders its exact sanitized parameters.
Only then does the approval control become available. The Google adapters remain
disabled until the corresponding persona explicitly connects an OAuth account.

### Live research display v0.5

General “find me” requests, Netflix-title searches, local-service searches, and
product searches are executed by the mother node. When a valid OpenAI API key
is available, AION calls the Responses API with built-in web search and a strict
result schema. It retains only the sanitized answer and at most five HTTPS
results; the raw provider response and credential are not projected to TV.

If no valid research credential is configured, AION produces explicit live
handoffs instead of fabricated recommendations: Maps for local services,
Shopping for products, Netflix search for titles, and standard web search as a
fallback. “Open the second result” is independently permission-gated and opens
only the selected credential-free HTTPS URL. A short follow-up can select a
number without repeating the wake phrase.

On macOS, `scripts/start_aion_fabric.command` provides the double-click entry
point. The dashboard binds only to localhost; only the token-protected,
read-only TV Canvas is reachable from the local network.

### Pilot Live Companion and Moments v0.15

Pilot now has an explicit live-context boundary for the television. The local
voice node keeps at most 30 seconds of microphone samples in an in-memory ring;
the ring is erased on microphone sleep and process stop and is never written to
the ledger or runtime directory. Recent transcript fragments remain in memory
only until a user explicitly asks Pilot to explain, verify, or share the current
moment. At that point Fabric combines the bounded transcript with a fresh,
signed-policy webOS state observation and persists only a structured
`pilot.live.context.v1` evidence record and its canonical hash.

“Pilot, fact check that” requests current evidence with primary and
authoritative sources preferred. The answer must label the claim Supported,
Misleading, False, Disputed, or Unverifiable when the evidence provider is
available. Without an active research credential, Pilot refuses to invent a
verdict and offers an explicit live-search handoff. “Pilot, explain that” uses
the same evidence boundary and never claims to see third-party pixels that webOS
does not expose. Results are rendered on the TV Canvas and mirrored to the
private phone controller.

“Pilot, share that moment” creates a signed `pilot.moment.v1` object. It contains
app/playback metadata, the bounded context excerpt, issuer identity, canonical
payload hash, intended recipient hint, and a delivery state. It does not contain
protected programme video or audio. YouTube-like surfaces may use a provider
timestamp link; supported live providers can later use native clip APIs; all
other services fall back to a context card. This preview stops at
`prepared_not_sent` until a private recipient and an authorized messaging
adapter are confirmed.

### Non-disruptive screen-understanding fusion v0.16

The owner-initiated phone observer now retains normalized OCR geometry as well
as bounded text and classification labels. The submitted image remains a
temporary local file and is deleted immediately after Apple Vision completes.
Fabric fuses this structured capture with cached permitted webOS application
state, the current confidence-labelled screen belief, and any explicitly
created LiveContext. The resulting `pilot.screen-understanding.v1` object
contains source-level confidence and independent findings for subtitles,
scoreboards and match clocks, products and prices, locations, game HUDs, and
general scene context.

The private controller renders this model without navigating the television
away from the current programme or game. The owner may attach a correction to
the latest observation; corrections are persona-bound, audit-hashed, limited to
an allowlist of fields, and never become face-identity evidence. People visible
in a capture remain explicitly unknown. Product, location, purchase, and share
actions remain private-confirmation-only. Pilot can answer bounded screen
questions from this observation, while insufficient evidence produces a clear
request for another capture rather than a guessed answer.

### Provider evidence and explicit Observer Mode v0.17

Fabric now recognizes bounded official references for YouTube, Netflix, and
Twitch and fuses the normalized provider identifier into the screen observation.
When the owner supplies `YOUTUBE_API_KEY`, Pilot may call the official YouTube
Data API `videos.list` method for title, channel, duration, caption, live, and
embed metadata. API responses are size-limited and failures fall back to a
labelled identifier-only result. Metadata never establishes regional playback
availability or the current household's subscription entitlement.

Netflix references expose only a provider title identifier and the boundary to
the provider's supported mobile Moments feature; Pilot does not extract or copy
protected programme media. Twitch references similarly identify the official
clip boundary without pretending that a Twitch developer application or signed
account is connected.

The phone controller also exposes **Observer Mode**. Starting it creates a
persona-bound bearer lease for at most ten minutes. Frames are accepted no more
frequently than once every three seconds, analysed locally through the same
Apple Vision pipeline, and deleted immediately. Only structured observations,
hashes, and bounded session counters persist. The raw token is returned once to
the phone and is never written to disk or projected in status responses.
Stopping is explicit and bound to the initiating private persona.

Mobile browsers permit `getUserMedia()` only in a secure context. Consequently,
the current LAN-HTTP developer preview honestly refuses automatic camera mode
on browsers that enforce that rule and retains the manual capture workflow.
Production continuous observation requires local TLS with a trusted certificate
or a signed native Pilot phone shell; it will not be weakened with an insecure
camera workaround.

### Claim-decomposed live news v0.18

“Pilot, fact check that” now compiles a `pilot.live-news.v1` evidence record.
The research request uses the OpenAI Responses API with built-in web search,
strict JSON Schema output, `store: false`, and requested web-search source
metadata. It separates the captured statement into at most four independently
checkable claims and requires each claim to name only the evidence indexes that
support it. Dates, definitions, populations, and measurement periods are
explicit comparison targets. Sanitization accepts only bounded HTTPS evidence;
the provider credential and raw response are not retained.

The compiled record contains the overall verdict, confidence, per-claim
verdicts, source classes, contextual qualifications, a correction timeline,
privacy declarations, and a canonical evidence hash. A missing research
provider produces `Unverifiable` with zero confidence rather than inheriting a
verdict from a search handoff.

Release 0.19 replaces cloud-first research with an explicit mother-local
intelligence policy. `AION Native` tries deterministic capability, local AION
state and memory, local Gemma, and bounded public evidence without authorizing
a paid model. `AION + Gemini` adds user-key Gemini synthesis and separately
gated Google Search grounding after those routes. `Pilot Boost` permits OpenAI
or another premium provider only after Native and Gemini routes fail. The
dashboard exposes these three maximum-authority settings, while keys remain in
the private mother vault and never enter the TV, node ledger, result record, or
audit payload.

Every result is labelled `AION Local`, `AION + live public evidence`, or
`Pilot Boost`. The persisted route trace contains provider classes rather than
credentials. A mother-local usage ledger applies a configurable Gemini safety
allowance. HTTPS filtering, allowed-source enforcement, claim-index validation,
and contradiction detection run outside the model. If evidence exists but no
model can safely synthesize it, Pilot still presents the current sources; a
fact-check remains `Unverifiable` instead of inventing a verdict.

### Pilot God View v0.20

God View is a dedicated token-protected television surface launched through
the existing signed Canvas capability. The dashboard and TV home place its
control beside Ask Pilot. The baseline experience is deliberately useful
without a Google or paid-model key: CesiumJS renders the globe, OpenStreetMap
supplies place and imagery evidence, Open-Meteo supplies current conditions and
five-day forecasts, and the adsb.lol ODbL point API supplies bounded nearby
aircraft signals. Provider requests are executed by the mother brain with
strict coordinates, timeouts, response-size limits, cache windows, and capped
result counts; provider credentials are never projected to the television.

The display marks live signals as `LIVE`, predictive weather as `FORECAST`,
and exposes source and freshness. Unavailable feeds remain unavailable rather
than being simulated silently. The LG remote and connected gamepad can move
the globe. Pilot Mode drops the viewing camera toward the terrain and adds an
F-16-inspired HUD for bank, dive, and climb controls. It is explicitly labelled
`VIEWING CAMERA` so the experience cannot be mistaken for an aircraft's actual
cockpit video. A TV-compatible local rendered Earth guarantees a useful visual
when a restricted browser cannot render the WebGL globe. A location request
then animates into a real nine-tile OpenStreetMap neighbourhood fetched,
validated, cached, and proxied by the mother brain; Lapland therefore does not
remain a static globe merely because Cesium is unavailable. `NASA Earth Now`
replaces the visual with the newest NASA DSCOVR EPIC natural-colour image and
displays its capture timestamp as `RECENT SATELLITE IMAGE`; it is not described
as continuous live video. `Live View from Space` embeds SEN's public STV-1 4K
Earth stream from cameras mounted on the ISS and labels SEN as the source. This
is preferred over NASA's operational external-camera feed for the flagship
view because extended darkness and sensor speckles can make the latter visually
ambiguous. The separate `Track ISS` action displays current ground position,
altitude, velocity, illumination state, and retrieval source. A telemetry
marker is never presented as live camera footage.

When webOS does not expose its gamepad or keyboard events to the browser, the
private phone controller uses a signed mother-brain command channel polled by
the token-protected God View surface. It includes direct Lapland, home-region,
NASA Earth, live-camera, ISS-tracker, Pilot Mode, selection, and directional
controls, so these actions do not depend on LG browser gamepad support. Google
Photorealistic 3D Tiles are reserved as an optional owner-configured visual
upgrade because Google imagery is proprietary and metered even though CesiumJS
itself is Apache-2.0 open source.

The television experience preserves what is playing: Pilot speaks one concise
verdict while the complete evidence record appears on the private phone. The
owner can say “Pilot, show me the evidence” to replace the programme explicitly
with the full-screen Canvas. Fabric does not claim an always-on overlay through
the LG gateway because webOS notifications over other applications are
reserved for system applications; that capability requires a supported native
TV surface or platform agreement.

Normative references:

- YouTube Data API `videos.list`: https://developers.google.com/youtube/v3/docs/videos/list
- Netflix Moments: https://help.netflix.com/en/node/210664027435620
- Twitch video and clip embedding: https://dev.twitch.tv/docs/embed/video-and-clips/
- Browser camera secure-context requirement: https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia
- OpenAI Responses API create method: https://developers.openai.com/api/reference/resources/responses/methods/create
- LG webOS notifications: https://webostv.developer.lge.com/develop/guides/notifications

## Build the downloadable preview

```bash
.venv/bin/python scripts/build_aion_fabric_preview.py
```

This creates `dist/aion-fabric-preview-0.47.0.zip`. The bundle contains only the
new Fabric runtime and its bootstrap files. It excludes COMDEX memory, HexCore,
Boardroom, credentials, vaults, and existing runtime data. A later signed AION
installer can add those components through explicit release profiles after the
Fabric boundary is proven.
