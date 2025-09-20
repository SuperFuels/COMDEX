GlyphNet Protocol (GNP) — Draft RFC v0.9

Status: Draft
Intended audience: engineers building GlyphNet nodes, transports, gateways, and tooling
Scope: Defines a symbolic, wave-native networking stack; packet formats; routing; reliability; security; and reference APIs.

⸻

1. Abstract

GlyphNet replaces bitstream-centric networking with symbolic packets (GIP) that can be encoded directly onto waves and executed end-to-end. Meaning is carried at the physical edge (waveforms → glyphs), removing binary parsing layers. This RFC specifies the layered stack (sPHY, sMAC, sNET, sSEC, sAPP); GIP packet structure; addressing, routing, reliability, security, and replay; and maps them to the reference implementation you’ve built.

⸻

2. Motivation
	•	Semantic transport: transmit meaning (glyph logic) rather than opaque bits.
	•	Performance: avoid serialize/parse overhead (JSON→AST) by decoding waves→glyphs→exec.
	•	Security: enforce trust with QKD policy, ephemeral keys, and symbolic locks.
	•	Observability: built-in tracing, replay, and prediction streaming.

⸻

3. Terminology
	•	Glyph: atomic symbolic token (e.g., ✦, ↔, 🧠) with executable semantics.
	•	GIP (Glyph Instruction Packet): top-level packet carrying glyphs, metadata, and optional code fragments.
	•	Node / Container: execution environment (e.g., Dimension Kernel container).
	•	Transceiver: encodes/decodes GIP⇄wave.
	•	Transport channel: tcp, gwave, beacon, radio, light, local.
	•	QKD: quantum key distribution session (GKey) + policy enforcement.
	•	Ephemeral key: short-lived AES key tied to a session and symbolic lock(s).

⸻

4. Architecture (Layers)

4.1 sPHY — Symbolic Physical Layer
	•	Role: encode/decode glyph-bearing waveforms (audio/RF/light/fiber).
	•	Reference: glyphnet_transceiver.py, gip_adapter_wave.py, glyphwave_encoder.py.
	•	Encodings: tone/frequency maps, OAM/polarization (extensible registry).

4.2 sMAC — Symbolic Framing & Access
	•	Role: frame glyph sequences into GIP packets; apply compression refs; throttle; rate-limit; WS broadcast.
	•	Reference: glyph_transport_switch.py, broadcast_throttle.py, gip_compressor.py.

4.3 sNET — Routing & Delivery
	•	Role: addressing, channel selection, forwarding (tcp/gwave/beacon/radio/light/local), satellite delay buffer.
	•	Reference: glyph_transport_switch.py, glyphnet_packet.py, glyphnet_satellite_mode.py.

4.4 sSEC — Security & Trust
	•	Role: encryption (RSA/AES/ephemeral), QKD policy, locks, fingerprints, identity registry, rate limits.
	•	Reference:
	•	Crypto: glyphnet_crypto.py, ephemeral_key_manager.py, glyphnet_node_sim.py (sim), time_locked_key_manager.py.
	•	QKD: qkd_policy.py, qkd_fingerprint.py.
	•	Identity: agent_identity_registry (token validation).
	•	Abuse guard: rate_limit_manager.

4.5 sAPP — Execution & Orchestration
	•	Role: execute glyph logic, CodexLang, entanglement, teleport, replay, metrics, trace.
	•	Reference:
	•	Execution: gip_executor.py, glyphnet_terminal.py, glyphnet_command.py.
	•	Teleport: GlyphSocket, container_bootstrap.py.
	•	Replay/Trace: glyphnet_ws.py, glyphnet_trace.py, glyph_trace_logger, ReplayTimelineRenderer.
	•	UI: websocket broadcast, glyphnet_router.py, GlyphNetDebugger React component.

⸻

5. GIP Packet (Canonical)

{
  "id": "uuid",
  "timestamp": 1737412345.123,
  "type": "symbolic_thought|trigger|link|codexlang|glyph_push|... ",
  "sender": "AION",
  "recipient": "broadcast|target-id",
  "payload": { "glyphs": [ { "glyph": "✦", "args": {...} }, ... ], "...": "..." },
  "meta": { "trace_id": "opt", "qkd_required": false|"strict", "priority": "opt", ... },
  "encoding": "glyph",
  "compression": "symbolic"
}

	•	Creation: backend/modules/gip/gip_packet.py (dataclass + helpers).
	•	Validation: gip_packet_schema.py.
	•	Compression alias: gip_compressor.py.
	•	Encryption wrappers: glyphnet_packet.create_gip_packet(..., encrypt=...) or glyphnet_crypto.encrypt_packet(...).

