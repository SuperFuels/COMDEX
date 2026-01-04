flowchart TD
  %% GX1 End-to-End Build Plan (Mode A = MUST, Mode B = SHOULD, Extras = MAY)
  %% Legend:
  %% ✅ = done, ⏳ = next, ⬜ = pending
  %% MUST = benchmark-grade SIM path (canonical)
  %% SHOULD = integration path (SLE/QQC/SQI/QFC/UI/ledger)
  %% MAY = optional polish / plotting / perf

  A0([GX1: One callable engine, two modes]) --> A1

  %% ─────────────────────────────────────────────
  %% 0) Project Hygiene + Guardrails
  %% ─────────────────────────────────────────────
  subgraph H0[0) Hygiene + Guardrails]
    direction TB
    H01[[MUST ⬜ Define env toggles + invariants]]
    H01a[⬜ TESSARIS_DETERMINISTIC_TIME semantics documented]
    H01b[⬜ TESSARIS_TEST_QUIET semantics documented]
    H02[[MUST ✅ GX1-focused test suite runner]]
    H03[[MUST ✅ Import-cycle guard for wave_state]]
    H04[[MUST ✅ EntangledWave registry extracted (wave_store.py)]]
    H05[[MUST ✅ Add minimal log gate helper + adopt in noisy GX1 path]]
  end

  A1 --> H0
  H01 --> H01a --> H01b
  H0 --> A2

  %% ─────────────────────────────────────────────
  %% 1) Artifact Contract (single source of truth)
  %% ─────────────────────────────────────────────
  subgraph C0[1) Artifact Contract + Schemas]
    direction TB
    C01[[MUST ✅ Freeze output layout + filenames]]
    C01a[✅ runs/LATEST_RUN_ID.txt]
    C01b[✅ runs/<run_id>/CONFIG.json]
    C01c[✅ runs/<run_id>/METRICS.json]
    C01d[✅ runs/<run_id>/TRACE.jsonl]
    C01e[✅ runs/<run_id>/REPLAY_BUNDLE.json]
    C01f[✅ ARTIFACTS_INDEX.md + ARTIFACTS_INDEX.sha256]
    C02[[MUST ⬜ Stable JSON discipline]]
    C02a[⬜ stable key order + canonical floats (policy)]
    C02b[⬜ stable hashing helper used by tests]
    C03[[MUST ✅ JSON Schemas for CONFIG/METRICS/REPLAY]]
    C03a[✅ schema: gx1_genome_benchmark_config.schema.json]
    C03b[✅ schema: gx1_genome_benchmark_metrics.schema.json]
    C03c[✅ schema: gx1_genome_benchmark_replay_bundle.schema.json]
    C04[[MUST ✅ Contract tests (existence + schema-valid)]]
    C05[[MUST ✅ Metrics schema-compat hotfix recorded]]
    C05a[✅ metrics root strips builder-internal keys (mode/stride/max_events)]
  end

  A2([Mode A: SIM = benchmark core]) --> C0
  C01 --> C01a --> C01b --> C01c --> C01d --> C01e --> C01f
  C02 --> C02a --> C02b
  C03 --> C03a --> C03b --> C03c
  C0 --> A3

  %% ─────────────────────────────────────────────
  %% 2) Dataset Ingest (JSONL/FASTA -> records[])
  %% ─────────────────────────────────────────────
  subgraph D0[2) Dataset Ingest]
    direction TB
    D01[[MUST ✅ Dataset loader(s)]]
    D01a[✅ JSONL rows -> records[]]
    D01b[⬜ FASTA + sidecar manifest (if needed)]
    D02[[MUST ✅ Provenance stamping]]
    D02a[✅ dataset hash recorded in CONFIG + REPLAY_BUNDLE]
    D02b[✅ row count + schema version recorded]
    D03[[MUST ✅ Negative tests]]
    D03a[✅ invalid row schema rejected]
    D03b[✅ empty dataset rejected]
  end

  A3 --> D0
  D0 --> A4

  %% ─────────────────────────────────────────────
  %% 3) Codec (DNA -> deterministic op stream)
  %% ─────────────────────────────────────────────
  subgraph K0[3) Genomics Codec]
    direction TB
    K01[[MUST ✅ Define mapping table + version]]
    K01a[✅ A,C,G,T -> primitives/opcodes/glyph packets]
    K01b[✅ mapping_version embedded in CONFIG/REPLAY]
    K02[[MUST ✅ encode_dna(seq) -> symbol/op stream]]
    K03[[MUST ✅ decode(stream) -> recovered tokens]]
    K04[[MUST ✅ Determinism tests]]
    K04a[✅ same input+seed => identical stream]
    K04b[✅ stream hash stable across runs]
  end

  A4 --> K0
  K0 --> A5

  %% ─────────────────────────────────────────────
  %% 4) Scenarios (matched / mismatch / multiplex / mutation)
  %% ─────────────────────────────────────────────
  subgraph S0[4) Scenario Generator]
    direction TB
    S01[[MUST ✅ Scenarios defined]]
    S01a[✅ matched_key]
    S01b[✅ mismatched_key]
    S01c[✅ multiplex k=2..n]
    S01d[✅ mutation injection]
    S02[[MUST ✅ Scenario plan normalization]]
    S02a[✅ warmup_ticks / eval_ticks policy]
    S02b[✅ noise profiles / channel schedule]
    S03[[MUST ✅ Scenario determinism tests]]
  end

  A5 --> S0
  S0 --> A6

  %% ─────────────────────────────────────────────
  %% 5) Mode A Engine (SIM tick loop)
  %% ─────────────────────────────────────────────
  subgraph M0[5) Mode A: SIM Core Engine (Canonical)]
    direction TB
    M01[[MUST ✅ Deterministic tick loop]]
    M01a[✅ no wall clock]
    M01b[✅ fixed dt policy]
    M01c[✅ per-tick per-channel signals emitted]
    M02[[MUST ✅ Signal model completeness]]
    M02a[✅ amplitude/phase proxies]
    M02b[✅ coherence/drift proxies]
    M02c[✅ channel separation observables]
    M03[[MUST ✅ Decode stage]]
    M03a[✅ matched filtering / inverse operator]
    M03b[✅ integrate+dump recovered tokens]
    M04[[MUST ✅ Metrics stage]]
    M04a[✅ rho_matched / rho_mismatch]
    M04b[✅ crosstalk_max]
    M04c[✅ coherence/drift window means]
    M04d[✅ mutation localization score]
    M05[[MUST ✅ Artifact writer]]
    M05a[✅ stable CONFIG/METRICS/TRACE/REPLAY/INDEX]
    M06[[MUST ✅ GX1 test suite passes]]
  end

  A6 --> M0
  M0 --> A7

  %% ─────────────────────────────────────────────
  %% 6) Mode B Engine (Integration target)
  %% ─────────────────────────────────────────────
  subgraph B0[6) Mode B: SLE/QQC/SQI/QFC/UI/Ledger Integration]
    direction TB

    B01[[SHOULD ⬜ Shared plan adapter]]
    B01a[⬜ reuse SAME codec + scenarios from Mode A]
    B01b[⬜ plan -> WaveCapsule payload]

    B02[[SHOULD ✅ SLE adapter determinism]]
    B02a[✅ SLEAdapter tick-driven, seeded]
    B02b[✅ stable trace events]

    B03[[SHOULD ⬜ Dispatch path]]
    B03a[⬜ WaveCapsule -> SymaticsDispatcher]
    B03b[⬜ Dispatcher -> beam_tick_loop/beam_runtime/beam_scheduler]
    B03c[⬜ event envelope normalization consistent with TRACE contract]

    B04[[SHOULD ⬜ SQI hookup]]
    B04a[⬜ feed SQI engine with event stream]
    B04b[⬜ SQI score bundle returned + recorded]
    B04c[⬜ determinism: seeded RNG + no wall clock]

    B05[[SHOULD ⬜ QQC/Resonance Computer hookup]]
    B05a[⬜ bridge to QQC kernel (photon/resonance bridge)]
    B05b[⬜ resonance feedback influences drift/coherence in a controlled way]
    B05c[⬜ deterministic replay seeds captured]

    B06[[SHOULD ⬜ Telemetry + Ledger outputs]]
    B06a[⬜ ledger_feed writes data/ledger/...jsonl tagged with scenario_id]
    B06b[⬜ REPLAY_BUNDLE includes ledger hashes]
    B06c[⬜ optional websocket hooks gated/disabled in tests]

    B07[[SHOULD ⬜ QFC frames for UI]]
    B07a[⬜ qqc_qfc_adapter emits QFC frames]
    B07b[⬜ UI consumes frames without needing non-deterministic timing]

    B08[[SHOULD ⬜ Integration tests]]
    B08a[⬜ smoke: Mode B run produces artifacts + ledger]
    B08b[⬜ determinism: same seed => identical trace hashes]
  end

  A7([Mode B: Integration target]) --> B0
  B0 --> A8

  %% ─────────────────────────────────────────────
  %% 7) Replay + Repro (both modes)
  %% ─────────────────────────────────────────────
  subgraph R0[7) Replay + Reproducibility]
    direction TB
    R01[[MUST ✅ Replay bundle completeness]]
    R01a[✅ mapping_version + seeds + rng_algo]
    R01b[✅ scenario pack + thresholds snapshot]
    R01c[✅ trace hash + metrics hash]
    R02[[SHOULD ✅ Replay runner]]
    R02a[✅ re-run from REPLAY_BUNDLE -> same metrics/trace]
    R03[[MAY ⬜ Golden fixtures]]
    R03a[⬜ store small golden run bundle for CI]
  end

  A8 --> R0
  R0 --> A9

  %% ─────────────────────────────────────────────
  %% 8) CLI + UX (developer workflow)
  %% ─────────────────────────────────────────────
  subgraph X0[8) CLI + Dev Workflow]
    direction TB
    X01[[MUST ✅ Single entrypoint]]
    X01a[✅ python -m backend.genome_engine.run_genomics_benchmark ... (SIM)]
    X01b[✅ python -m backend.genome_engine.run_genomics_benchmark ... (SLE)]
    X02[[MUST ✅ Quiet mode by default in tests]]
    X02a[✅ TESSARIS_TEST_QUIET gates print/log spam]
    X03[[MAY ⬜ Optional plots exporter]]
    X03a[⬜ drift curves / separation curves saved under runs/<run_id>/plots]
  end

  A9 --> X0
  X0 --> Z0

  %% ─────────────────────────────────────────────
  %% 9) Done Criteria
  %% ─────────────────────────────────────────────
  subgraph Z0[9) Definition of Done]
    direction TB
    Z01[[MUST ✅ Mode A passes: deterministic, schema-valid, artifact-complete]]
    Z02[[SHOULD ⬜ Mode B runs end-to-end with SQI+ledger+QFC hooks (determinism-capable)]]
    Z03[[MUST ✅ Docs: how to run + how to replay + lock procedure]]
  end



