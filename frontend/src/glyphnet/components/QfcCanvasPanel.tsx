import React, { useEffect, useMemo, useRef, useState } from "react";

/**
 * Shared, top-of-page QFC canvas panel.
 * This is the ONLY component shared by QFC HUD and QFC Bio pages.
 *
 * Notes:
 * - This is intentionally self-contained and minimal.
 * - Wire it to your real telemetry stream by replacing the mocked frame source below.
 */

export type QfcFrame = {
  mode: string;               // e.g. "genome" | "wormhole"
  telemetry: string;          // e.g. "live" | "replay"
  kappa: number;
  chi: number;
  sigma: number;
  alpha: number;
  gate: number;
  epoch: number;
  topoNodes: number;
  topoEdges: number;
  channel: string;            // e.g. "CH:+1"
};

export type QfcProvenance = {
  runId?: string;
  scenarioId?: string;
  execMode?: "A" | "B";
  sqiEnabled?: boolean;
  seed?: number;
  gitRevShort?: string;
  inputBundleHash?: string;
  traceDigestShort?: string;
  artifactsOk?: boolean;
  replayCmd?: string;
};

type Props = {
  title?: string;
  // Optional: feed in real values from parent if you already have telemetry plumbing.
  frame?: Partial<QfcFrame>;
  provenance?: Partial<QfcProvenance>;
  // Hook points for buttons (no-ops by default).
  onCaptureFrame?: () => void;
  onSaveTraceSlice?: () => void;
  onExportSnapshot?: () => void;
  onVerifySnapshot?: () => void;
  onCopyReplayCmd?: () => void;
};

function fmt(n: number, digits = 4) {
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(digits);
}

function shortHash(h?: string, n = 10) {
  if (!h) return "—";
  return h.length <= n ? h : h.slice(0, n) + "…";
}

