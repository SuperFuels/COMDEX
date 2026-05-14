🛠 Mermaid Build Task Checklist (A7 + Temporal Framework)

flowchart TD

subgraph A7["⚪ A7: Mechanized Proofs + Temporal Framework"]
direction TB

  goal["🎯 Goal:
  - Lean/Coq/TLA+ ingestion pipeline
  - Works in Standalone + Integrated modes
  - WaveClock as core time model"]

  subgraph orig["📌 Original A7 Subtasks"]
    A71["Lean Parsing & Injection"]
    A72["Proof Visualization"]
    A73["Validation (logic trees)"]
    A74["Audit & Reporting"]
  end

  subgraph new["📌 New Subtasks (Standalone vs Integrated)"]
    subgraph standalone["Standalone Mode (Symatics-only)"]
      S1["Add --mode standalone (CLI) & mode=standalone (API)"]
      S2["Parse .lean → container JSON"]
      S3["Generate previews / Mermaid / PNG"]
      S4["Validate logic trees + temporal"]
      S5["Save reports (md/json)"]
      S6["Use shims (CodexLangRewriterShim, LocalRegistry)"]
    end

    subgraph integrated["Integrated Mode (Full Codex Stack)"]
      I1["Default: --mode integrated"]
      I2["Normalize logic via CodexLangRewriter"]
      I3["Run SQI scoring per theorem (+ temporal drift)"]
      I4["Attach mutation hooks"]
      I5["Register in symbolic_registry"]
      I6["Emit WebSocket events to SCI"]
      I7["Optional: QFC LightCone projection"]
    end
  end

  subgraph temporal["📌 Symatics Temporal Framework v0.1"]
    T1["Define WaveClock JSON schema"]
    T2["Add operators: phase(), sync(), normalize()"]
    T3["Implement sync protocol (ping-pair, freq est, PLL)"]
    T4["Integrate temporal validation (always saved in container)"]
    T5["Expose temporal errors at API & CLI"]
    T6["Add --normalize flag for CodexLang output in standalone"]
    T7["Update lean_inject_cli.py + lean_inject_api.py to handle wave_clock"]
  end

  subgraph impl["📌 Implementation Plan"]
    P1["Patch lean_inject_cli.py: --mode {standalone, integrated}"]
    P2["Patch lean_inject_api.py: mode field + temporal validation"]
    P3["Update lean_utils.py with shims"]
    P4["Update lean_watch.py: pass mode through"]
    P5["Prototype Python simulator (oscillator + Kalman)"]
    P6["Lab/network test (sync via UDP)"]
    P7["Publish RFC: Symatics Algebra Whitepaper v0.2 with Wave-Time section"]
  end

  goal --> orig --> new --> temporal --> impl
end