⸻
You’re right to stop me. The actual product here is not “SIM-only baseline + optional hooks.” The thing we’re building is an end-to-end Genome Resonance Computer that:
    •   takes genomic inputs
    •   produces real runtime events through your existing resonance stack
    •   feeds SQI
    •   emits QFC frames to the existing frontend UI
    •   writes ledger + replay artifacts
    •   is deterministic (seed + tick clock) so the harness can grade it

Below is the full end-to-end flow you asked for: what runs, what calls what, and what gets emitted at each layer.

⸻

End-to-end flow (what we are building)

One callable entrypoint

run_genomics_benchmark() / genome_resonance_engine()
This orchestrates everything and returns a structured result and writes the artifact bundle.

It supports two execution backends:
    1.  SIM backend (fast reference model)
    2.  SLE/QQC backend (the real integration path: WaveCapsule → Dispatcher → Beam loop → SQI → QFC/UI + ledger)

The key: both modes produce the same artifact contract so harness comparison is apples-to-apples.

⸻

Mode A — SIM backend (reference correctness + debugging)

This is the “model of record” for correctness and repeatability.

A1) Dataset ingest
    •   Reads JSONL/FASTA → records[]
    •   Normalizes into a canonical internal schema:
    •   record_id
    •   sequence
    •   scenario_id
    •   channel_key (if present)
    •   mutation_spec (if present)