export default function QfcCanvasPanel({
  title = "QFC Canvas (live frame viewer)",
  frame,
  provenance,
  onCaptureFrame,
  onSaveTraceSlice,
  onExportSnapshot,
  onVerifySnapshot,
  onCopyReplayCmd,
}: Props) {
  // ---------------------------------------------------------------------------
  // TEMP MOCK: replace with your real telemetry -> qfc frame wiring.
  // If parents pass frame/provenance, those override the mock.
  // ---------------------------------------------------------------------------
  const [mockTick, setMockTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setMockTick((x) => (x + 1) % 10_000), 500);
    return () => clearInterval(t);
  }, []);

  const computedFrame: QfcFrame = useMemo(() => {
    const base: QfcFrame = {
      mode: "genome",
      telemetry: "live",
      kappa: 0.0074,
      chi: 0.2375,
      sigma: 0.9044,
      alpha: 0.9482,
      gate: 0.904,
      epoch: 883808010 + mockTick,
      topoNodes: 10,
      topoEdges: 14,
      channel: "CH:+1",
    };
    return { ...base, ...frame } as QfcFrame;
  }, [frame, mockTick]);

  const computedProv: QfcProvenance = useMemo(() => {
    const base: QfcProvenance = {
      runId: "P21_GX1_…",
      scenarioId: "GN01",
      execMode: "A",
      sqiEnabled: false,
      seed: 1337,
      gitRevShort: "6141b8f…",
      inputBundleHash: "9ac3…",
      traceDigestShort: "2bb357…",
      artifactsOk: true,
      replayCmd: "python -m backend.genome_engine.run_genomics_benchmark --config <CONFIG.json>",
    };
    return { ...base, ...provenance };
  }, [provenance]);

  // ---------------------------------------------------------------------------
  // Canvas placeholder: if you already have a WebGL canvas component, replace
  // this block with your existing canvas element or renderer.
  // ---------------------------------------------------------------------------
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    const { width, height } = c;
    ctx.clearRect(0, 0, width, height);

    // Simple placeholder visual: grid + helix line
    ctx.fillStyle = "#0b0f1a";
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = "rgba(255,255,255,0.07)";
    for (let x = 0; x < width; x += 24) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += 24) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Helix-ish curve reacting to alpha/sigma (placeholder)
    ctx.strokeStyle = "rgba(140,80,255,0.9)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    for (let i = 0; i < 300; i++) {
      const t = i / 299;
      const x = width * 0.5 + Math.sin(t * Math.PI * 6 + mockTick * 0.04) * (80 + computedFrame.sigma * 40);
      const y = height * (0.15 + t * 0.7);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    ctx.fillStyle = "rgba(255,255,255,0.85)";
    ctx.font = "12px ui-monospace, SFMono-Regular, Menlo, monospace";
    ctx.fillText(`${computedFrame.mode} • ${computedFrame.telemetry} • ${computedFrame.channel}`, 12, 18);
  }, [computedFrame.alpha, computedFrame.sigma, computedFrame.mode, computedFrame.telemetry, computedFrame.channel, mockTick]);

  // ---------------------------------------------------------------------------
  // UI
  // ---------------------------------------------------------------------------
  return (
    <section style={{ marginBottom: 18 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <h2 style={{ margin: "6px 0", fontSize: 18 }}>{title}</h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button onClick={onCaptureFrame} style={btnStyle}>Capture frame</button>
          <button onClick={onSaveTraceSlice} style={btnStyle}>Save trace slice</button>
        </div>
      </div>

      <div style={{ borderRadius: 12, overflow: "hidden", border: "1px solid rgba(255,255,255,0.08)" }}>
        <canvas ref={canvasRef} width={1400} height={520} style={{ width: "100%", display: "block" }} />
        {/* chip row */}
        <div style={{ background: "rgba(10,14,24,0.95)", padding: "10px 12px", display: "flex", gap: 10, flexWrap: "wrap" }}>
          <span style={chipStyle}>{`mode:${computedFrame.mode}`}</span>
          <span style={chipStyle}>{`telemetry:${computedFrame.telemetry}`}</span>
          <span style={chipStyle}>{`kappa:${fmt(computedFrame.kappa)}`}</span>
          <span style={chipStyle}>{`chi:${fmt(computedFrame.chi)}`}</span>
          <span style={chipStyle}>{`sigma:${fmt(computedFrame.sigma)}`}</span>
          <span style={chipStyle}>{`alpha:${fmt(computedFrame.alpha)}`}</span>
          <span style={chipStyle}>{`gate:${fmt(computedFrame.gate, 3)}`}</span>
          <span style={chipStyle}>{`epoch:${computedFrame.epoch}`}</span>
          <span style={chipStyle}>{`topo:n=${computedFrame.topoNodes} e=${computedFrame.topoEdges}`}</span>
          <span style={chipStyle}>{computedFrame.channel}</span>
        </div>
      </div>

      {/* Under-canvas defensible tri-pane */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr", gap: 12, marginTop: 12 }}>
        {/* Pane 1 Provenance */}
        <div style={cardStyle}>
          <h3 style={h3Style}>1) Provenance</h3>
          <dl style={dlStyle}>
            <Row k="run_id" v={computedProv.runId ?? "—"} />
            <Row k="scenario" v={`${computedProv.scenarioId ?? "—"}  exec:${computedProv.execMode ?? "—"}  sqi:${computedProv.sqiEnabled ? "ON" : "OFF"}`} />
            <Row k="seed" v={computedProv.seed ?? "—"} />
            <Row k="git_rev" v={computedProv.gitRevShort ?? "—"} />
            <Row k="input_bundle_hash" v={computedProv.inputBundleHash ?? "—"} />
            <Row k="trace_digest" v={computedProv.traceDigestShort ?? "—"} />
            <Row k="artifacts" v={computedProv.artifactsOk ? "phase ✅  run ✅" : "—"} />
          </dl>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
            <button
              onClick={() => {
                if (onCopyReplayCmd) return onCopyReplayCmd();
                if (computedProv.replayCmd) navigator.clipboard?.writeText(computedProv.replayCmd);
              }}
              style={btnStyle}
              title="Copy replay command"
            >
              Copy replay cmd
            </button>
          </div>
        </div>

        {/* Pane 2 Frame Values */}
        <div style={cardStyle}>
          <h3 style={h3Style}>2) Frame Values</h3>
          <dl style={dlStyle}>
            <Row k="kappa" v={fmt(computedFrame.kappa)} />
            <Row k="chi" v={fmt(computedFrame.chi)} />
            <Row k="sigma" v={fmt(computedFrame.sigma)} />
            <Row k="alpha" v={fmt(computedFrame.alpha)} />
            <Row k="gate" v={fmt(computedFrame.gate, 3)} />
            <Row k="epoch" v={computedFrame.epoch} />
            <Row k="nodes" v={computedFrame.topoNodes} />
            <Row k="edges" v={computedFrame.topoEdges} />
          </dl>
          <div style={{ opacity: 0.7, fontSize: 12, marginTop: 8 }}>
            Rule: if a number is not shown here, it MUST NOT drive the visual.
          </div>
        </div>

        {/* Pane 3 Outputs */}
        <div style={cardStyle}>
          <h3 style={h3Style}>3) Outputs</h3>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button onClick={onVerifySnapshot} style={btnStyle}>Verify snapshot</button>
            <button onClick={onExportSnapshot} style={btnStyle}>Export snapshot</button>
          </div>
          <div style={{ marginTop: 10, fontSize: 13, opacity: 0.85 }}>
            Downloads (wired in Bio page): TRACE / METRICS / REPLAY / Evidence bundle
          </div>
          <div style={{ marginTop: 10, fontSize: 13, opacity: 0.85 }}>
            Artifact ladder (wired in Bio page): run-local + phase-level indexes and sha256
          </div>
        </div>
      </div>
    </section>
  );
}

function Row({ k, v }: { k: string; v: any }) {
  return (
    <>
      <dt style={dtStyle}>{k}</dt>
      <dd style={ddStyle}>{typeof v === "string" ? v : String(v)}</dd>
    </>
  );
}

const btnStyle: React.CSSProperties = {
  padding: "8px 10px",
  borderRadius: 10,
  border: "1px solid rgba(255,255,255,0.12)",
  background: "rgba(255,255,255,0.06)",
  color: "white",
  cursor: "pointer",
  fontSize: 13,
};

const chipStyle: React.CSSProperties = {
  padding: "4px 8px",
  borderRadius: 999,
  border: "1px solid rgba(255,255,255,0.10)",
  background: "rgba(255,255,255,0.06)",
  fontSize: 12,
  color: "rgba(255,255,255,0.92)",
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
};

const cardStyle: React.CSSProperties = {
  borderRadius: 12,
  border: "1px solid rgba(255,255,255,0.08)",
  background: "rgba(10,14,24,0.55)",
  padding: 12,
};

const h3Style: React.CSSProperties = {
  margin: "0 0 10px 0",
  fontSize: 14,
  opacity: 0.9,
};

const dlStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "170px 1fr",
  gap: "6px 10px",
  margin: 0,
};

const dtStyle: React.CSSProperties = {
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
  fontSize: 12,
  opacity: 0.7,
};

const ddStyle: React.CSSProperties = {
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
  fontSize: 12,
  margin: 0,
  color: "rgba(255,255,255,0.92)",
};