⸻

6. Addressing & Identity
	•	IDs: human-readable identities (e.g., AION, MARS_DRONE) + optional container IDs.
	•	Public keys: resolvable via identity registry (agent_identity_registry).
	•	Tokens: validate_agent_token() used in WS handshake gate.
	•	Presence: glyphnet_satellite_mode.available_targets.

⸻

7. Routing & Transport
	•	API: route_gip_packet(packet, transport?: str, options?: dict) -> bool.
	•	Channels: tcp, gwave (wave transceiver), beacon (audio tone), radio, light, local.
	•	Auto-select: fallback order (e.g., ["gwave","tcp","beacon","radio","light","local"]).
	•	WS Broadcast: broadcast_ws_event("glyph_packet", packet).
	•	GWave path: transmit_gwave_packet(packet) via global transceiver.
	•	Local sim: simulate_waveform_transmission + loopback for developer testing.

⸻

8. Reliability & Flow
	•	Buffering: satellite mode stores & forwards when targets reappear.
	•	Throttling: broadcast_throttle minimizes WS floods.
	•	Rate limiting: per-sender guard via rate_limit_manager.
	•	(Optional) ACK/NACK: add meta.delivery_ack=true + WS echo on receiver; not enforced by core.

⸻

9. Security Model

9.1 Encryption
	•	Ephemeral AES: session-scoped via ephemeral_key_manager (auto-expiry, locks).
	•	RSA: for static interop; optional signature wrapping.
	•	Helpers: glyphnet_crypto.encrypt_packet/decrypt_packet.

9.2 QKD Policy
	•	Policy gate: qkd_policy.enforce_qkd_policy(packet, gkey); supports qkd_required: false|true|"strict".
	•	Combined integrity: verify_wave_state_integrity() checks decoherence fingerprint & collapse hash.
	•	Fallback renegotiation: renegotiate_gkey() on strict mode failure.

9.3 Locks & Time-locks
	•	Symbolic key locks: glyphnet_key_locks (CodexLang predicates to unlock).
	•	Time-locked keys: time_locked_key_manager (unlock by time or condition).

9.4 Identity & WS Gate
	•	WS token check: validate_agent_token() before accepting clients (defense-in-depth).

⸻

10. Execution Semantics
	•	Dispatcher: gip_executor.execute_gip_packet(packet) routes by packet.type.
	•	Supported types:
	•	symbolic_thought → parse each glyph, execute, store memory, metrics, trace.
	•	trigger → execute single glyph (from meta.trigger_glyph).
	•	link → container link creation.
	•	codexlang → run CodexLang string (from meta.code).
	•	Side broadcast: results forwarded to Codex + AION (gip_broadcast.py).
	•	Teleportation: GlyphSocket consumes TeleportPackets, boots/resumes containers, injects events.
	•	Replay: ReplayTimelineRenderer streams frames via WS (glyphnet_ws.stream_replay_frame).

⸻

11. Observability & Replay
	•	Trace buffer: glyphnet_trace.py (awareness, execution, prediction, snapshots).
	•	GIP log: gip_log.py (+ routes/glyphnet_router.py GET /glyphnet/logs).
	•	WS events: high-volume events throttled; handlers cover agent identity, CRDT merges, permission updates, prediction paths, SoulLaw verdicts, etc.
	•	Debugger UI: React component polls /api/glyphnet/logs.

⸻

12. Developer Gateways
	•	HTTP adapter: gip_adapter_http.py (/gip/send, /gip/packet).
	•	WS interface: gip_websocket_interface.py for raw GIP + symbolic commands.
	•	GlyphNet WS: glyphnet_ws.py (throttled broadcast, event handling, teleport hooks).
	•	Router API: routes/glyphnet_router.py for push/logs; optional /ws-test token precheck.

⸻

13. Extensibility Registries (proposed)
	•	Glyph→Wave registry: maps glyph IDs to sPHY encodings (mode, polarization, waveform).
	•	Packet types: open enum controlled by module registrations.
	•	Meta fields: reserved prefixes (qkd_*, acl_*, trace_*).
	•	Transports: dynamic registration (glyph_transport_config.py).

⸻