A2) Encode (genomics_codec)
    •   encode_dna(seq) -> symbol_stream
    •   Produces deterministic “chips/operators/glyph packets”:
    •   opcode
    •   args
    •   channel
    •   tick schedule

A3) Run (SIM tick loop)
    •   deterministic tick clock (TickClock(dt))
    •   seeded RNG (SeededRNG(seed))
    •   produces per tick/per channel:
    •   amplitude proxy
    •   phase proxy
    •   coherence/drift proxies
    •   crosstalk observables

A4) Decode
    •   matched filtering / inverse operator plan
    •   reconstructs tokens / recovered stream

A5) Score (genomics_metrics)
    •   rho_matched, rho_mismatch
    •   crosstalk_max
    •   windowed drift/coherence means
    •   mutation localization score

A6) Artifacts

Writes:
    •   CONFIG.json
    •   METRICS.json
    •   TRACE.jsonl
    •   REPLAY_BUNDLE.json
    •   ARTIFACTS_INDEX.md + sha256

✅ SIM is your “truth surface” for debugging and science.
But the product is Mode B.

⸻

Mode B — SLE/QQC backend (the real resonance computer path)

This is the thing that makes the benchmark actually run through your existing runtime and show up in the frontend UI.

B0) Engine orchestrator constructs a RunPlan

