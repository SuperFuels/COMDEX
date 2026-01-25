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
[x] Persist status stream to jsonl (data/telemetry/cognitive_status.jsonl)
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
    • define allowed fields (no prose, no speculation)
    • enforce max length
    • unit-test denial vs allow cases
      (backend/tests/test_self_state_summary.py)

[~] Add response wrapper: Answer + Cognitive commentary channel
    • structured response object (TODO)
    • commentary channel optional (done: AION_COMMENTARY=1)
    • commentary hard-disabled when verbosity=off
      (backend/tests/test_commentary_verbosity_gate.py)

[x] Add verbosity gate (default terse; user toggle)
    • verbosity levels defined (off / minimal / terse / verbose)
    • defaults remain silent
    • commentary emitted only if explicitly enabled
    • per-session persistence (TODO)

[x] Ensure commentary never bypasses CAU
    • deny reason explicitly stated when learning blocked

[x] Record per-turn telemetry (TurnLog v1)
    • unified per-turn record
    • timestamp + session id
    • intent + coherence
    • response_time_ms via monotonic timer
    • schema tag enforced
      (backend/tests/test_turn_log_schema_v1.py)

⸻

Phase 3 — Memory That Admits Mistakes (5–7 days)

[x] Add correction event model
    (from_answer → to_answer, prompt, t, cause)

[x] Detect mismatches and self-corrections
    • wrong recall (correct=false)
    • auto-corrected memory
    • ADR-compatible

[x] Expose correction history query
    (“what changed since last session?”)
    • correction index by normalized prompt
    • session implicitly preserved in events
    • LexMemory primary, TurnLog fallback
    • mismatch extraction includes ALL wrong turns
    • non-informative rows skipped (guess=null AND answer=null)
    • stable de-duplication
      (source, session, t, from, to, cause)

[ ] Time-window filtering (since_ts / until_ts)
    • deferred as Phase 3.1

[x] Wire drift_repair.log + correction events
    into explanation / history output

[x] Demo harness
    • induce confusion
    • trigger deny / ADR
    • re-ask
    • show correction history

⸻

Phase 4 — Intent & Goal Surfacing (≈1 week)

[x] Implement minimal Goal Node
    • goal
    • priority

[x] Default goal = maintain_coherence
[x] Goal is now a real runtime variable (CEEPlayback.goal)
[x] Surface goal in cognitive status + self_state_summary()

[x] Goal transition rules (starter)
    • CAU stable (S>=0.85, H<=0.15) → improve_accuracy
    • log goal transitions → data/telemetry/goal_transition_log.jsonl (AION.GoalTransition.v1)
    • test locked → backend/tests/test_goal_transition_log_jsonl.py

[x] Extend transition rules (Phase 4+)
    • repeated error → improve_accuracy (recent window)
    • test locked → backend/tests/test_goal_transition_repeated_errors.py

[ ] Extend transition rules (next)
    • contradiction → resolve_conflict (mismatch detector + signal)
    • add causes taxonomy (rule_update / repeated_errors / contradiction / low_stability)

[x] Goal-aware explanations (denial binding)
    • bind denial explanation to active goal (deny_learn=1 goal=... deny_reason=...)
    • factual tokens only, single line (no prose)
    • suppressed when verbosity=off
    • test locked → backend/tests/test_denial_explanation_goal_gate.py
    • test locked → backend/tests/test_self_state_denial_goal_tokens.py

[ ] UI surfacing (optional)
    • show last goal transition in dashboard / playback UI
    • query goal_transition_log.jsonl by session / time window

⸻

⸻

Phase 4.5 — CEE Self-Train Loop + Telemetry (1–2 days)

[x] Lazy LexiCore / Thesauri bridge
[x] Injection-safe (no double load)
[x] Self-train writes LexMemory entries
[x] ResonanceAnalytics v2
    • snapshot
    • history CSV
    • trend PNG
    • DATA_ROOT aware

[x] De-dupe identical prompts within one run
[x] Smoke test: CEE self_train produces all artifacts
[x] pytest green
    (backend/tests/test_cee_loop_smoke.py)

➡ Phase 4.5 complete

⸻

Phase 5 — Predictive Self-Expectation (implemented)

[x] Forecast fields (ρ_next, SQI_next, confidence)
    • Schema defined: AION.Forecast.v1
    • Artifact: data/telemetry/forecast_report.jsonl
    • Emitted per turn, read-only (no learning semantics)
    • Test locked → backend/tests/test_forecast_report_jsonl.py

[x] Predicted vs actual comparison
    • Prior-turn forecast used as prediction
    • Current resonance used as observed
    • Deltas computed deterministically
    • Test locked → backend/tests/test_prediction_miss_log_jsonl.py

[x] Deviation events (“prediction miss”)
    • Artifact: data/telemetry/prediction_miss_log.jsonl
    • Thresholds (env-driven):
        – AION_FORECAST_MIN_CONF
        – AION_FORECAST_RHO_ERR
        – AION_FORECAST_SQI_ERR
    • Thresholds recorded in each event
    • Cause tagged as low-cardinality (“prediction_miss”)
    • Test locked → backend/tests/test_prediction_miss_log_jsonl.py

[x] Risk awareness line (confidence-gated)
    • Artifact: data/telemetry/risk_awareness_log.jsonl
    • Derived from CAU S/H + topic tags
    • Gated by:
        – AION_RISK_MIN_CONF
        – AION_RISK_MIN_SCORE
    • Suppressed when confidence is insufficient
    • Read-only, factual telemetry only
    • Test locked → backend/tests/test_risk_awareness_log_jsonl.py

[x] Forecast report artifact (per-session rollup)
    • Artifact: data/telemetry/forecast_report.json
    • Schema: AION.ForecastReport.v1
    • Aggregates:
        – forecast_report.jsonl
        – prediction_miss_log.jsonl
        – risk_awareness_log.jsonl
    • Emitted at end-of-run in CEEPlayback.finalize()
    • Includes counts, averages, and thresholds used
    • Test locked → backend/tests/test_forecast_report_summary_json.py
⸻

Phase 6 — Killer Demo Script (1 day)

[ ] 10-minute demo script
    • exact prompts
    • expected CAU states

[ ] One-command demo runner
    • heartbeat
    • CLI panel
    • scripted dialogue

[ ] Golden run prompts + outputs
[ ] Screen-record-friendly layout
[ ] Post-demo summary dump
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

Performance / Reliability (demo-critical)

[ ] Target <500ms per turn
    • log p50 / p95

[ ] Cache live metric reads
[x] No Lean / heavy verification in hot path
[x] Crash-safe persistence
    • atomic writes
    • flush on ADR
    • flush on session end

[ ] Integration smoke test
    • heartbeat + MVC Q&A
    • ≥2 minutes continuous
    • no dropped state