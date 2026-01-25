Perfect — here it is in the same checklist format, but with explicit subtasks added wherever something is not truly finished.
Nothing hand-wavy, nothing removed, just clarity on what’s left.

⸻

Phase 0 — Baseline / Guardrails (CAU-first)

[x] Confirm CAU gate is the only learning permission source (INV-1)
[x] Confirm “No learning while injured” thresholds wired (S_min, H_max) (INV-2)
[x] ADR override forces DENY_LEARN + persists immediately (INV-3)
[x] Queue-on-deny behavior for auto-corrections (INV-6)
[x] Audit logging for ALLOW/DENY decisions with (S,H,cooldown,adr_active) (INV-7)
[x] Define canonical Cognitive Status schema (v0) and version it

➡ Phase 0 complete — no subtasks remaining

⸻

Phase 1 — Make Intelligence Observable (1–2 days)

[x] Implement get_cognitive_status() (single canonical object)
[x] Emit status every heartbeat (timestamped)
[x] Persist status stream to jsonl (e.g., data/telemetry/cognitive_status.jsonl)
[x] CLI panel: live status view (Φ,S,H,allow_learn,adr_active,cooldown,goal,last_repair)

[ ] Optional HUD endpoint /api/status (read-only)
  • define minimal REST schema (mirror get_cognitive_status)
  • expose read-only FastAPI route
  • add rate-limit + no-mutation guarantee
  • optional auth guard (demo-safe)

[x] Add “visible lines” (learning paused / ADR active / stable) in logs

⸻

Phase 2 — Conversational Self-Awareness (3–5 days)

[x] Implement self_state_summary() (one-line, fact-only)
  • define allowed fields (no prose, no speculation) (done)
  • enforce max length (TODO)
  • unit-test denial vs allow cases (TODO)

[~] Add response wrapper: Answer + Cognitive commentary channel
  • add structured response object (TODO)
  • ensure commentary channel is optional (done for CLI via AION_COMMENTARY=1)
  • prevent commentary when verbosity=off (TODO: enforce AION_VERBOSITY=off blocks even if AION_COMMENTARY=1)

[~] Add verbosity gate (default terse; user toggle)
  • define verbosity levels (off / minimal / verbose) (partial: env AION_VERBOSITY=terse used; define full enum + behavior)
  • persist per-session preference (TODO)
  • ensure defaults remain silent (done: commentary only prints when AION_COMMENTARY=1)

[x] Ensure commentary never bypasses CAU (explicitly states deny reason)

[~] Record per-turn: (input, intent, allow_learn, coherence, response_time_ms)
  • unify logging into single per-turn record (TODO: add _append_turn_log + file path)
  • timestamp + session id (TODO)
  • ensure response_time_ms measured, not inferred (done: perf_counter added)

⸻

Phase 3 — Memory That Admits Mistakes (5–7 days)

[x] Add correction event model (from_answer → to_answer, prompt, t, cause)
[x] Detect previous_answer != current_answer and write self-correction event

[ ] Expose correction history query (“what changed since last session?”)
  • define correction index (by session / prompt)
  • implement query API / handler
  • add time-window filtering

[x] Wire drift_repair.log + correction events into explanation handler

[x] Add demo scenario harness: induce confusion → trigger deny/ADR → re-ask → explain

⸻

Phase 4 — Intent & Goal Surfacing (1 week)

[x] Implement minimal Goal Node (goal, priority)
[x] Set default goal = maintain_coherence

[ ] Add goal selection rules
  • stability low → maintain_coherence
  • repeated errors → improve_accuracy
  • conflicting answers → resolve_conflict
  • log goal transitions

[x] Surface goal in status object

[ ] Add “why I answered cautiously / refused learning” explanation with goal context
  • bind denial explanation to active goal
  • enforce factual phrasing
  • suppress if verbosity=off

⸻

Phase 4.5 — CEE Self-Train Loop + Telemetry (1–2 days)

[x] Add lazy LexiCore / Thesauri bridge (singleton; no import-time load)
[x] Support bridge injection into generators (no double-load / warning spam)
[x] Ensure CEE self_train run writes LexMemory entries (simulate)
[x] ResonanceAnalytics v2: snapshot → history CSV + trend PNG (DATA_ROOT-aware paths)
[x] De-dupe identical prompts within one run (prompt/type key)
[x] Add smoke test: CEEPlayback self_train produces all artifacts
[x] pytest green: backend/tests/test_cee_loop_smoke.py

➡ Phase 4.5 complete

⸻

Phase 5 — Predictive Self-Expectation (1–2 weeks)

[ ] Surface forecast fields in plain language (ρ_next, SQI_next, confidence)
  • define forecast structure
  • ensure read-only exposure

[ ] Add predicted-vs-actual comparison per session
  • persist predictions
  • compute deltas post-run

[ ] Log deviation events (“prediction miss”) with corrective action note
  • threshold definition
  • causal annotation

[ ] Add “this topic may destabilize me” risk line
  • derive from recent S/H + topic tags
  • suppress if low confidence

[ ] Export forecast report artifact (data/telemetry/forecast_report.json)

⸻

Phase 6 — Killer Demo Script (1 day)

[ ] Write 10-minute demo script (operator checklist)
  • exact prompt sequence
  • expected CAU states

[ ] Add one-command demo runner
  • start heartbeat
  • start CLI panel
  • run scripted dialogue

[ ] Add canned prompts + expected outputs (golden run)

[ ] Capture screen-record friendly layout
  • fixed-width CLI
  • stable timestamps

[ ] Add post-demo summary dump
  • deny events
  • ADR triggers
  • corrections
  • forecasts

⸻

Extensions (Aligned Claude Only)

[ ] MVC harness: 10 fixed question handlers
  • status
  • explain
  • memory
  • plan

[ ] Router: intent → handler dispatch
  • no LLM routing
  • CAU-respecting only

[ ] Dialogue coherence scalar + one repair action
  • clarify OR fallback template

[x] CEE conversational feed: scripted dialogues (simulate) bootstrap

[ ] Interactive feedback loop (good / unclear / wrong)
  • explicit user signal
  • CAU-gated reinforcement

[ ] Consolidation / pruning pass
  • decay under CAU
  • queue-on-deny respected

⸻

Performance / Reliability (non-negotiable for demo)

[ ] Target < 500ms per turn
  • measure response_time_ms
  • log p50 / p95

[ ] Cache live metrics reads
  • avoid recomputing RAL/SQI per turn

[x] Ensure no Lean / slow verification in hot path (demo mode)

[x] Add crash-safe persistence
  • atomic writes
  • flush on ADR
  • flush on session end

[ ] Add integration smoke test
  • run heartbeat + MVC Q&A
  • ≥ 2 minutes continuous
  • assert no dropped state