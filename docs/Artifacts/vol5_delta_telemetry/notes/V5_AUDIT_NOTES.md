# Volume V Audit Notes (pre-lock)

- Goal: deterministic Δ-telemetry trace for λ–ψ–E coupling.
- Lock criteria: runner emits V5_TRACE.jsonl + V5_METRICS.json + V5_LINT_PROOF.log and self-checks determinism (same trace sha256 across two runs).
- This note is informational; Truth Chain uses the emitted artifacts as the verification surface.
