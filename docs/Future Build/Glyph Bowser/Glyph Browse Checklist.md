root((GlyphNet Build Checklist)) — updated

P4 • WA/WN + Voice & Radio
[x] WA/WN Addressing (logical IDs)
[x] WA/WN identities (ucs://…; realm wave.tp)
[x] Address Book + deep-link invites (#/chat?topic=…&kg=…)
[x] Recents per-graph (keyed by kg+topic); invite copies kg
[x] PSTN mapping (Twilio) — inbound/status webhooks wired
    • [x] FastAPI router (/api/voice/inbound, /api/voice/status)
    • [x] HMAC signature verify + DEV_ALLOW_UNVERIFIED toggle
    • [x] Map E.164 → WA; post ring/status to /api/glyphnet/tx
    • [~] Number→graph routing (prefix map/env toggles)
    • [ ] Telnyx adapter + <Dial><Client> bridge to WebRTC
[x] Name service rules (display name ↔ WA/WN)
 • [x] Alias table + strict canonicalization (strip punctuation, casefold, collapse spaces)
 • [x] Persist best-known label per WA (address book de-dupe)
[x] Recents de-duplication by canonical WA (one row per kg:topic)

PTT / Walkie-Talkie over GlyphNet
[x] UI: press-and-hold mic in Chat composer (icons only)
[x] Mic capture → Opus via MediaRecorder (webm/ogg)
[x] Capsule schema: voice_frame { channel, seq, ts, mime, data_b64 }
[x] Playback: enable-audio toggle + volume slider
[x] Input level meter; mic picker & device refresh
[x] Persist recents on send (rememberTopic(topic, label, graph))
[x] Floor control: entanglement_lock “voice/”
[x] Echo de-dup + optimistic→server replacement (preserve from)
[ ] (Optional) E2EE: X25519 DH → AES-GCM (rolling nonce via seq)

Metrics
[x] RTT echo (meta.t0) & client RTT capture
[x] Chunk loss counters (recv/lost) tracked per topic/channel
[x] Show chunk loss % in UI/footer (lost / (lost + recv))

Voice Notes (async voice messages)
[x] Backend /tx: voice_note branch (canonical msg_id, publish, thread log)
[x] Record/attach → voice_note capsule (.ogg/.m4a/.webm etc.)
[x] File picker accepts: .webm, .ogg, .mp3, .m4a, .wav, .aac, .flac
[x] Playback UI with seek inside chat bubbles
[x] (Optional) Transcription → text capsule
 • [x] Client: “Transcribe on attach” toggle + post glyphs after transcript (with engine + transcript_of meta)
 • [x] Backend: POST /api/media/transcribe → { text } (stub-friendly; faster-whisper/whisper if available)

Full Calls (WebRTC media; GlyphNet signaling)
[x] Signaling capsules: voice_offer / voice_answer / ice
• [x] RX intercept in WS merge (offer/answer/ice) + call state refs (callIdRef, pcRef, callState)
• [x] TX: sendOffer / sendAnswer / sendIce over /api/glyphnet/tx
• [x] RTCPeerConnection factory (makePeer) + SDP plumbing (onLocalDescription/ICE hooks)
• [x] Fallback packed signaling (~SIG- base64url) with packSig/unpackSig and render-suppression
• [x] Extra capsules: voice_cancel / voice_reject / voice_end + full handlers
• [x] Busy-offer protection (reject competing call_ids; ignore self-offers)
• [x] ICE send path centralized (only via onLocalIce); UI shows last cand type

	•	Media: SRTP w/ AEC/AGC, jitter buffer
• [x] SRTP (implicit via WebRTC)
• [x] Capture constraints: AEC/AGC/NS enabled for mic
• [ ] Custom jitter buffer (not needed yet; consider for PTT low-latency)
	•	NAT: STUN list + TURN fallback
• [x] STUN list (DEFAULT_ICE)
• [x] TURN fallback + config UI (IceSettings + /api/rtc/ice load + local override)
	•	Call UI: ring / accept / decline / mute / hold
• [x] Ring/Accept/Decline/Hang up strips
• [x] Mute (toggle track.enabled)
• [x] Hold/Resume (RTCRtpSender.replaceTrack(null|track))
• [x] Accept bug fix + state guards (pendingOfferRef)
• [x] Call timer + local/remote “📞 Call ended” summary bubble
• [x] Ring tone play/pause tied to state
• [x] Hangup sends voice_end; decline sends voice_reject; cancel handled
• [x] Outbound cancel button + voice_cancel (UI + handler)
	•	(Optional) E2EE via Insertable Streams; keys via GlyphNet
	•	P4 • Modes & Policy (IP ↔ RF)
• [x] Transport mode switch (Auto / Radio-only / IP-only)
• [x] Settings toggle + persisted policy (localStorage: gnet:transportMode)
• [x] Status pill: {auto, radio-only, ip-only} + health of :8787 (onRadioHealth)
• [x] Router: honor policy in all fetch/WS calls (HTTP via transportBase; WS via glyphnetWsUrl)
	•	Radio / Mesh Transport (dual-band)
Phase 1 — MVP fallback (keeps working if internet dies)
• [x] Local Radio Node (127.0.0.1:8787)
• [x] Endpoints: /health, /api/glyphnet/tx, /ws/glyphnet (echo + forward)
• [x] In-mem outbox queue + retry (store-carry-forward stub)
• [x] Frame bridge: IP capsule ↔ RF frame (HTTP + WS → enqueueRF/encodeFrame)
	•	[ ] TransportSelector: prefer local RF → fallback IP (auto choose)
• [x] Frontend health probe (:8787/health, 2–5s backoff) + sticky choice (onRadioHealth)
• [x] HTTP multiplexer: cloud vs radio-node via transportBase (wired in ChatThread)
• [x] WS multiplexer: route WS to radio-node when healthy (useGlyphnet → glyphnetWsUrl)
• [x] Telemetry counters for RF/IP sends + failures in footer (postTx wired; footer shows rf_ok/rf_err/ip_ok/ip_err)
• [x] Route all sends through postTx (sendSignal, onPickVoiceFile, transcribeOnAttach swapped)
	•	Frame schema & guardrails
• [x] Frame: { topic, seq, ts, codec?, bytes } (binary payload) + encoder (encodeFrame, nextSeq)
• [x] Guardrails from band_profile (MTU, send-rate) — paced queue (RATE_HZ) + MTU-aware fragmentation
• [x] Enforce max capsule size in Local Radio Node (MAX_RF_INGRESS_BYTES)
• [x] Backend ingress guardrails (glyph count / plaintext size) in glyphnet_router
• Polish
• [x] Call history rollup: aggregate “📞 Call ended …” into daily sections
• [x] RF profile pill in UI (profile • MTU @ RATE_HZ • Q) via /health polling

Polish
[x] Call history rollup: aggregate “📞 Call ended …” into daily sections

Legend:
[x] done [~] partially done / wired on one path [ ] todo

Phase 2 — Real RF path

[x] Accessory radio bridge
 • Path-bound WS /ws/rflink with token auth (query + Bearer header + X-Bridge-Token)
 • Single-active-bridge policy (upgrade-mux build: refuse with 1013 “busy”; path-bound build: supersede old with 1000 — enforced)
 • RF pacing + fragmentation (MTU-aware, RATE_HZ tick; rfQueue → rfOutbox → bridge, tick nudges bridge)
 • Immediate enqueue kick (kickRFStep) so frames ship without waiting for first tick
 • Bridge hello handshake ({“type”:“hello”,”mtu”,”rate_hz”})
 • Keepalive pings on bridge (reduces 1006 idle closes)
 • RX fanout → (rf) capsule broadcast on /ws/glyphnet rooms
 • [x] Serial line Link/PHY driver (TTY): ASCII Base64 line mode + JSON line {topic,bytes_b64}; env RF_SERIAL_DEV/BAUD; drains outbox on open; listed in /bridge/transports as kind:"serial"
 • [x] Link/PHY driver abstraction (pluggable modules) — registry + ws-bridge + serial + mock; drains via drainOutboxViaDrivers(); /bridge/transports status endpoint
 • [x] Token handoff hardening — supports dev plain token OR signed auth; X-Bridge-Sig (v1,<ts>,HMAC_SHA256), clock-skew tolerance, RADIO_BRIDGE_TOKEN_NEXT rotation; REQUIRE_BRIDGE_SIG env to enforce; works for WS (/ws/rflink) & REST (/bridge/tx); CORS allows X-Bridge-Sig
 • [x] Band profile guardrails (ACTIVE {MTU,RATE_HZ}; MAX_RF_INGRESS_BYTES enforced; /health reports profile/active)
 • [x] Bridge control endpoints: /bridge/health & /bridge/tx (tokened), MTU/rate mirrored, size guardrails
 • [x] WS upgrade mux routes: /ws/glyphnet, /ws/rflink, /ws/ghx (+ GHX heartbeat; container info stub)

[~] Store-carry-forward
 • [x] Disk spool on Radio Node: RN queue persistence + TTL/caps + reload
 • [x] RX “seen” markers persisted; (topic,seq) de-dupe enforced on RX (when seq provided)
 • [ ] Opportunistic relay when peers appear

[x] Discovery (basic)
 • Beacon frame on RF (control:beacon JSON; MTU-fit, periodic)
 • Neighbor table with TTL + /discovery/neighbors endpoint (captures id/profile/rate/mtu/UA; TTL pruning)

⸻

Phase 3 — Nice-to-have

[ ] Desktop LAN P2P (WebRTC DataChannel; #/p2p route) as offline hop
[ ] Multi-hop mesh policy (region guardrails + TTL)
[ ] Radio diagnostics panel (RSSI/SNR, queue depth, duty-cycle)

⸻

Security / E2EE (Radio path)

[ ] Session keys: X25519 DH → AES-GCM (nonce = seq)
[ ] Key derivation per-topic; rotate by interval/frames
[ ] Optional: key exchange via GlyphNet (when IP available), else pre-shared

Security / E2EE (App path — QKD)

[x] Dev QKD shim on radio-node (/qkd/lease, /qkd/health)
[x] Vite proxy for /radio/qkd + /radio/* to :8787 (WSS/HTTP)
[x] Frontend getLease via gateway (/radio/qkd/lease) — qkd_cache.ts updated
[x] Fetch path encryption (POST /api/glyphnet/tx) + RX decrypt in WS merge (glyphs/voice)
[x] Sender identity hint on TX (meta.localWA) and recipient echo (meta.recipient)
[x] Lease fetch + AES-GCM/PBKDF2 utils in lib/qkd.ts
[x] Proxy to real QKD agent (QKD_AGENT env; proxy routes live — go-live is operational swap)

⸻

Developer UX & Tests

[~] “Radio healthy” toast + reconnection logic (WS “reconnecting…” + health pill present; dedicated “radio healthy” toast not yet)
[~] RF/IP path injectors in DevTools — server endpoints live: /dev/rf/mock/status|enable|disable|rx (UI hooks pending)
[ ] Offline kill-switch test plan (unplug WAN; verify chat/PTT over RF)

⸻

Documentation

[ ] README: run Local Radio Node + cables (WebUSB/Serial)
[ ] band_profile authoring guide + compliance notes

⸻

Telemetry & Receipts

[x] Delivery acks for media chunks (present in Outbox; server acks include msg_id/delivered)
[x] Basic talk-time counters (sessions, talkMs, grants/denies)
[x] Per-topic PTT session panel (last 10) + totals (persisted)
[ ] Dropout/error logs surfaced in UI

⸻

Performance Targets (guardrails)

[ ] PTT e2e: 250–400 ms (200 ms chunks baseline)
[ ] Low-latency path: 20 ms Opus frames (<250 ms target)
[x] Max capsule size + send rate limits per band_profile (pacing + MAX_RF_INGRESS_BYTES checks live)


[x] FastAPI CORS for Codespaces/Vercel + regex allow; ALLOW_ALL_CORS override
[x] Vite proxy for /api and /ws in dev
[x] WebSocket paths verified; Codespace port made public (fixed “offline”)
[x] Per-graph topic keying for thread store & history fetch
[x] Settings gear: consolidate audio enable/volume/mic into dropdown (UI polish)
[x] Single upgrade router for all WS paths (/ws/glyphnet, /ws/rflink, /ws/ghx)

Telemetry & Receipts
	•	⬜ Outbox queue + retry for failed /api/glyphnet/tx posts, with a “pending” indicator on bubbles.
	•	⬜ Footer metrics surfacing: show RTT avg/last and send failures/retries in the tiny status line.

Voice Notes (UX)
	•	⬜ Unified attach flow (📎 and 🎵 share the same picker/validator).
	•	⬜ Drag-and-drop onto the composer for audio files.
	•	⬜ Size guard (e.g., 12–16 MB) with a friendly error.

Reliability
	•	⬜ Cross-tab self-echo guard (extra hash/seen-id so the same message from another tab can’t double-render).


***********************KNOWLEDGE GRAPH & BROSWER INTEGRATION***************************************************
P5 • Knowledge Graph (Personal/Work) — Browser Integration

K0 • Scope & Partitioning
	•	Per-user, per-graph partitioning: two logical stores kg=personal and kg=work (hard boundary; no cross-leaks).
	•	Entity namespace policy: every node/edge keys include {kg, ownerWA} for multi-device merge without collisions.
	•	Container topology: one KG Container per graph (dc_kg_personal, dc_kg_work) + optional satellite atoms for high-volume streams (Visits, Voice, Files).

K1 • Data Model (v1 schema)
	•	Core entities
	•	Agent(id, label, device?)
	•	Topic(wa, realm, label)  // WA/WN thread target
	•	Thread(id, kg, topic)    // synthetic, 1:1 with (kg, topic)
	•	Message(id, ts, kind=text|voice|mail|signal, size?, mime?, transcript_of?)
	•	Attachment(id, file_id, mime, size, sha256)
	•	Call(id, ts_start, ts_end?, state, ice_type?)
	•	PTTSession(id, ts, dur_ms, acquire_ms?, granted)
	•	FloorLock(id, ts, result, acquire_ms)
	•	Visit(id, ts, uri, host, title?, referrer?, duration_s?)  // wormhole history
	•	Cookie(id, ts, key, value_hash, scope, expires?, policy)   // “habits” ledger, privacy-safe
	•	File(id, name, mime, size, sha256, versions[], location)
	•	ContainerRef(id, container_id, kind=atom|dc, path?)        // binds runtime to KG
	•	Edges (typed)
	•	SENT_BY(Message→Agent), ON_TOPIC(Message→Topic), IN_THREAD(Message→Thread)
	•	HAS_ATTACHMENT(Message→Attachment→File)
	•	PART_OF(Call→Thread), HELD_BY(FloorLock→Agent)
	•	OBSERVED_FOR(Cookie→Agent|Thread), VISITED_BY(Visit→Agent)
	•	ABOUT(ContainerRef→Thread|Topic)
	•	Indices
	•	{kg, thread_id, ts}, {kg, topic.wa}, {kg, file.sha256}, {kg, host}, {kg, cookie.key}

K2 • Storage Engines & APIs
	•	Backend KG writer façade (wraps your knowledge_graph_writer.py):
	•	POST /api/kg/events  → append-only batch ingest
	•	GET  /api/kg/query   → graph slice (filters: kg, thread, entity, time window)
	•	POST /api/kg/upsert-entity (optional) → idempotent identity updates
	•	Pluggable backends
	•	Default: SQLite/duckdb + property graph tables (portable)
	•	Adapter: Neo4j / Memgraph (opt-in)
	•	Local cache: IndexedDB mirror per graph for offline reads

K3 • Browser Emitters (zero-UI-change drop points)
	•	ChatThread.tsx
	•	After sendText() success → event:{type:"message", kind:"text", thread, ts, size, enc?}
	•	After sendVoiceNoteFile() → event:{type:"message", kind:"voice", mime, size}
	•	sendVoiceFrame() (PTT) → event:{type:"ptt_frame"} batched → PTTSession on release
	•	Floor locks: on grant/deny → event:{type:"floor_lock", acquire_ms, granted}
	•	Calls: state transitions (offer|answer|connect|end|reject|cancel) → event:{type:"call", state}
	•	Transcription path: when transcript posted → event:{type:"message", kind:"text", transcript_of}
	•	WormholeBar / Router
	•	On navigation resolve → event:{type:"visit", uri, host, title}
	•	On dwell/close → update duration_s
	•	KG Drive hooks (re-use your Drive plan)
	•	On file upload/download/share → event:{type:"file", action, file_id, sha256, size}
	•	Cookies/Habits Ledger (privacy-safe)
	•	Record keys + hashed values with scope & expiry; never store raw secrets.
	•	Toggle in Settings: “Allow AI memory of habits (per graph)”.

K4 • Container Runtime ↔ KG Bridge
	•	GlyphRuntime events → KG (glyph_execution, glyph_replay, container_collapsed, SoulLaw):
	•	Map to ContainerRef, Message(kind="runtime_log"), SoulLawEvent (if you keep it), edges to threads/agents when relevant.
	•	Entanglement: when fork_entangled_path creates a container, emit edge: ABOUT(ContainerRef→Thread) for the originating thread.

K5 • Query, Search & Summarization
	•	Thread hydration: Chat fetches via /api/glyphnet/thread AND augments from KG for:
	•	attachments list, call summaries, PTT rollups (no extra round-trips later).
	•	Cross-thread search: /api/kg/query?q=...&kg=... full-text over Message/Visit/File.name.
	•	AION memory reads: GET /api/kg/view/memory?kg=personal&scope=habits|topics|people (pre-joined aggregates).

K6 • Privacy, Retention, Governance
	•	Per-graph retention policies (defaults):
	•	Messages: 18 months; Voice frames: 90 days; Cookies/Habits: per-item expiry; Visits: 12 months.
	•	Redaction & “Forget”
	•	POST /api/kg/forget (entity set or time window); tombstone edges; cascade to local IndexedDB.
	•	Consent surfaces
	•	Settings toggles per graph: Store visits, Store habits, Store transcripts, Encrypt at rest only.
	•	Audit trail
	•	Append-only Mutation Ledger (hash-chained) for KG writes (no payload; just envelope metadata).

K7 • Sync & Offline
	•	IndexedDB mirror per graph: gnet_kg_{kg}
	•	Write-through on event POST; read-through for KGDock, Inbox summaries.
	•	Compaction window + LRU pages per thread.
	•	Reconciliation
	•	Cursor-based GET /api/kg/query?after=; idempotent re-apply by event_id.

K8 • UI Surfaces
	•	KG Dock v2
	•	Tabs: Timeline, Graph, Files, Visits, Habits
	•	Thread context pill (topic, kg); filters & time range
	•	Graph view
	•	Mini D3 canvas: Topic ↔ Messages ↔ Attachments ↔ Calls; hover to reveal props.
	•	Privacy banner (per graph): show active policies + “Pause memory” quick toggle.
	•	Visit history panel with host aggregates; “Clear last hour/day” actions.

K9 • Security & Crypto
	•	At-rest encryption of KG rows (server) with per-user keys (works with your Vault model).
	•	No plaintext for sensitive Cookie values; store salted hashes + entropy budget.
	•	QKD hooks: allow enc={kid, iv} metadata on KG events when encrypting payloads (aligns with your QKD plan).

K10 • Telemetry & Tests
	•	Counters: kg_ev_ok/err, kg_cache_hits, kg_sync_conflicts, kg_forget_ops, privacy_paused_min.
	•	Tests:
	•	Event idempotency & merge
	•	Partition isolation (personal vs work)
	•	Offline/online flaps
	•	Forget/redaction correctness
	•	AION query correctness (aggregates)

K11 • Migration & Acceptance
	•	One-shot migrate existing thread/session caches → KG (messages, voice notes, call summaries).
	•	Backfill visits from current hash router history (if stored).
	•	Acceptance
	•	Switching between Personal/Work shows different KG surfaces immediately.
	•	New chats/voice/calls/visits appear in KG Dock within 1s.
	•	Clearing “habits” or “last day of visits” reflects in UI and AION memory.
	•	Export of a thread includes message + file graph slice.

⸻

Minimal glue (so it’s easy to implement)

Backend (FastAPI/Flask-ish)

POST /api/kg/events
# body: { kg:"personal|work", owner:"ucs://…", events:[{type, ts, thread_id, payload…}] }
# 200 → { ok:true, applied:N, last_event_id }
GET  /api/kg/query?kg=personal&thread_id=…&after=…&limit=…
# 200 → { nodes:[…], edges:[…], next_cursor }

Frontend emit helper
Add emitKg(kg, events[]) and call it in:
	•	sendText, sendVoiceNoteFile, sendVoiceFrame (on release), floor-lock grant/deny, call state transitions, transcript sent, file uploaded, wormhole visited.

IndexedDB keys
	•	DB: gnet_kg_{kg}
	•	Stores: events (by event_id), nodes, edges, views:{thread_id -> summary}

⸻

What this unlocks for you (short version)
	•	Clean separation Personal vs Work memory (and easy future “Family”, “Org”, etc.).
	•	AION can read structured memory (habits, visits, files, contacts) with explicit consent.
	•	Browser acts like WhatsApp/Email plus “Drive” and “History”, all in one KG—searchable and summarizable.
	•	Container Runtime events become first-class knowledge (entanglement and ethics logs are no longer siloed).

If you want, I can draft the small emitKg(...) utility and the event payload shapes for the exact React functions you’ve already got (sendText, sendVoiceFrame, etc.) so you can paste them straight in.


-----
What to do now (no UI yet)
	1.	Device/local identity
	•	Generate an Ed25519/X25519 keypair on first run.
	•	Derive:
	•	AGENT_ID = sha256(pubkey)[:16] (replace the hardcoded one)
	•	WA = ucs://self/<pubkey-fp> (or wave.tp/<fp>) for display/routing.
	•	Persist private key in:
	•	Tauri: OS keychain; Web-only: IndexedDB (encrypted) + backup export.
	2.	Use identity everywhere
	•	Headers: keep X-Agent-Token: dev-token for dev, but add X-Agent-Id: <AGENT_ID> (you already do) and optionally a request signature header of the body (HMAC w/ device key or Ed25519) for future-proofing.
	•	KG events: include { owner: WA, kg: personal|work }.
	•	Floor locks / call state: use owner = AGENT_ID (you already do—just source it from the identity module).
	3.	Partition data by owner + graph
	•	DB/IndexedDB keys: prefix with {owner, kg}.
	•	Thread store, files, visits, “habits” all use that prefix.
	4.	Add a tiny Settings → Identity panel
	•	Show Your address (WA), copy buttons, and Export/Import Identity (JSON/QR).
	•	That’s enough to move data across devices until account auth lands.

Minimal TS util (drop-in)

// src/utils/identity.ts
import { subtle } from "./crypto"; // or window.crypto.subtle

const KEY_DB = "gnet:identity:v1";

export type AgentIdentity = {
  agentId: string;        // short fingerprint
  wa: string;             // ucs://self/<fp>
  pubkey_b64: string;
  privkey_b64?: string;   // keep outside localStorage if Tauri keychain is used
};

export async function getIdentity(): Promise<AgentIdentity> {
  const cached = localStorage.getItem(KEY_DB);
  if (cached) return JSON.parse(cached);

  const kp = await window.crypto.subtle.generateKey(
    { name: "Ed25519", namedCurve: "Ed25519" } as any, true, ["sign", "verify"]
  );
  const pub = new Uint8Array(await subtle.exportKey("raw", kp.publicKey));
  const priv = new Uint8Array(await subtle.exportKey("pkcs8", kp.privateKey));

  const fpBuf = await subtle.digest("SHA-256", pub);
  const fp = Array.from(new Uint8Array(fpBuf)).slice(0, 16)
                   .map(b => b.toString(16).padStart(2, "0")).join("");
  const wa = `ucs://self/${fp}`;

  const id: AgentIdentity = {
    agentId: fp,
    wa,
    pubkey_b64: btoa(String.fromCharCode(...pub)),
    privkey_b64: btoa(String.fromCharCode(...priv)), // move to keychain in Tauri
  };
  localStorage.setItem(KEY_DB, JSON.stringify(id));
  return id;
}

Then wire it:
	•	ChatThread: replace the current AGENT_ID source with const { agentId } = await getIdentity().
	•	Headers: keep X-Agent-Id: agentId.
	•	KG emit: include { owner: wa } on all events.

Later, when you add login
	•	Add /api/auth/exchange that verifies a device-proof (Ed25519 sig of a server nonce) and returns a session token; map ownerWA → account.
	•	Keep all KG keys the same (owner + kg). Multi-device just means multiple devices prove the same owner and share/sync.
	•	Optional: “Link device” by scanning a QR containing the owner’s public key + a one-time server nonce.

TL;DR


***********************KNOWLEDGE GRAPH & BROSWER INTEGRATION***************************************************

Conversation Persistence & History (Thread Storage + Pagination)

[ ] Persistent thread storage per kg:topic
• [ ] Backend: /api/glyphnet/thread supports cursor pagination (limit, before, after)
• [ ] Index by {kg, topic, ts, id}; return next_cursor/prev_cursor
• [ ] Store inbound/outbound uniformly (voice_note, voice_frame, text, signaling filtered)

[ ] Client caching (survives navigation/reload)
• [ ] Migrate sessionStorage → IndexedDB (gnet_threads) with per-thread LRU window
• [ ] Keep N newest messages in memory; hydrate older via “Load older”
• [ ] De-dupe by id and by content signature (existing logic reused)

[ ] UI/UX
• [ ] Infinite-scroll “Load older” on scroll-top + spinner + sticky day dividers
• [ ] “Jump to latest” button when user is scrolled up
• [ ] Empty-state + skeletons; show approximate count if known

[ ] Sync & retention
• [ ] Soft cap per thread (e.g., 20k items) with rolling compaction in IndexedDB
• [ ] Background prefetch next page when user pauses scrolling
• [ ] Export thread to JSON (.gnetthread)

Acceptance
• Switch away from a thread returns later with history intact.
• Scrolling up reliably loads older pages; no dupes; memory stays bounded.

⸻

Wormhole Mail (Email-style Composer & Delivery)

[ ] Schema & capsules
• [ ] mail_send capsule: { to[], cc[], bcc[], subject, text, html?, attachments[], signature? }
• [ ] mail_delivery/mail_status events: queued/sent/delivered/failed + provider ids
• [ ] Map kevin@wave.tp to WA/WN via name service (kg-aware)

[ ] Backend
• [ ] POST /api/mail/send → returns { message_id }
• [ ] Attachment upload: POST /api/mail/upload → { file_id, mime, size, sha256 }
• [ ] Store mail in thread log + a Mailbox collection (Inbox/Sent/Drafts)
• [ ] Provider adapter (stub first): local echo → later SMTP/SendGrid/Twilio Email
• [ ] Signature templates per graph; DKIM/SPF later if bridging to real email

[ ] Client
• [ ] “Chat ↔ Mail” tab toggle in composer
• [ ] Fields: To, Cc, Bcc, Subject, Attach, Signature picker, Rich-text (basic)
• [ ] Draft autosave; send as mail_send + thread summary bubble
• [ ] Render inbound mail bubbles (subject header + attachments preview)

[ ] Security & rate limits
• [ ] Size caps per message/attachment; total send rate per user
• [ ] Blocklist/allowlist; HTML sanitization for inbound html

Acceptance
• Can compose & send a mail-style message to a WA, see it log in thread + Sent.
• Inbound mail events render with subject/attachments.

⸻

“KG Drive” — Document Vault per Graph (Dropbox-like)

[ ] Storage & metadata
• [ ] Buckets per graph: kg=personal|work
• [ ] File table: { file_id, name, mime, size, sha256, versions[], created_by, updated_at, acl }
• [ ] Versioning (append-only); server-side SHA-256 verification

[ ] API
• [ ] POST /api/files/upload (resumable or simple first)
• [ ] GET /api/files/list?kg&path&cursor&limit
• [ ] GET /api/files/download?file_id (signed URL if external store)
• [ ] POST /api/files/move|rename|delete
• [ ] Share link: POST /api/files/share → returns share token (kg-scoped ACL)

[ ] UI
• [ ] “Drive” panel per graph: folders, sort, search, previews (audio/image/text/pdf)
• [ ] Quick-save from chat attachment → choose graph/folder
• [ ] File details (versions, who shared, where used)

[ ] Integrations
• [ ] Link into thread as attachment cards
• [ ] Drag-drop upload from thread composer

Acceptance
• Can upload, list, download, version, and share a file in personal/work graphs; clickable cards appear in chat.

⸻
*******************************Photon Secure Glyph Document*************************************************
Photon Secure Glyph Document (.pgdoc) — Encrypted, Share-by-Registry

[ ] File format & crypto
• [ ] New container .pgdoc (zip or CBOR bundle):
manifest.json (title, authors, created_ts, algs, chunk map)
payload.bin (glyph stream or photon source)
sig.bin (author signature)
• [ ] Crypto: X25519 key exchange → AES-GCM content-key; per-chunk nonce
• [ ] Document Key Registry: map { doc_id → [allowed_public_keys] } with audit log

[ ] APIs
• [ ] POST /api/pgdoc/create (returns doc_id, share link)
• [ ] POST /api/pgdoc/grant|revoke (add/remove public keys)
• [ ] GET /api/pgdoc/open?doc_id (server streams encrypted; client decrypts)
• [ ] Optional: server-side re-wrap key for new recipients without re-encrypting payload

[ ] Photon editor integration
• [ ] Export to .pgdoc (compile photon → glyphs → encrypt)
• [ ] Open .pgdoc if user has key; error toast if not in registry
• [ ] “Lock” toggle (read-only mode akin to PDF)
• [ ] Watermarking & signature verification UI

[ ] UX & failure modes
• [ ] Clear errors for “no access”, “key mismatch”, “tampered”
• [ ] Offline open if key+blob cached locally

• [ ] sign the document like docusign
• [ ] make payment to a document / contract
• [ ] Docusign features
• [ ] document edits track changes (legal type docs)

Acceptance
• Create a .pgdoc, grant another user, they can open; revocation blocks further opens; signatures verify.

*******************************Photon Secure Glyph Document*************************************************
*******************************Q QUANTUM KEY DISTRIBUTION*************************************************
flowchart TD
    %% QKD Integration – Build Tasks & Key Notes
    %% Status tags: [ ] todo · [~] in-progress · [x] done

    A0([QKD Integration – Overview\nGoal: App-layer encryption of GlyphNet payloads + WebRTC IS\nKeys sourced from local QKD agent; server sees ciphertext only])

    subgraph S1[Core Plumbing]
      A1[[ [ ] QKD Agent Contract ]]
      note right of A1
        Define browser-facing lease API:
        lease({localWA, remoteWA, kg, purpose, bytes}) -> {kid, key, ttl_ms}
        Transport: localhost IPC/HTTP via radio-node proxy.
        No plaintext keys persisted; in-memory only.
      end

      A2[[ [ ] Browser Shim: qkd.ts ]]
      note right of A2
        Thin client that calls the agent, caches leases per
        (purpose|kg|local|remote), exposes qkdLease().
        Replace dev stub when you provide real QKD files.
      end

      A3[[ [ ] Crypto Wrapper: crypto_qkd.ts ]]
      note right of A3
        AES-GCM w/ per-message IV, HKDF on QKD blocks for subkeys.
        Helpers: qkdEncrypt()/qkdDecrypt() + ivFromSeq(kid, seq).
      end

      A1 --> A2 --> A3
    end

    subgraph S2[Payload Encryption (GlyphNet)]
      B1[[ [ ] Text: encrypt glyphs ]]
      note right of B1
        sendText(): UTF-8 -> qkdEncrypt(purpose:"glyph", seq++)
        Replace capsule.glyphs with glyphs_enc_b64 + enc {scheme,kid,seq,iv_b64,aad:"glyph"}.
      end

      B2[[ [ ] Voice Note: encrypt data_b64 ]]
      note right of B2
        sendVoiceNoteFile(): base64 bytes -> qkdEncrypt("voice_note", seq++)
        Use field data_enc_b64 (or reuse data_b64) + enc {..., aad:"voice_note"}.
      end

      B3[[ [ ] PTT Frames: encrypt data_b64 ]]
      note right of B3
        sendVoiceFrame(): per-channel seq -> qkdEncrypt("voice_frame", seq++)
        Add enc {..., aad:"voice_frame"}. Keep existing channel/seq for loss calc.
      end

      B1 --> B2 --> B3
    end

    subgraph S3[Receive Path]
      C1[[ [ ] WS Merge: decrypt if enc present ]]
      note right of C1
        In normalize/merge: detect capsule.enc, choose purpose by payload type,
        call qkdDecrypt(). On failure, show "Locked/Decrypt failed" chip (no crash).
      end

      C2[[ [ ] Back-compat ]]
      note right of C2
        If no enc field → treat as plaintext (dev/interop).
        Prefer enc when both present.
      end

      C1 --> C2
    end

    subgraph S4[WebRTC (Insertable Streams)]
      D1[[ [ ] Feature Flag: qkdE2EE ]]
      D2[[ [ ] Sender Transform ]]
      D3[[ [ ] Receiver Transform ]]
      note right of D2
        Attach transforms to audio sender; frame counter as seq.
        Derive subkey for purpose:"call".
      end
      note right of D3
        Mirror decrypt on receiver; handle re-key events gracefully.
      end
      D1 --> D2 --> D3
    end

    subgraph S5[Key Policy & Rotation]
      E1[[ [ ] Rekey triggers ]]
      note right of E1
        Rotate on: time (e.g., 10 min) OR N messages/frames OR reconnect.
        Update kid; bump lease; notify peer via control glyph (optional).
      end
      E2[[ [ ] Nonce/Seq rules ]]
      note right of E2
        Per-purpose monotonic seq; include in AAD.
        IV 12B; ensure uniqueness per kid.
      end
      E3[[ [ ] Storage & Scrub ]]
      note right of E3
        No key material in logs, storage, or thread cache.
        Zeroize temp buffers when feasible.
      end
      E1 --> E2 --> E3
    end

    subgraph S6[Fallback & UX]
      F1[[ [ ] Policy when QKD unavailable ]]
      note right of F1
        Modes: {deny send | classical E2EE fallback | warn & allow}.
        Default: warn & allow during dev; configurable per KG.
      end
      F2[[ [ ] Error surfacing ]]
      note right of F2
        Display small lock+warning chip on failed decrypt;
        keep raw event hidden to avoid leaking plaintext.
      end
      F1 --> F2
    end

    subgraph S7[Telemetry, Tests, Compliance]
      G1[[ [ ] Counters ]]
      note right of G1
        __tele: enc_ok/enc_err/dec_ok/dec_err, kid_rotations, qkd_lease_fail.
      end
      G2[[ [ ] Test Matrix ]]
      note right of G2
        Plain ↔ Enc interop, rekey mid-stream, replay window,
        wrong-kid rejection, packet loss + PTT seq gaps.
      end
      G3[[ [ ] Threat notes ]]
      note right of G3
        Confidentiality from QKD keys; integrity via GCM tag;
        metadata (topic, kg, timing) still observable.
      end
      G1 --> G2 --> G3
    end

    %% Dependencies
    A3 --> B1
    A3 --> B2
    A3 --> B3
    B1 --> C1
    B2 --> C1
    B3 --> C1
    A2 --> D1
    A3 --> D2
    A3 --> D3

    Quick implementer notes (for future you)
	•	Drop points (no UI change):
	•	sendText, sendVoiceNoteFile, sendVoiceFrame: call qkdEncrypt(...) and swap fields as shown.
	•	WS merge (useGlyphnet/ChatThread normalize): decrypt when capsule.enc exists.
	•	WebRTC: gate with featureFlags.qkdE2EE.
	•	Agent handoff: When you send me the QKD files, we’ll replace the stub in qkd.ts with the real agent binding and keep the rest of the surfaces unchanged.


*******************************Q QUANTUM KEY DISTRIBUTION*************************************************

mindmap
  root((GlyphNet Build Checklist))
    P0 • Foundations
      [ ] Mono-repo scaffolding
        [ ] apps/packages
        [ ] CI (lint/test/build)
        [ ] release tags
      [ ] Security baseline
        [ ] signed commits
        [ ] SAST / dep scan
        [ ] secrets policy
      [ ] Design system
        [ ] Tailwind tokens
        [ ] shadcn/ui kit
        [ ] iconography + motion
      [x] Spec registry
        [x] Protocol ADRs
        [x] GIP frames + Wormhole URI (🌀, .tp)
        [x] Resolver API (/api/wormhole/resolve) + client lib
      [ ] Container Hosting Model
        [ ] Edge runtimes + CAS snapshots (IPFS/Arweave/S3)
        [ ] On-chain anchors (names, versions, keys)
      [ ] Dual-Band Architecture Doc
        [ ] Mesh-first (GlyphNet/radio) → IP fallback (HTTPS/WS)
        [ ] Transport negotiation + policy

    P1 • Browser Shell (Tauri + React)
      [ ] B01 Tauri shell
        [ ] dev window (macOS)
        [ ] sandboxed renderer
        [ ] multi-window
        [ ] auto-updates
      [ ] B02 Runtime bridge
        [ ] WASM CodexCore
        [ ] Native addon for crypto/keys
        [ ] IPC to local UCS/AION
      [ ] B03 Vault + Keyring
        [ ] encrypted .dc mounts
        [ ] device keys in OS keychain
      [x] B04 Navigation model
        [x] 🌀 wormhole bar (+ www toggle)
        [x] dimension:// / ucs:// / glyph://
        [x] hash-router + title updates
        [x] enter→hash update (no refresh)
        [x] Inbox deep-link (#/inbox?topic=…)
        [ ] history graph
      [x] B05 Home (Personal Container)
        [x] AION panel (UI stub)
        [x] Wave Inbox (slide-over)
        [x] Knowledge Graph dock
        [x] ContainerView wiring (wormhole→container)
        [x] Quick Actions (inject/clear)
        [x] GHX feed panel
        [x] GlyphNet capsule feed (read-only)
        [x] Wave Inbox: WS subscribe (ucs://… topics)
        [x] Address Book: recent topics + Copy Invite
        [x] Outbox → POST /api/glyphnet/tx
        [x] Actions: Reverse (/api/photon/translate_reverse) & Execute
      [ ] B06 Dual-Band TransportSelector
        [ ] GlyphNet mesh if available
        [ ] fallback HTTPS/WS
        [ ] CAS snapshot loader
      [ ] B07 DevTools: Dimension Inspector
        [ ] glyph trace
        [ ] packet sniffer (GIP)
        [ ] time profiler
        [ ] memory map

    P2 • Core Runtime (CodexCore/Tessaris)
      [ ] C01 CodexCore engine (evaluator + scheduler + effects)
      [ ] C02 TessarisEngine (thought expansion + collapse)
      [ ] C03 TimeEngine (ratio, caps, watchdogs, per-tab dial)
      [ ] C04 GlyphExecutor (pipelines, streaming, cancel)
      [ ] C05 Memory/DNA + Knowledge Graph (store, ledger, GC)
      [ ] C06 Ethics/SoulLaw (rules, recovery, audits)

    P3 • Network & Protocols
      D01 GlyphNet Adapters
        [x] op:"capsule" TX path (validate + publish)
        [x] RX WebSocket feed /ws/glyphnet?topic=ucs://…
        [x] Dev override token + /api/glyphnet/ws-test
        [x] WS fallback fanout when bus has 0 subs
        [x] CORS allowlist (localhost + Codespaces)
        [x] Browser compose UI → POST /api/glyphnet/tx
        [x] Topic ACLs (per-recipient permissions) — env-driven prefix rules via config_acl.py
        [ ] Delivery acks/receipts
      D02 GIP (Glyph Internet Protocol)
        [x] frames/ops + REST (/api/gip/send, /api/gip/send/{id})
        [x] compression module present
        [ ] replay/resume
      D03 Wormhole Router
        [ ] intent → route, trust graph, retries/TTL, registry lookup
      D04 SoulLink Handshake
        [ ] container identity, mutual attestation, key rotations
      D05 Registry Service
        [x] base registries + resolver bridge
        [ ] address book (🌀*.tp)
        [ ] discovery cache
        [ ] pin/trust lists
      D06 QKD Messaging Hook
        [x] hook integrated (meta.qkd_required)
        [ ] fingerprints
        [ ] fallbacks
      D07 Transport Negotiation
        [ ] Mesh ↔ IP bridging, NAT traversal, CAS verification

MESSAGING BY  GLYPHS
mindmap
  root((Glyph-Only Messaging<br/>(Encode-at-Send, Decode-at-View)))
    Glyph Registry & Codec
      "[ ] Define registry format (/registry/glyphs.jsonl): {word, glyph, pos?, freq?, v}"
      "[ ] Implement codec lib: encodeGlyphs(text) → glyphTokens[]; decodeGlyphs(tokens) → text"
      "[ ] OOV strategy: char-level tokens + fallback dictionary updates"
      "[ ] Versioning: meta.glyphs_v added to every capsule"
      "[ ] Perf: cache hot tokens; measure encode/decode throughput"
    Wire Format & API
      "[ ] Enforce capsule.glyphs: string[] (no plaintext on wire)"
      "[ ] Backcompat: accept legacy text on RX → encode immediately → drop text"
      "[ ] Update de-dup signature to token-based"
      "[ ] txt|<tokens joined with '|'>|<floor(ts/5000)>"
      "[ ] Add registry version echo in server responses (drift detection)"
    Storage & Persistence
      "[ ] Local thread store writes glyph tokens only (strip text when persisting)"
      "[ ] Server thread log stores tokens + glyphs_v"
      "[ ] Index/search: transient decode index in memory when needed"
      "[ ] No-plaintext-at-rest flag ON (gnet:noPlainAtRest=1)"
    UI / UX
      "[ ] Composer accepts text; on Send → encode → POST glyphs"
      "[ ] Render path: decode tokens → display text"
      "[ ] Recent messages decode window (last N or T minutes)"
      "[ ] Settings toggle: Store plaintext locally (off by default)"
      "[ ] Footer badge shows glyphs_v + codec status (green/amber/red)"
    Transcription & Attachments
      "[ ] Transcribe → encode transcript to tokens before sending"
      "[ ] Voice-note captions optional: store tokens, render via decode"
    Security / E2EE (QKD-Ready)
      "[ ] Default: X25519 (or PQC: Kyber) KEM → AES-GCM/ChaCha20 per topic"
      "[ ] Key rotation policy (interval/msgs); nonce = seq"
      "[ ] Metadata: meta.enc_v, meta.key_epoch"
      "[ ] QKD interface (future): getQKDKey(topic); fallback to KEM"
      "[ ] At-rest: encrypted spool on Radio Node; no key material on disk"
      "[ ] Redaction: never log plaintext or decoded text"
    Metrics & Telemetry
      "[ ] Measure packet size savings (plaintext vs glyphs)"
      "[ ] Encode/decode latency histogram"
      "[ ] Drift alerts when glyphs_v mismatches client registry"
      "[ ] Counters: % OOV, avg tokens/msg, compression ratio"
    Migration
      "[ ] One-shot: convert legacy plaintext logs → glyph tokens (+ glyphs_v)"
      "[ ] Dual-read window: accept old msgs, encode on ingest, mark migrated"
      "[ ] Data retention: purge plaintext backups after verification"
    Tests
      "[ ] Unit: codec (round-trip, OOV, punctuation, RTL/CJK)"
      "[ ] Property: decode(encode(x)) == x for corpora"
      "[ ] Integration: enforce token-only on wire"
      "[ ] Security: no plaintext in storage/console/network captures"
      "[ ] Perf: ≥ 50k tokens/s on target devices"
    Documentation
      "[ ] README: glyph-only pipeline, flags, versioning"
      "[ ] Registry authoring guide; update & signing"
      "[ ] Security notes: E2EE, rotation, QKD hook, threat model"
    Feature Flags & Rollout
      "[ ] FF_GLYPH_ONLY_TX (gate transmit)"
      "[ ] FF_NO_PLAINTEXT_AT_REST (gate storage)"
      "[ ] FF_PQC_DEFAULT (use Kyber by default)"
      "[ ] Gradual rollout plan + kill switch"
      "[ ] Telemetry dashboard for adoption & savings"
    Acceptance Criteria
      "[ ] No plaintext on wire or at rest by default"
      "[ ] UI renders identically via on-the-fly decode"
      "[ ] Size/latency targets met; OOV < 2% on sample corpus"
      "[ ] Keys rotate per policy; decrypt/verify across rotations"
      "[ ] Backcompat migration without user-visible regressions"
***************************GLYPHNET BROWSER CHECKLIST******************************************

graph TD
%% ================== PHASE 0: FOUNDATIONS ==================
A0[🏁 P0 • Foundations]:::phase
A01[Mono-repo scaffolding\n• apps/packages\n• CI (lint/test/build)\n• release tags]:::task
A02[Security baseline\n• signed commits\n• SAST/dep scan\n• secrets policy]:::task
A03[Design system\n• Tailwind tokens\n• shadcn/ui kit\n• iconography + motion]:::task
A04[Spec registry\n• Protocol ADRs\n• GIP frames + Wormhole URI (🌀, .tp)\n• ✅ Resolver API (/api/wormhole/resolve) + client lib]:::task
A05[Container Hosting Model\n• Edge runtimes + CAS snapshots (IPFS/Arweave/S3)\n• On-chain anchors (names, versions, keys)]:::task
A06[Dual-Band Architecture Doc\n• Mesh-first (GlyphNet/radio) → IP fallback (HTTPS/WS)\n• Transport negotiation + policy]:::task
A0 –> A01 –> A02 –> A03 –> A04 –> A05 –> A06

%% ================== PHASE 1: BROWSER SHELL ==================
B0[🧭 P1 • AI-First Browser Shell (Tauri + React)]:::phase
B01[Tauri shell\n• dev window runs (macOS)\n• sandboxed renderer\n• multi-window\n• auto-updates]:::task
B02[Runtime bridge\n• WASM CodexCore\n• Native addon for crypto/keys\n• IPC to local UCS/AION]:::task
B03[Vault + Keyring\n• encrypted .dc mounts\n• device keys in OS keychain]:::task
B04[Navigation model\n• ✅ 🌀 wormhole bar (default) + www toggle\n• dimension:// / ucs:// / glyph://\n• ✅ hash-router + title updates\n• ✅ enter→hash update (no refresh)\n• ✅ Inbox deep-link (#/inbox?topic=…)\n• history graph]:::task
B05[Home (Personal Container)\n• ✅ AION panel (UI stub)\n• ✅ Wave Inbox (slide-over)\n• ✅ Knowledge Graph dock\n• ✅ ContainerView wiring (wormhole→container)\n• ✅ Quick Actions (inject/clear)\n• ✅ GHX feed panel\n• ✅ GlyphNet capsule feed (ContainerView, read-only)\n• ✅ Wave Inbox: WS subscribe (ucs://… topics)\n• ✅ Address Book: recent topics + Copy Invite\n• ✅ Outbox → POST /api/glyphnet/tx\n• 🔜 Actions: Reverse (/api/photon/translate_reverse) & Execute]:::task
B06[Dual-Band TransportSelector\n• GlyphNet mesh if available\n• fallback HTTPS/WS\n• CAS snapshot loader]:::task
B07[DevTools: Dimension Inspector\n• glyph trace\n• packet sniffer (GIP)\n• time profiler\n• memory map]:::task
A06 –> B0
B0 –> B01 –> B02 –> B03 –> B04 –> B05 –> B06 –> B07

%% ================== PHASE 2: CORE RUNTIME ==================
C0[🧠 P2 • Core Runtime (CodexCore/Tessaris)]:::phase
C01[CodexCore engine\n• evaluator + scheduler\n• effect system]:::task
C02[TessarisEngine\n• thought expansion\n• collapse operators]:::task
C03[TimeEngine (Container)\n• time_ratio\n• budget caps\n• watchdogs\n• per-tab Time Dial]:::task
C04[GlyphExecutor\n• pipelines\n• streaming outputs\n• cancellation]:::task
C05[Memory/DNA + Knowledge Graph\n• per-identity KG store\n• mutation ledger\n• compaction/GC]:::task
C06[Ethics/SoulLaw\n• allow/deny rules\n• recovery states\n• audit hooks]:::task
B02 –> C0
C0 –> C01 –> C02 –> C03 –> C04 –> C05 –> C06

%% ================== PHASE 3: NETWORK & PROTOCOLS ==================
D0[🌐 P3 • Network & Protocols]:::phase
D01[GlyphNet Adapters\n• radio/mesh transceiver\n• backpressure\n• auth tokens\n• ✅ op:"capsule" TX path (validate + publish)\n• ✅ RX WebSocket feed /ws/glyphnet?topic=ucs://…\n• ✅ Dev override token + /api/glyphnet/ws-test\n• ✅ WS fallback fanout when bus has 0 subs\n• ✅ CORS allowlist (localhost + Codespaces)\n• ✅ Browser compose UI → POST /api/glyphnet/tx\n• 🔜 Topic ACLs (per-recipient permissions)\n• 🔜 Delivery acks/receipts]:::task
D02[GIP (Glyph Internet Protocol)\n• ✅ frames/ops + REST endpoints (/api/gip/send, /api/gip/send/{id})\n• ✅ compression (module present)\n• replay/resume]:::task
D03[Wormhole Router\n• intent → route\n• trust graph\n• retries/TTL\n• registry lookup]:::task
D04[SoulLink Handshake\n• container identity\n• mutual attestation\n• key rotations]:::task
D05[Registry Service\n• address book (🌀*.tp)\n• ✅ base registries + resolver bridge\n• discovery cache\n• pin/trust lists]:::task
D06[QKD Messaging Hook\n• ✅ hook integrated (meta.qkd_required)\n• fingerprints\n• fallbacks]:::task
D07[Transport Negotiation\n• Mesh ↔ IP bridging\n• NAT traversal\n• CAS verification]:::task
C04 –> D0
D0 –> D01 –> D02 –> D03 –> D04 –> D05 –> D06 –> D07

%% ============ PHASE 4: DIMENSION RUNTIME UI (FRONTEND) ============
E0[🪟 P4 • Dimension Runtime UI]:::phase
E01[Dimension Renderer\n• dc schema → UI tree\n• slots: Prompt/GlyphGrid/Logs\n• ✅ v0: ContainerView resolves + connects GHX WS\n• ✅ GET /api/aion/container/{id} (dc JSON)\n• ✅ /ws/ghx/{id} + GHX bus broadcast\n• ✅ inject/save endpoints + live auto-refresh\n• ✅ Empty state + deep-link (#/container/{id})]:::task
E02[Prompt Bar v1\n• CodexLang input\n• tooluse palette\n• slash cmds]:::task
E03[Time Controls\n• live ratio dial\n• pause/step\n• budget presets]:::task
E04[GlyphGrid 3D\n• streams/tails\n• pin/share/export\n• diffs]:::task
E05[Inspector Overlays\n• ethics hits\n• memory writes\n• network traces]:::task
E06[Wave Composer\n• message/email merge\n• attachments (glyphs/photo)\n• QKD send]:::task
B05 –> E0
E0 –> E01 –> E02 –> E03 –> E04 –> E05 –> E06

%% ================== PHASE 5: SOULNET LAYER ==================
F0[🔒 P5 • SoulNet Social Layer]:::phase
F01[Encrypted Waves\n• container ↔ container\n• threaded intents\n• delivery receipts]:::task
F02[Sharing & Permissions\n• share dim pages\n• scopes/time-box\n• revoke]:::task
F03[Presence & Bonds\n• SoulLink bonds\n• trust levels\n• consent gates]:::task
F04[Inbox/Outbox\n• queued intents\n• summaries\n• recovery]:::task
D04 –> F0
F0 –> F01 –> F02 –> F03 –> F04

%% ================== PHASE 6: COMMERCE ==================
G0[🛒 P6 • CodexCommerce]:::phase
G01[Business Container Template\n• product_list.codex\n• offer_logic.glyph]:::task
G02[Intent Parser\n• buy/compare\n• constraints\n• scoring]:::task
G03[Marketplace Router\n• multi-offer fanout\n• trust/latency scores]:::task
G04[Checkout/Settlement\n• confirm/hold/pay\n• receipts\n• on-chain settlement + fees]:::task
G05[Business Creation Sheet\n• build/config/publish .dc\n• register wormhole]:::task
F04 –> G0
G0 –> G01 –> G02 –> G03 –> G04 –> G05

%% ================== PHASE 7: SECURITY & OPS ==================
H0[🛡️ P7 • Security & Ops]:::phase
H01[Key Mgmt\n• device keys\n• secure enclave/HSM\n• rotation]:::task
H02[Policy Engine\n• SoulLaw editor\n• policy packs\n• test harness]:::task
H03[Telemetry (privacy-first)\n• local metrics\n• anon agg\n• kill switches]:::task
H04[Update Channel\n• signed updates\n• rollback\n• canary]:::task
H05[Chaos/Recovery\n• fault inject\n• replay\n• snapshots]:::task
H06[Deterministic Audit\n• time budgets\n• policy decisions\n• packet trails]:::task
A02 –> H0
H0 –> H01 –> H02 –> H03 –> H04 –> H05 –> H06

%% ================== PHASE 8: DX & TOOLING ==================
I0[🧑‍💻 P8 • Dev eXperience]:::phase
I01[CLI (codex)\n• init/run/pack\n• keys\n• wormholes\n• wave send]:::task
I02[SDKs\n• JS/TS runtime kit\n• Python ops kit\n• Rust protocol crate]:::task
I03[Playground\n• local containers\n• inspector\n• recipes]:::task
I04[Docs\n• “Hello Dimension”\n• protocol refs\n• security guides]:::task
I05[Simulators\n• GlyphNet node sim\n• LuxNet mesh sim\n• Packet/replay tools]:::task
B07 –> I0
I0 –> I01 –> I02 –> I03 –> I04 –> I05

%% ================== PHASE X: LAUNCH PATH ==================
Z0[🚀 Launch Path]:::phase
Z1[Alpha (local only)\n• vault\n• AION home\n• dimension renderer (v0 ✅)\n• Prompt Bar\n• Time controls]:::milestone
Z2[Beta (networked)\n• GlyphNet mesh + IP fallback\n• SoulLink\n• Encrypted Waves\n• Registry]:::milestone
Z3[GA\n• Commerce nodes\n• on-chain settlement\n• policy packs\n• updates/telemetry]:::milestone
E03 –> Z1 –> Z2 –> Z3

classDef phase fill:#0b1020,stroke:#4f63ff,stroke-width:1px,color:#e6ecff;
classDef task fill:#10162a,stroke:#4253ff,color:#dbe4ff;
classDef milestone fill:#0f1b2d,stroke:#09f,color:#e6ffff,stroke-dasharray: 3 3;
classDef phase fill:#0b1020,stroke:#4f63ff,stroke-width:1px,color:#e6ecff;
classDef task fill:#10162a,stroke:#4253ff,color:#dbe4ff;
classDef milestone fill:#0f1b2d,stroke:#09f,color:#e6ffff,stroke-dasharray: 3 3;

⸻

Key Notes & “Do-Not-Lose” Info

Addressing & Navigation
	•	🌀 Wormhole Bar is default; .tp suffix resolves via Registry to a container. Users can toggle to www. legacy.
	•	Supported schemes: dimension://, ucs://, glyph://, 🌀name.tp.

Transport Order & Hosting
	•	Transport order: GlyphNet mesh (radio) → IP (HTTPS/WebSocket w/ GIP) → CAS snapshot (read-only) → Ephemeral local runtime (reconcile later).
	•	Hosting: Live edge runtimes (owner-operated portal nodes) + content-addressed snapshots (IPFS/Arweave/S3-CAS). On-chain anchors store names/versions/keys (not bulk data).

Containers & Time Dilation
	•	TimeEngine is per-container. time_ratio scales internal scheduler budgets (CPU/memory quotas + cooperative yielding). UI exposes Time Dial.
	•	“Instant” agent replies are the product of container-time dilation; all collapses are auditable via replay.

Protocol Contracts
	•	GIP frame: { hdr:{ ver, ts, trace, auth }, body:{ glyphs|ops }, sig } with streaming + resume via trace+seq.
	•	Wormhole intents are idempotent with TTL, trace_id, and retry policy.
	•	QKD hooks for wave messaging: session bootstrap, fingerprint, fallback if unavailable.

Knowledge Graph
	•	Each user/business maintains a dedicated Knowledge Graph (KG) in their container: preferences, history, cookies-for-AI, saved media, wormhole links. Exposed to AION with explicit SoulLaw gates.

Security/Invariants
	•	Device keys never leave the vault; remote ops use short-lived capability tokens.
	•	All network traffic: GlyphNet WS or HTTPS with GIP payloads; packets are signed.
	•	Deterministic replay: glyph ops, time budgets, and policy decisions are re-runnable for audit.
	•	Kill-switch to pause/terminate runaway thought loops.

Performance Targets
	•	Cold open: < 1500 ms to first interactive frame.
	•	Prompt → first token (local): < 250 ms (warm).
	•	Time-dilation jitter: < 5% up to 600×.
	•	GlyphGrid render: 60 FPS for N=500 live glyphs.
	•	Transport switch: < 200 ms seamless mesh↔IP failover.

Developer Experience
	•	One-line local dev: codex init && codex run.
	•	Playground mounts a container folder; hot-reloads CodexLang.
	•	Inspector records: glyph trace, memory writes, ethics checks, network hops, time slices.

Compatibility & Rollout
	•	Alpha: local-only; import .dc from file.
	•	Beta: enable SoulLink + GlyphNet with trusted registry (allowlist).
	•	GA: Commerce nodes + policy packs + on-chain settlement; maintain backward protocol compatibility.

⸻

Deliverables Checklist (condensed)
	•	Tauri shell + React AI-first browser
	•	Runtime bridge (WASM CodexCore + native crypto)
	•	Vault & keyring + encrypted .dc mounts
	•	🌀 wormhole resolver + dual-band TransportSelector
	•	AION Home (Prompt Bar + Wave Inbox + Time Dial + KG dock)
	•	Dimension Inspector (glyph/time/memory/net + GIP sniffer)
	•	GlyphNet adapters + GIP framing + Router + Registry
	•	SoulLink handshake + QKD messaging hook
	•	Encrypted wave messaging (message/email merged)
	•	Business Creation Sheet + Marketplace Router
	•	Policy engine + security test harness
	•	CLI, SDKs, Playground, Simulators, Docs
	•	Alpha → Beta → GA rollout gates


***************************GLYPHNET BROWSER CHECKLIST******************************************







send a WAVE - is like a message
Send a teleport - email

or both are waves, emails merged into messages, 

the browser is the internet, its the access to the glyphnet, the url is the wormhole address
ones the addres is located it takes you to the dc container, a business container or your personal container or a shared container
personal container is like your way to message, email , communicate with people, communicate with aion, setup tasks etc
business containers is purchasing services, browsing the new net, buying things,

the glyphnet sdhould be dual, works off normal net and has access / uses the glyphnet radio frequency as a mesh

the browser is literally the access to the glyphnet, it is the receiver and antenna, that is the radio basically

there should be a dev tools sections which provides access to essentailly build new agents or business aplications

graph TD
  %% =============== PHASE 0: FOUNDATIONS ===============
  A0[🏁 P0 • Foundations]:::phase
  A01[Repo scaffolding\n• mono-repo (apps/packages)\n• CI (lint/test/build)\n• release tags]:::task
  A02[Sec baseline\n• signed commits\n• SAST/dep scan\n• secrets policy]:::task
  A03[Design system\n• Tailwind tokens\n• shadcn/ui kit\n• iconography + motion]:::task
  A04[Spec registry\n• Protocol ADRs\n• RPC/GIP schemas\n• versioning rules]:::task
  A0 --> A01 --> A02 --> A03 --> A04

  %% =============== PHASE 1: BROWSER SHELL ===============
  B0[🧭 P1 • Browser Shell (Electron+Next)]:::phase
  B01[Electron shell\n• multi-window\n• sandboxed renderer\n• updates]:::task
  B02[Runtime bridge\n• Rust/Tauri module\n• Node native addon\n• WASM CodexCore]:::task
  B03[Container FS\n• local vault\n• encrypted .dc mounts\n• key mgmt (wallet)]:::task
  B04[Navigation model\n• dimension:// scheme\n• wormhole intents\n• history graph]:::task
  B05[UI frame\n• Prompt Bar (Cmd-K)\n• Time Dilation HUD\n• Dock: Containers/Agents]:::task
  B06[DevTools: Dimension Inspector\n• glyph trace\n• time profiler\n• memory map]:::task
  A04 --> B0
  B0 --> B01 --> B02 --> B03 --> B04 --> B05 --> B06

  %% =============== PHASE 2: CORE RUNTIME ===============
  C0[🧠 P2 • Core Runtime (CodexCore/Tessaris)]:::phase
  C01[CodexCore engine\n• evaluator + scheduler\n• effect system]:::task
  C02[TessarisEngine\n• thought expansion\n• collapse operators]:::task
  C03[TimeEngine\n• time_ratio\n• budget caps\n• watchdogs]:::task
  C04[GlyphExecutor\n• pipelines\n• streaming outputs\n• cancellation]:::task
  C05[Memory/DNA\n• glyph store\n• mutation ledger\n• compaction/GC]:::task
  C06[Ethics/SoulLaw\n• allow/deny rules\n• recovery states\n• audit hooks]:::task
  B02 --> C0
  C0 --> C01 --> C02 --> C03 --> C04 --> C05 --> C06

  %% =============== PHASE 3: NETWORK LAYER ===============
  D0[🌐 P3 • Network & Protocols]:::phase
  D01[GlyphNet (WS)\n• pub/sub topics\n• backpressure\n• auth tokens]:::task
  D02[GIP (Glyph Internet Protocol)\n• compression\n• frames/ops\n• replay]:::task
  D03[Wormhole Router\n• intent → route\n• trust graph\n• retries/ttl]:::task
  D04[SoulLink handshake\n• container identity\n• mutual attestation\n• keys/rotations]:::task
  D05[Registry\n• address book\n• discovery cache\n• pin/trust lists]:::task
  C04 --> D0
  D0 --> D01 --> D02 --> D03 --> D04 --> D05

  %% =============== PHASE 4: DIMENSION RUNTIME UI ===============
  E0[🪟 P4 • Dimension Runtime UI]:::phase
  E01[Dimension Renderer\n• dc schema → UI tree\n• slots: Prompt/GlyphGrid/Logs]:::task
  E02[Prompt Bar v1\n• CodexLang input\n• tooluse palette\n• slash cmds]:::task
  E03[Time Controls\n• live ratio dial\n• pause/step\n• budget presets]:::task
  E04[GlyphGrid 3D\n• streams/tails\n• pin/share/export\n• diffs]:::task
  E05[Inspector Overlays\n• ethics hits\n• memory writes\n• network traces]:::task
  B05 --> E0
  E0 --> E01 --> E02 --> E03 --> E04 --> E05

  %% =============== PHASE 5: SOULNET LAYER ===============
  F0[🔒 P5 • SoulNet Social Layer]:::phase
  F01[Encrypted Messaging\n• container ↔ container\n• threaded intents\n• attachments (glyphs)]:::task
  F02[Sharing & Permissions\n• share dim pages\n• scopes/time-box\n• revoke]:::task
  F03[Presence & Bonds\n• SoulLink bonds\n• trust levels\n• consent gates]:::task
  F04[Inbox/Outbox\n• queued intents\n• summaries\n• recovery]:::task
  D04 --> F0
  F0 --> F01 --> F02 --> F03 --> F04

  %% =============== PHASE 6: COMMERCE NODES ===============
  G0[🛒 P6 • CodexCommerce]:::phase
  G01[Business Container Template\n• product_list.codex\n• offer_logic.glyph]:::task
  G02[Intent Parser\n• buy/compare\n• constraints\n• scoring]:::task
  G03[Marketplace Router\n• multi-offer fanout\n• trust/latency scores]:::task
  G04[Checkout Glyphs\n• confirm/hold/pay\n• receipts\n• refunds]:::task
  F04 --> G0
  G0 --> G01 --> G02 --> G03 --> G04

  %% =============== PHASE 7: SECURITY & OPS ===============
  H0[🛡️ P7 • Security & Ops]:::phase
  H01[Key Mgmt\n• device keys\n• HSM/secure enclave\n• rotation]:::task
  H02[Policy Engine\n• SoulLaw editor\n• policy packs\n• test harness]:::task
  H03[Telemetry (privacy-first)\n• local metrics\n• anon agg\n• kill switches]:::task
  H04[Update Channel\n• signed updates\n• rollback\n• canary]:::task
  H05[Chaos/Recovery\n• fault inject\n• replay\n• snapshots]:::task
  A02 --> H0
  H0 --> H01 --> H02 --> H03 --> H04 --> H05

  %% =============== PHASE 8: DX & TOOLING ===============
  I0[🧑‍💻 P8 • Dev eXperience]:::phase
  I01[CLI (codex)\n• init/run/pack\n• keys\n• wormholes]:::task
  I02[SDKs\n• JS/TS runtime kit\n• Python ops kit\n• Rust protocol crate]:::task
  I03[Playground\n• local containers\n• inspector\n• recipes]:::task
  I04[Docs\n• “Hello Dimension”\n• protocol refs\n• security guides]:::task
  B06 --> I0
  I0 --> I01 --> I02 --> I03 --> I04

  %% =============== PHASE X: ALPHA/BETA/GA ===============
  Z0[🚀 Launch Path]:::phase
  Z1[Alpha (local only)\n• vault\n• dimension renderer\n• Prompt Bar\n• Time controls]:::milestone
  Z2[Beta (networked)\n• GlyphNet\n• SoulLink\n• Messaging]:::milestone
  Z3[GA\n• Commerce nodes\n• policy packs\n• updates/telemetry]:::milestone
  E03 --> Z1 --> Z2 --> Z3

  classDef phase fill:#0b1020,stroke:#4f63ff,stroke-width:1px,color:#e6ecff;
  classDef task fill:#10162a,stroke:#4253ff,color:#dbe4ff;
  classDef milestone fill:#0f1b2d,stroke:#09f,color:#e6ffff,stroke-dasharray: 3 3;

  Key Notes & “Do-Not-Lose” Info

Architectural Contracts
	•	dimension:// URI scheme → resolves to container id + optional entry surface.
	•	Wormhole intents are idempotent messages with TTL, trace id, retry policy.
	•	GIP frames = {hdr:{ver,ts,trace,auth}, body:{glyphs|ops}, sig}; streaming ok, resumable via trace+seq.
	•	TimeEngine exposes time_ratio, cpu_budget_ms, mem_budget_mb, watchdog_events.
	•	SoulLaw evaluates pre-execution, mid-stream, and on-commit; must support deny with remedy.

Security/Invariants
	•	Keys never leave device vault; remote ops use capability tokens derived from local keys (short-lived).
	•	All network traffic over GlyphNet WS or HTTPS with GIP-framed payloads.
	•	Deterministic replays: glyph ops, time budgets, and policy decisions must be replayable for audit.
	•	Kill-switch in runtime to pause/terminate runaway thought loops.

Performance Targets
	•	Cold open: < 1500 ms to first interactive frame.
	•	Prompt→first token (local): < 250 ms (after warm).
	•	Time dilation scheduling jitter: < 5% at ratios up to 600×.
	•	GlyphGrid render steady at 60 FPS for N=500 live glyphs.

DX (Developer Experience)
	•	One-line local dev: codex init && codex run.
	•	Playground can mount a container folder and hot-reload CodexLang.
	•	Inspector records: glyph trace, memory writes, ethics checks, network hops, time slices.

Compatibility & Rollout
	•	Alpha runs local-only (no external registry); import .dc from file.
	•	Beta enables SoulLink + GlyphNet with a trusted registry (allowlist).
	•	GA introduces Commerce nodes and policy packs; keep backward protocol compatibility (ver headers).

⸻

Deliverables Checklist (condensed)
	•	Electron shell + Next.js app scaffold
	•	Runtime bridge (WASM CodexCore + Node addon)
	•	Vault & keyring + encrypted .dc mounts
	•	dimension:// resolver + wormhole navigation
	•	Prompt Bar + Time Dilation HUD + GlyphGrid
	•	Dimension Inspector (glyph/time/memory/net)
	•	GlyphNet (WS) + GIP framing + router
	•	SoulLink handshake + trust graph
	•	Encrypted container messaging
	•	Business container template + marketplace router
	•	Policy engine + security test harness
	•	CLI, SDKs, Playground, Docs
	•	Alpha → Beta → GA rollout gates

If you want, I can turn this into a GitHub Project kanban with issue templates and CI workflows pre-wired (ESLint, Ruff, PyTest, Vitest, Playwright, Cargo).

graph TD
    A[📦 Phase 1 — Core Browser Shell] --> A1[frontend/pages/browser/index.tsx — Browser UI Frame]
    A1 --> A1a[Implement multi-tab container view]
    A1 --> A1b[Docked prompt bar + CodexLang execution console]
    A1 --> A1c[Tab = container session mapping]
    A --> A2[frontend/components/Browser/TabBar.tsx]
    A2 --> A2a[Dynamic tab creation/removal]
    A2 --> A2b[Bind each tab to container_id + wormhole link]
    A --> A3[frontend/components/Browser/AddressBar.tsx]
    A3 --> A3a[Container address resolution]
    A3 --> A3b[Teleport to container via Wormhole Router]
    A --> A4[frontend/components/Browser/Viewport.tsx]
    A4 --> A4a[Render dimension page UI if available]
    A4 --> A4b[Fallback: generic container preview shell]
    A --> A5[frontend/hooks/useContainerSession.ts]
    A5 --> A5a[Connect to backend websocket_manager.py]
    A5 --> A5b[Stream CodexCore/GlyphOS outputs live]
    A5 --> A5c[Handle session resume/close events]

    B[⚙ Phase 2 — Backend Container API] --> B1[backend/modules/browser/browser_manager.py]
    B1 --> B1a[Launch container sessions on request]
    B1 --> B1b[Return container metadata + time_dilation params]
    B1 --> B1c[Manage multiple active container sessions]
    B --> B2[backend/modules/browser/wormhole_router.py]
    B2 --> B2a[Resolve container_id or address → runtime session]
    B2 --> B2b[Forward prompt bar inputs to container CodexCore]
    B --> B3[backend/modules/browser/container_proxy.py]
    B3 --> B3a[Bridge browser viewport to container dimension renderer]
    B3 --> B3b[Handle encrypted container data streams]

    C[🔗 Phase 3 — SoulNet Integration Layer] --> C1[frontend/hooks/useSoulNetLinks.ts]
    C1 --> C1a[Detect if container has dimension page mapping]
    C1 --> C1b[Enable “Open in Browser” from SoulNet UI]
    C --> C2[backend/modules/soulnet/soulnet_integration.py]
    C2 --> C2a[Listen for cross-container share events]
    C2 --> C2b[Allow friend-to-friend container sharing]
    C --> C3[frontend/components/SoulLinkBadge.tsx]
    C3 --> C3a[Show when container is linked to another SoulNet user]

    D[🚀 Phase 4 — Runtime Enhancements] --> D1[Time Dilation Controls in Browser UI]
    D1 --> D1a[Allow per-tab speed adjustments]
    D1 --> D1b[Visual indicator of internal vs external time]
    D --> D2[Multi-Agent Collaboration Tabs]
    D2 --> D2a[Multiple users in one container session]
    D2 --> D2b[Live glyph sync via GlyphNet]
    D --> D3[CodexLang Script Injection]
    D3 --> D3a[Run custom CodexLang scripts in any container]

    E[🛡 Phase 5 — Security & Ethics] --> E1[SoulLaw Enforcement Layer]
    E1 --> E1a[Filter unsafe prompts/outputs]
    E1 --> E1b[Warn before irreversible container mutations]
    E --> E2[Encrypted Container Messaging]
    E2 --> E2a[Private tab-to-tab container comms]
    E2 --> E2b[Optional AI-driven junk filter]

    Key Notes to Keep
	1.	Modular Build → Browser shell first, SoulNet social pages later.
	2.	Container-First Design → Every tab is a container session (dimension page optional).
	3.	Real-Time Streaming → WebSocket connection per tab for CodexCore + GlyphOS outputs.
	4.	Wormhole Routing → Address bar accepts both container IDs and SoulNet wormhole links.
	5.	Security by Default → All container interactions pass through SoulLaw filter.
	6.	Time Dilation Ready → Tabs can run at different subjective time speeds.
	7.	Plugin Hooks → CodexLang scripts and dimension renderers are hot-swappable.
	8.	Encrypted Comms → Support direct container-to-container chat/messaging.

⸻
Awesome — here’s a clean, practical repo map + wiring plan to stand up the Next-Gen Browser Shell now, and snap SoulNet dimension pages in later with zero rewiring.

Folder & File Map (minimal, production-ready)

/frontend
  /components/Browser
    AddressBar.tsx             # container address / wormhole input + resolver
    TabBar.tsx                 # tab mgmt (add/close/switch), session badges
    Viewport.tsx               # renders dimension page or generic container view
    PromptBar.tsx              # CodexLang console (send → backend → stream)
    TimeDial.tsx               # per-tab time dilation control UI
    DevConsole.tsx             # stream log, glyphs, errors
  /hooks
    useContainerSession.ts     # create/attach session, WS stream, lifecycle
    useWormhole.ts             # resolve ucs:// / dimension:// → container_id
    useSoulNetLinks.ts         # (future) deep-link from SoulNet into tabs
  /lib
    api.ts                     # REST calls: create session, send prompt, etc.
    ws.ts                      # websocket helper with auto-retry + events
    types.ts                   # shared FE types (zod) mirrors shared/schemas
  /pages
    /browser
      index.tsx                # main shell layout: TabBar + AddressBar + Viewport
    /_app.tsx                  # theme/provider bootstrapping
  /state
    browserStore.ts            # zustand store: tabs, activeTabId, sessions
  /styles
    globals.css

/backend
  /routes
    browser_api.py             # REST: create/close session, prompt, list, resolve
    container_ws.py            # WS: /ws/containers/{session_id}
  /modules
    /browser
      browser_manager.py       # Session registry; owns session <-> container link
      wormhole_router.py       # resolve addresses → container_id, provenance
      container_proxy.py       # bridges runtime (UCS) to stream frames
      time_dilation.py         # per-session time controls (soft scheduler)
      security.py              # SoulLaw gates for prompts/outputs
    /soulnet
      soulnet_integration.py   # (later) share/open from SoulNet into browser
  /adapters
    ucs_bridge.py              # thin wrapper over ucs_runtime (create/load/exec)
  main.py                      # FastAPI app, router mounts, CORS, ws

/shared
  /schemas
    events.py                  # Pydantic: WS frames (OPEN/STATE/OUTPUT/ERROR/CLOSE)
    api.py                     # Pydantic: REST DTOs (CreateSession, Prompt, etc.)
  /ts
    events.ts                  # zod mirrors for FE
    api.ts

/infra
  dev.env                      # BACKEND_WS_URL, BACKEND_HTTP_URL, etc.
  docker-compose.yml
  Procfile

  Contracts (keep these stable)

REST (FastAPI)
	•	POST /browser/sessions → Create session for a container
	•	body: { container_id?: string, address?: string, time_ratio?: number }
	•	resp: { session_id, container_id, time_ratio, created_at }
	•	POST /browser/sessions/{id}/prompt → Send CodexLang prompt
	•	body: { text: string, context?: object }
	•	resp: { accepted: true }
	•	POST /browser/sessions/{id}/time → Update time dilation
	•	body: { time_ratio: number } → resp { ok: true }
	•	DELETE /browser/sessions/{id} → Close session
	•	GET /browser/sessions → List active sessions
	•	GET /browser/resolve?address=ucs://... → { container_id }

WebSocket
	•	GET /ws/containers/{session_id}
	•	Frames (JSON, newline-delimited):
	•	OPEN   { type:"OPEN",   session_id, container_id, meta }
	•	STATE  { type:"STATE",  session_id, status, time_ratio }
	•	OUTPUT { type:"OUTPUT", session_id, stream:[ ... glyphs/log lines ... ] }
	•	ERROR  { type:"ERROR",  session_id, message, code? }
	•	CLOSE  { type:"CLOSE",  session_id, reason? }

Backend: key wiring

adapters/ucs_bridge.py
	•	Import the singleton UCS runtime and do all interactions through it.
	•	Methods:
	•	ensure_container_loaded(container_id|address) -> container_id
	•	start_session(container_id) -> SessionHandle (lightweight id + refs)
	•	execute_prompt(session, text, context) → yields OUTPUT chunks
	•	set_time_ratio(session, ratio) → time_dilation scheduler hint

modules/browser/browser_manager.py
	•	In-memory sessions: Dict[session_id, Session].
	•	create_session(container_id, time_ratio):
	•	calls ucs_bridge.ensure_container_loaded()
	•	allocates session_id, stores {container_id, time_ratio, ws_clients:set()}
	•	attach_ws(session_id, websocket); detach_ws(...)
	•	broadcast(session_id, frame); close_session(session_id)

modules/browser/wormhole_router.py
	•	resolve(address:str) -> container_id:
	•	accepts ucs://, dimension://, raw ids
	•	tries local ucs_runtime.resolve_atom/address_index, then registry

routes/browser_api.py

Minimal stubs (they just orchestrate the modules):

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from shared.schemas.api import CreateSession, SessionInfo, PromptIn
from backend.modules.browser import browser_manager, wormhole_router

router = APIRouter(prefix="/browser", tags=["browser"])

@router.post("/sessions", response_model=SessionInfo)
def create_session(req: CreateSession):
    cid = req.container_id or wormhole_router.resolve(req.address or "")
    if not cid:
        raise HTTPException(404, "Container not found")
    return browser_manager.create_session(cid, req.time_ratio or 1.0)

@router.post("/sessions/{sid}/prompt")
def send_prompt(sid: str, body: PromptIn):
    browser_manager.send_prompt(sid, body.text, body.context or {})
    return {"accepted": True}

@router.post("/sessions/{sid}/time")
def set_time(sid: str, body: dict):
    browser_manager.set_time_ratio(sid, float(body.get("time_ratio", 1.0)))
    return {"ok": True}

@router.delete("/sessions/{sid}")
def close_session(sid: str):
    browser_manager.close_session(sid)
    return {"ok": True}

routes/container_ws.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.modules.browser import browser_manager

ws_router = APIRouter()

@ws_router.websocket("/ws/containers/{sid}")
async def ws_container(websocket: WebSocket, sid: str):
    await websocket.accept()
    await browser_manager.attach_ws(sid, websocket)
    try:
        while True:
            _ = await websocket.receive_text()  # (optional) inbound commands
    except WebSocketDisconnect:
        await browser_manager.detach_ws(sid, websocket)

Frontend wiring (React + TS + Zustand)

state/browserStore.ts

import create from "zustand";
import { SessionInfo } from "@/shared/ts/api";

type Tab = { tabId: string; sessionId: string; title: string; containerId: string };
type Store = {
  tabs: Tab[];
  activeTabId?: string;
  addTab: (s: SessionInfo) => void;
  closeTab: (tabId: string) => void;
  setActive: (tabId: string) => void;
};

export const useBrowserStore = create<Store>((set) => ({
  tabs: [],
  addTab: (s) =>
    set((st) => ({
      tabs: [...st.tabs, { tabId: s.session_id, sessionId: s.session_id, title: s.container_id, containerId: s.container_id }],
      activeTabId: s.session_id,
    })),
  closeTab: (tabId) => set((st) => ({ tabs: st.tabs.filter(t => t.tabId !== tabId) })),
  setActive: (tabId) => set({ activeTabId: tabId }),
}));

hooks/useContainerSession.ts

import { useEffect, useRef, useState } from "react";
import { openWS } from "@/lib/ws";
import { createSession, sendPrompt, setTime } from "@/lib/api";
import { WSEvent } from "@/shared/ts/events";

export function useContainerSession(initial?: { containerId?: string; address?: string; }) {
  const [session, setSession] = useState<{ sessionId?: string; containerId?: string; timeRatio: number }>({ timeRatio: 1 });
  const [stream, setStream] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  async function open(target: { containerId?: string; address?: string; timeRatio?: number }) {
    const s = await createSession(target);
    setSession({ sessionId: s.session_id, containerId: s.container_id, timeRatio: s.time_ratio });
    wsRef.current = openWS(`/ws/containers/${s.session_id}`, (evt: WSEvent) => {
      if (evt.type === "OUTPUT") setStream((prev) => [...prev, ...evt.stream]);
    });
  }

  async function prompt(text: string, ctx?: any) {
    if (!session.sessionId) return;
    await sendPrompt(session.sessionId, { text, context: ctx });
  }

  async function setTimeRatio(r: number) {
    if (!session.sessionId) return;
    await setTime(session.sessionId, r);
    setSession((s) => ({ ...s, timeRatio: r }));
  }

  useEffect(() => () => { wsRef.current?.close(); }, []);
  return { session, stream, open, prompt, setTimeRatio };
}

components/Browser/AddressBar.tsx
	•	Parses ucs://... or dimension://... and calls open({ address }).
	•	If raw container_id, call open({ containerId }).

components/Browser/Viewport.tsx
	•	If a dimension page renderer is registered for that container, render it; else show generic inspector (meta, glyphs stream, prompt).

Time Dilation (soft first, hard later)
	•	Soft: UI control sends time_ratio → backend stores it on session and uses it to batch outputs/throttle or “expand” internal cycles (simulate with timers).
	•	Hard (later): Integrate with UCS/AION time scheduler if present (real compute dilation).

Security (always on)
	•	All prompts → security.py → SoulLaw checks (content, irreversible ops, spending).
	•	All outputs → optional redaction/filter for unsafe leakage before UI.

Boot order & “build before SoulNet?”

Yes. This browser runs now:
	1.	Implement the backend session API + WS.
	2.	Implement frontend shell (TabBar, AddressBar, Viewport, PromptBar).
	3.	Hook to UCS runtime adapter (load container, execute prompts).
	4.	When SoulNet pages arrive, register dimension renderers → they auto-render inside Viewport.

ENV you’ll need

BACKEND_HTTP_URL=http://localhost:8000
BACKEND_WS_URL=ws://localhost:8000
CORS_ORIGINS=http://localhost:3000

Quick success path (MVP sprint)
	•	Day 1–2: browser_manager, REST + WS, FE shell with one tab & prompt.
	•	Day 3: AddressBar resolve + multiple tabs, live OUTPUT stream.
	•	Day 4: TimeDial + security gates + error surfaces.
	•	Day 5: “Open in Browser” hook from SoulNet (stub), pluggable renderer slot.