14. Error Codes (suggested)
	•	GNP-100 Invalid packet schema
	•	GNP-110 Unauthorized / invalid token
	•	GNP-200 QKD policy failure
	•	GNP-210 Fingerprint/collapse mismatch
	•	GNP-300 Transport unavailable
	•	GNP-310 Rate limited
	•	GNP-400 Execution error

⸻

15. Versioning
	•	Packet field gnp_version: recommended (default 0.9).
	•	Changes must be backward-compatible; unknown fields ignored by default.

⸻

16. Security Considerations
	•	Code execution risk: glyphs & CodexLang must run in sandboxed containers.
	•	Key lifecycle: ephemeral keys with TTL; locks + time-locks; vault persistence for long-term keys.
	•	Replay attacks: include nonce/epoch window in encrypted payloads; trace dedupe on id.
	•	Side channels: avoid leaking glyph→wave registry for secure links; prefer QKD + integrity checks.
	•	Abuse: apply rate limiting & throttling at sMAC and WS.

⸻

17. Interop with Legacy IP
	•	Gateway mode: run GlyphNet side-by-side, using tcp or ws transports for bridging.
	•	Dual stack: allow recipient="broadcast" on IP networks; route to GWave where supported.
	•	HTTP form: /gip/send for interop clients.

⸻

18. Minimal Conformance Profile

A Conformant GlyphNet Node MUST:
	1.	Parse/emit canonical GIP packets (Section 5) and validate schema.
	2.	Support at least one transport (tcp or gwave).
	3.	Enforce rate limiting and throttle WS broadcast.
	4.	Execute symbolic_thought and trigger types.
	5.	Support AES ephemeral encryption OR RSA public-key encryption.
	6.	Optionally enforce QKD policy if meta.qkd_required present.

⸻

19. Example Flows

19.1 Encrypted Push (Ephemeral AES)
	1.	Build packet via create_gip_packet(..., encrypt=True, ephemeral_session_id="sess-123").
	2.	ephemeral_key_manager generates key (symbolic derivation + TTL).
	3.	push_symbolic_packet(packet,"gwave") → _dispatch_packet → transmit_gwave_packet.
	4.	Receiver: glyphnet_transceiver.receive_packet() → decode → decrypt via session key → execute_gip_packet.

19.2 QKD Strict Route
	1.	Sender sets meta.qkd_required="strict" + expected fingerprint/collapse_hash.
	2.	_dispatch_packet calls enforce_qkd_policy() → verify_wave_state_integrity() → handshake check.
	3.	On failure: renegotiate GKey; if still failing, block.

19.3 Replay
	1.	Execution emits trace/log events.
	2.	ReplayTimelineRenderer.play_replay() streams frames via glyphnet_ws.stream_replay_frame.
	3.	UI scrubs timeline with pause/resume/seek.

⸻

20. Open Issues
	•	Standardize glyph→wave encodings beyond tone map (OAM, polarization).
	•	Formal ACK/NACK & congestion control.
	•	Multi-hop symbolic routing (GlyphRouters) based on meaning/state, not addresses.
	•	Signed packets & provenance ledger (optional).
	•	Formal CRDT schemas for collaborative glyph editing.

⸻

21. Reference Modules (by concern)
	•	Packets: gip_packet.py, glyphnet_packet.py, gip_packet_schema.py
	•	Transports: glyph_transport_switch.py, glyphnet_transceiver.py, glyphnet_transport.py, glyphwave_encoder.py, glyphwave_simulator.py, glyphnet_satellite_mode.py
	•	Security: glyphnet_crypto.py, ephemeral_key_manager.py, glyphnet_key_locks.py, time_locked_key_manager.py, qkd_policy.py, qkd_fingerprint.py, agent_identity_registry.py, rate_limit_manager
	•	Execution: gip_executor.py, glyphnet_terminal.py, GlyphSocket, container_bootstrap.py
	•	WS & API: glyphnet_ws.py, glyphnet_ws_interface.py, gip_websocket_interface.py, gip_adapter_http.py, glyphnet_router.py
	•	Observability: glyphnet_trace.py, gip_log.py, ReplayTimelineRenderer, React GlyphNetDebugger

⸻

22. Getting Started (Minimal)

# Create + send
from backend.modules.glyphnet.glyphnet_packet import create_gip_packet, push_symbolic_packet
pkt = create_gip_packet(payload={"glyphs":[{"glyph":"✦"}]}, sender="AION", target="ASTARION")
ok = push_symbolic_packet(pkt, transport="gwave")

# Receive + execute is handled by glyphnet_transceiver + gip_executor