From dataset + scenario generator:
    •   scenarios[]
    •   thresholds
    •   seed, dt
    •   mux schedule
    •   mutation injection plan
    •   channel keys

This RunPlan is the same idea you already used for SLEAdapter determinism.

⸻

B1) Plan → WaveCapsule (payload)

wave_capsule.py
    •   Wrap the encoded stream (ops over ticks/channels) into a capsule payload that the runtime understands
    •   Adds deterministic metadata:
    •   seed, rng_algo
    •   dt, warmup_ticks, eval_ticks
    •   scenario_id, channel, tick
    •   Output: a capsule object / dict

⸻

B2) WaveCapsule → SymaticsDispatcher (operator execution)

symatics_dispatcher.py
    •   Dispatcher resolves opcode to the correct runtime domain
    •   Executes per tick/ch:
    •   symbolic ops
    •   photonic/resonance ops (via QQC bridges where relevant)
    •   Output: per tick results with fields like:
    •   coherence / qscore
    •   drift
    •   collapse_state
    •   optional prediction / symbolic state deltas

This is where “symbolic → resonance” actually happens.

⸻

B3) Dispatcher → Beam runtime tick loop (time-structured execution)

beam_tick_loop.py + beam_runtime.py + beam_scheduler.py
    •   Drives:
    •   tick index
    •   channel iteration
    •   queueing/scheduling
    •   event emission

Critical requirement for determinism
    •   Beam loop must be driven by tick index
    •   no wall clock sleeps in benchmark mode
    •   RNG must be injected, not global

Output: a stream of Beam events

⸻

B4) Event normalization → TRACE (contract)

Your adapter layer produces a normalized, stable event schema:
    •   tick, t, channel
    •   opcode, source, target
    •   qscore, drift
    •   scenario_id
    •   meta (status, collapse_state, etc.)

This is exactly what you already locked down with beam_event_envelope style output.

⸻

B5) SQI scoring (real hook, not optional)

sqi_engine.py / sqi_scorer.py
    •   Consumes the event stream (or per-tick glyph-like packets)
    •   Accumulates:
    •   coherence/drift features
    •   stability metrics
    •   convergence measures
    •   Produces:
    •   per scenario SQI series
    •   eval-window metrics
    •   summary bundle per scenario

SQI outputs must be included in:
    •   METRICS.json
    •   REPLAY_BUNDLE.json
    •   optionally event meta (for UI)

⸻

B6) QQC/QFC emission to frontend (UI integration)

This is the “you already have a full frontend UI” part.

The runtime should emit QFC frames (existing UI consumes)

qqc_qfc_adapter.py
    •   Converts tick events / wave state transitions into:
    •   nodes/links
    •   per-node SQI / collapse_state / prediction
    •   per-link drift/coherence overlays

These frames flow to:
    •   websocket broadcaster OR whatever the existing UI already listens to

So the UI shows:
    •   entanglement links
    •   drift glow
    •   pulse frequency overlays
    •   collapse state transitions
    •   SQI score progression

✅ This is “integration properly.”

⸻

B7) Ledger feed + replay bundle

ledger_feed.py
    •   Writes JSONL of telemetry events tagged with:
    •   run_id
    •   scenario_id
    •   tick/channel
    •   qscore/drift/SQI
    •   collapse state
    •   hashes if needed

Replay bundle
    •   Stores:
    •   config
    •   seeds + rng algorithm
    •   plan (capsule summary)
    •   trace hashes
    •   metrics hashes
    •   enough info to re-run and reproduce the result

⸻

B8) Artifacts (same contract as SIM)

Even though runtime is different, output contract is the same:
    •   CONFIG.json
    •   METRICS.json (includes SQI summary)
    •   TRACE.jsonl (normalized)
    •   REPLAY_BUNDLE.json
    •   ARTIFACTS_INDEX.md + sha

Plus SLE-only extras you already support:
    •   ledger JSONL
    •   QFC frame dump (optional) for replay/UI debugging

⸻

What this means: “full end-to-end” in one line

DNA → codec → WaveCapsule → SymaticsDispatcher → Beam tick loop → event stream → SQI scorer → QFC frame emitter → frontend UI + ledger → artifact bundle

That is the real resonance computer integration path.

⸻

Where we are now (based on your latest state)

From your outputs:
    •   ✅ deterministic tick clock + seeded path exists in GX1 suite
    •   ✅ SLEAdapter determinism stable
    •   ✅ wave_state determinism guard + evolve determinism done
    •   ✅ wave_store registry split done
    •   ✅ GX1-focused tests passing

So the next work is not “more SIM.” It’s:

⸻

Next build tasks to complete the real integration end-to-end

1) Make the orchestrator run Mode B from the GX1 harness
    •   Add run_genomics_benchmark(mode="sle")
    •   It should:
    •   build WaveCapsule plan
    •   run Beam loop
    •   collect normalized trace
    •   call SQI scorer
    •   emit QFC frames (or at least capture them)
    •   write ledger + artifacts

2) Ensure determinism across the Beam+SQI+QFC path
    •   Confirm:
    •   no time.time() usage in scoring path
    •   no random.* global usage in SQI / QFC adapter
    •   stable event ordering
    •   Extend replay bundle to include:
    •   SQI series + hash
    •   QFC frame series + hash (optional but recommended)

3) Add a single “end-to-end integration test” for Mode B

Something like:
    •   run a tiny scenario pack (matched + mux2)
    •   assert:
    •   TRACE.jsonl exists and deterministic
    •   METRICS.json contains SQI fields
    •   at least N QFC frames were emitted/captured
    •   ledger JSONL contains scenario_id tags

4) Quiet logging gate (you already asked for this)
    •   backend/utils/log_gate.py
    •   replace prints in the worst offenders
    •   keep the GX1 suite readable

⸻

If you want, I’ll write the Mermaid flow diagram + checklist in the exact “build task list” format, but now explicitly aligned to:
    •   Mode A: SIM (reference)
    •   Mode B: SLE/QQC/SQI/QFC/UI/ledger (real integration target)

Just say: “mermaid checklist now” and I’ll output the full mermaid + stepwise checklist.


Yes — that’s the right mental model with one important nuance:
    •   Mode A (SIM) is the canonical benchmark / grading path: fastest, deterministic, reviewer-proof, no dependency on the rest of the stack.
    •   Mode B (SLE/QQC/SQI/QFC/UI/ledger) is the integration path: proves the GX1 plan can be routed through your live runtime plumbing and UI/telemetry, but it’s not the primary grading surface unless you explicitly choose to make it so.

The nuance

Mode B is “bells & whistles” functionally, but it’s not “optional” in the product sense—you still want it because it demonstrates the resonance computer actually plugs into the system. It’s just not required for audit-grade benchmark determinism.

So the contract is:

✅ Mode A MUST pass and be stable (this is what you ship as benchmark-core).
✅ Mode B SHOULD work and be deterministic-capable (integration proof + UI/telemetry), but doesn’t block the benchmark unless you decide the harness grades it.

Practical rule:
    •   If you want “scientific reproducibility + stable artifact ladder” → Mode A.
    •   If you want “show it live in the UI + run through QQC/SQI runtime” → Mode B.

And they should share:
    •   same scenario definitions
    •   same codec mapping version
    •   same artifact contract shape (even if Mode B has extra optional outputs like ledger/QFC frames)

If you want, I can now produce the full mermaid checklist where:
    •   Mode A tasks are marked MUST
    •   Mode B tasks are marked SHOULD
    •   optional extras are MAY
so it matches how you’re actually running the sprint.


