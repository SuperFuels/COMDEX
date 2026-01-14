// Glyph_Net_Browser/src/components/QFCViewport.tsx
"use client";

import { useEffect, useRef } from "react";
import type { CSSProperties } from "react";

// ✅ LIVE TELEMETRY HOOK (auto-bind)
// If your project doesn't support "@/...", change to: "../hooks/useTessarisTelemetry"
import { useTessarisTelemetry } from "@/hooks/useTessarisTelemetry";
import type { TessarisTelemetry } from "@/hooks/useTessarisTelemetry";

type QFCMode = "gravity" | "tunnel" | "matter" | "connect" | "antigrav" | "sync";

type QFCTheme = {
  gravity?: string;
  matter?: string;
  photon?: string;
  connect?: string;
  danger?: string;
  antigrav?: string;
  sync?: string;
};

type QFCFlags = {
  nec_violation?: boolean;
  nec_strength?: number; // 0..1
  jump_flash?: number; // 0..1
};

type QFCFrame = {
  t: number;

  // metrics (existing)
  kappa?: number;
  chi?: number;
  sigma?: number;
  alpha?: number;
  curl_rms?: number;
  curv?: number;
  coupling_score?: number;
  max_norm?: number;

  // injected by backend renderer (new)
  mode?: QFCMode;
  theme?: QFCTheme;
  flags?: QFCFlags;
};

type QFCViewportProps = {
  title?: string;
  subtitle?: string;
  rightBadge?: string;

  // you can still force these, but if frame carries them, frame wins
  mode?: QFCMode;
  theme?: QFCTheme;

  frame?: QFCFrame | null;
  frames?: QFCFrame[];

  // ✅ optional: provide telemetry explicitly (otherwise uses the hook)
  telemetry?: TessarisTelemetry;

  // optional toggles
  bloom?: boolean;
  bloomStrength?: number; // 0.15–0.35 sweet spot
  bloomBlur?: number; // 8–16 sweet spot
};

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const num = (v: any, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);

// alpha helper (rgba/rgb -> rgba with new alpha; hex/named unchanged)
const withAlpha = (c: string, a: number) => {
  const aa = String(Math.max(0, Math.min(1, a)));
  if (!c) return `rgba(255,255,255,${aa})`;
  if (c.startsWith("rgba("))
    return c.replace(
      /rgba\(([^)]+),\s*[\d.]+\s*\)/,
      `rgba($1, ${aa})`,
    );
  if (c.startsWith("rgb("))
    return c.replace(/rgb\(([^)]+)\)/, `rgba($1, ${aa})`);
  return c;
};

// ✅ Map live telemetry -> QFCFrame
function buildQfcFrameFromTelemetry(t: TessarisTelemetry): QFCFrame | null {
  if (!t) return null;

  const analytics: any = t.analytics ?? {};
  const fusion: any = t.fusion ?? {};

  // rqfs can be {state:{...}} or flat; tolerate both
  const rqfsAny: any = (t as any).rqfs ?? {};
  const rqfsState: any = rqfsAny?.state ?? rqfsAny ?? {};

  // Optional “renderer output” if you later add it
  const qfcAny: any =
    (t as any).qfc ??
    fusion?.qfc ??
    analytics?.qfc ??
    {};

  const flags: QFCFlags =
    (qfcAny.flags as QFCFlags) ??
    (fusion?.flags as QFCFlags) ??
    {};

  const theme: QFCTheme =
    (qfcAny.theme as QFCTheme) ??
    (fusion?.theme as QFCTheme) ??
    {};

  const mode: QFCMode | undefined =
    (qfcAny.mode as QFCMode) ??
    (fusion?.mode as QFCMode) ??
    undefined;

  // Primary metrics: prefer fusion / rqfs.state; fallback to analytics
  const kappa = num(rqfsState.nu_bias ?? rqfsState.kappa ?? analytics.mean_nu, 0);
  const chi = num(rqfsState.phi_bias ?? rqfsState.chi ?? analytics.mean_phi, 0);
  const sigma = num(rqfsState.amp_bias ?? rqfsState.sigma ?? analytics.mean_amp, 0);

  // ---- ψ̃ (cognitive wave) ----
  // TCFK now emits: ψ̃, psi_tilde, cognition_signal
  const psiRaw = num(
    fusion["ψ̃"] ??
      fusion.psi_tilde ??
      fusion.cognition_signal ??
      fusion.inference_strength ??
      fusion.signal,
    NaN,
  );

  // Renderer visuals want 0..1; cognition_signal is typically -1..1.
  const psi01 = Number.isFinite(psiRaw) ? clamp01(0.5 + 0.5 * psiRaw) : NaN;

  // Use ψ̃ if present; otherwise fall back to existing fusion_score/alpha/etc.
  const alpha = num(
    Number.isFinite(psi01)
      ? psi01
      : (fusion.fusion_score ?? fusion.fusion ?? fusion.alpha ?? analytics.stability),
    0,
  );

  // ---- κ̃ (resonance field) ----
  // TCFK now emits: κ̃, kappa_tilde, curl_rms, curv
  const curl_rms = num(
    fusion["κ̃"] ??
      fusion.kappa_tilde ??
      fusion.curl_rms ??
      fusion.curl ??
      analytics.curl_rms,
    0,
  );

  const curv = num(
    fusion.curv ?? fusion.curvature ?? analytics.curv ?? analytics.curvature,
    0,
  );

  const coupling_score = num(
    fusion.coupling_score ?? fusion.coupling ?? analytics.coupling_score ?? analytics.stability,
    0,
  );

  const max_norm = num(fusion.max_norm ?? analytics.max_norm, 0);

  // Use telemetry timestamps if present, else Date.now()
  // (We just need monotonic-ish t for history deltas / flash logic.)
  const ts =
    (typeof analytics.timestamp === "string" && Date.parse(analytics.timestamp)) ||
    (typeof fusion.timestamp === "string" && Date.parse(fusion.timestamp)) ||
    Date.now();

  return {
    t: ts,
    kappa,
    chi,
    sigma,
    alpha,
    curl_rms,
    curv,
    coupling_score,
    max_norm,
    mode,
    theme,
    flags,
  };
}

export default function QFCViewport(props: QFCViewportProps) {
  const {
    title = "QFC HUD",
    subtitle,
    rightBadge,
    mode = "gravity",
    theme,
    frame,
    frames,
    telemetry: telemetryProp,
    bloom = true,
    bloomStrength = 0.22,
    bloomBlur = 12,
  } = props;

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // ✅ auto-bind to live telemetry unless caller passes telemetry explicitly
  const liveTelemetry = useTessarisTelemetry();
  const telemetry = telemetryProp ?? liveTelemetry;

  // ✅ internal live history when frame/frames props aren't supplied
  const liveFrameRef = useRef<QFCFrame | null>(null);
  const liveFramesRef = useRef<QFCFrame[]>([]);

  // latest values without restarting RAF
  const latestRef = useRef<{
    mode: QFCMode;
    theme: QFCTheme;
    frame: QFCFrame | null;
    frames: QFCFrame[];
    bloom: boolean;
    bloomStrength: number;
    bloomBlur: number;
  }>({
    mode,
    theme: theme ?? {},
    frame: frame ?? null,
    frames: Array.isArray(frames) ? frames : [],
    bloom,
    bloomStrength,
    bloomBlur,
  });

  useEffect(() => {
    // baseline from props
    latestRef.current.mode = mode;
    latestRef.current.theme = theme ?? {};
    latestRef.current.frame = frame ?? null;
    latestRef.current.frames = Array.isArray(frames) ? frames : [];
    latestRef.current.bloom = bloom;
    latestRef.current.bloomStrength = bloomStrength;
    latestRef.current.bloomBlur = bloomBlur;
  }, [mode, theme, frame, frames, bloom, bloomStrength, bloomBlur]);

  // ✅ If caller did NOT supply frame/frames, synthesize them from live telemetry
  useEffect(() => {
    // explicit props win (renderer remains a pure viewport when controlled)
    const hasExternalFrames =
      frame !== undefined || (Array.isArray(frames) && frames.length > 0);
    if (hasExternalFrames) return;

    if (!telemetry) return;

    const fr = buildQfcFrameFromTelemetry(telemetry);
    if (!fr) return;

    const hist = liveFramesRef.current;
    const last = hist.length ? hist[hist.length - 1] : null;

    if (!last || last.t !== fr.t) {
      hist.push(fr);
      if (hist.length > 240) hist.splice(0, hist.length - 240);
    } else {
      hist[hist.length - 1] = fr;
    }

    liveFrameRef.current = fr;

    // update the RAF snapshot source
    latestRef.current.frame = fr;
    latestRef.current.frames = hist;
  }, [telemetry, frame, frames]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // offscreen buffer for bloom (cheap)
    const buffer = document.createElement("canvas");
    const bctx = buffer.getContext("2d");
    if (!bctx) return;

    let raf = 0;
    let warned = false;

    // cached dims (avoid getBoundingClientRect per frame)
    let vw = 1;
    let vh = 1;
    let dpr = 1;

    const resize = () => {
      dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
      const r = canvas.getBoundingClientRect();
      vw = Math.max(1, Math.floor(r.width));
      vh = Math.max(1, Math.floor(r.height));

      canvas.width = Math.max(1, Math.floor(vw * dpr));
      canvas.height = Math.max(1, Math.floor(vh * dpr));
      buffer.width = canvas.width;
      buffer.height = canvas.height;

      // draw in CSS pixels
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      bctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    let lastFlash = 0;

    const draw = (ts: number) => {
      try {
        const snap = latestRef.current;
        const fr = snap.frame;
        const fs = snap.frames;

        // IMPORTANT: frame-provided renderer output wins
        const m: QFCMode = (fr?.mode as QFCMode) ?? snap.mode;
        const th: QFCTheme = (fr?.theme as QFCTheme) ?? snap.theme;
        const flags: QFCFlags = (fr?.flags as QFCFlags) ?? {};

        const w = vw;
        const h = vh;
        if (w <= 2 || h <= 2) {
          raf = requestAnimationFrame(draw);
          return;
        }

        // metrics
        const kappa = clamp01(num(fr?.kappa, 0.12));
        const chi = clamp01(num(fr?.chi, 0.22));
        const sigma = clamp01(num(fr?.sigma, 0.55));
        const alpha = clamp01(num(fr?.alpha, 0.12));
        const curv = clamp01(num(fr?.curv, 0.18));
        const curl = clamp01(num(fr?.curl_rms, 0.03) * 10);
        const coupling = clamp01(num(fr?.coupling_score, 0.55));

        // flash: prefer backend renderer’s jump_flash (more stable), fallback to local coupling delta
        let flash = clamp01(num(flags.jump_flash, -1));
        if (flash < 0) {
          const n = fs.length;
          const prev = n >= 2 ? fs[n - 2] : null;
          const prevCoupling = clamp01(num(prev?.coupling_score, coupling));
          const delta = Math.abs(coupling - prevCoupling);
          if (delta > 0.1) lastFlash = ts;
          flash = clamp01(1 - (ts - lastFlash) / 350);
        }

        const nec = clamp01(num(flags.nec_strength, 0));
        const necHot = !!flags.nec_violation;

        // draw base scene into buffer
        bctx.clearRect(0, 0, w, h);
        bctx.fillStyle = "rgba(2,6,23,0.18)";
        bctx.fillRect(0, 0, w, h);

        const centerX = w * (0.48 + 0.05 * Math.sin(ts / 1200));
        const centerY = h * (0.52 + 0.04 * Math.cos(ts / 1400));

        // ===== gravity =====
        if (m === "gravity") {
          const col = th.gravity ?? "rgba(56,189,248,0.70)";
          const intensity = clamp01(curv * 1.2 + kappa * 1.1);

          const r = Math.max(w, h) * (0.55 + 0.25 * intensity);
          const g = bctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, r);
          g.addColorStop(0, withAlpha(col, 0.2 + 0.26 * intensity));
          g.addColorStop(0.35, withAlpha(col, 0.12 + 0.16 * intensity));
          g.addColorStop(1, "rgba(0,0,0,0)");
          bctx.fillStyle = g;
          bctx.fillRect(0, 0, w, h);

          bctx.globalAlpha = 0.55;
          for (let i = 1; i <= 5; i++) {
            const rr = (r * i) / 7;
            bctx.beginPath();
            bctx.arc(centerX, centerY, rr, 0, Math.PI * 2);
            bctx.strokeStyle = "rgba(226,232,240,0.10)";
            bctx.lineWidth = 1;
            bctx.stroke();
          }
          bctx.globalAlpha = 1;

          bctx.globalAlpha = 0.65;
          bctx.beginPath();
          bctx.moveTo(centerX, 0);
          bctx.lineTo(centerX, h);
          bctx.strokeStyle = "rgba(226,232,240,0.06)";
          bctx.lineWidth = 2;
          bctx.stroke();
          bctx.globalAlpha = 1;
        }

        // ===== matter (BRIGHTER) =====
        if (m === "matter") {
          const col = th.matter ?? "rgba(226,232,240,0.90)";
          const density = clamp01(0.35 + chi * 0.85);

          const blobCount = 9;
          for (let i = 0; i < blobCount; i++) {
            const t = ts / 1000;
            const px =
              w *
              (0.12 +
                0.76 *
                  (0.5 + 0.5 * Math.sin(t * (0.45 + i * 0.08) + i)));
            const py =
              h *
              (0.16 +
                0.72 *
                  (0.5 + 0.5 * Math.cos(t * (0.4 + i * 0.06) + i * 1.7)));
            const rr =
              Math.min(w, h) *
              (0.12 + 0.18 * density) *
              (0.6 + 0.5 * Math.sin(t * (0.9 + i * 0.12)));

            const gg = bctx.createRadialGradient(px, py, 0, px, py, rr);
            gg.addColorStop(0, withAlpha(col, 0.18 + 0.3 * density));
            gg.addColorStop(0.55, withAlpha(col, 0.06 + 0.12 * density));
            gg.addColorStop(1, "rgba(0,0,0,0)");

            bctx.fillStyle = gg;
            bctx.beginPath();
            bctx.arc(px, py, rr, 0, Math.PI * 2);
            bctx.fill();
          }

          bctx.globalAlpha = 0.75;
          const y = h * (0.22 + 0.55 * (0.5 + 0.5 * Math.sin(ts / 1600)));
          bctx.fillStyle = "rgba(226,232,240,0.08)";
          bctx.fillRect(0, y, w, 2);
          bctx.globalAlpha = 1;
        }

        // ===== tunnel =====
        if (m === "tunnel") {
          const photon = th.photon ?? "rgba(251,191,36,0.80)";
          const danger = th.danger ?? "rgba(239,68,68,0.85)";

          const bandX = w * (0.62 + 0.14 * Math.sin(ts / 2200 + alpha * 6));
          const bandW = w * (0.12 + 0.12 * alpha);
          const rg = bctx.createLinearGradient(bandX - bandW, 0, bandX + bandW, 0);
          rg.addColorStop(0, "rgba(0,0,0,0)");
          rg.addColorStop(0.45, withAlpha(danger, 0.12 + 0.2 * (0.4 + alpha)));
          rg.addColorStop(0.55, withAlpha(danger, 0.14 + 0.24 * (0.4 + alpha)));
          rg.addColorStop(1, "rgba(0,0,0,0)");
          bctx.fillStyle = rg;
          bctx.fillRect(0, 0, w, h);

          bctx.globalAlpha = 0.85;
          bctx.beginPath();
          const mid = h * 0.52;
          const amp = h * (0.06 + 0.1 * sigma);
          const freq = 0.01 + 0.018 * sigma;
          const speed = 0.0028 + 0.002 * sigma;

          for (let x = 0; x <= w; x += 6) {
            const y =
              mid +
              Math.sin(x * freq + ts * speed) * amp +
              Math.sin(x * (freq * 0.45) - ts * (speed * 1.3)) * (amp * 0.35);
            if (x === 0) bctx.moveTo(x, y);
            else bctx.lineTo(x, y);
          }

          bctx.strokeStyle = photon;
          bctx.lineWidth = 3;
          bctx.stroke();

          bctx.globalAlpha = 0.22;
          bctx.strokeStyle = withAlpha(photon, 0.18);
          bctx.lineWidth = 2;
          bctx.beginPath();
          bctx.moveTo(0, mid - amp * 1.6);
          bctx.lineTo(w, mid - amp * 0.9);
          bctx.moveTo(0, mid + amp * 1.6);
          bctx.lineTo(w, mid + amp * 0.9);
          bctx.stroke();
          bctx.globalAlpha = 1;

          if (flash > 0) {
            bctx.globalAlpha = 0.55 * flash;
            bctx.fillStyle = withAlpha(photon, 0.35);
            bctx.fillRect(0, 0, w, h);
            bctx.globalAlpha = 1;
          }
        }

        // ===== connect =====
        if (m === "connect") {
          const col = th.connect ?? "rgba(34,211,238,0.85)";

          const nodeCount = 6;
          const nodes = Array.from({ length: nodeCount }).map((_, i) => {
            const t = ts / 1000;
            const px =
              w *
              (0.18 +
                0.64 *
                  (0.5 + 0.5 * Math.sin(t * (0.35 + i * 0.07) + i * 1.9)));
            const py =
              h *
              (0.22 +
                0.58 *
                  (0.5 + 0.5 * Math.cos(t * (0.31 + i * 0.05) + i * 1.3)));
            return { x: px, y: py };
          });

          bctx.globalAlpha = 0.75;
          bctx.lineWidth = 2;
          bctx.strokeStyle = col;
          for (let i = 0; i < nodeCount - 1; i++) {
            const a = nodes[i];
            const b = nodes[(i + 2) % nodeCount];
            const mx = (a.x + b.x) / 2 + w * 0.06 * Math.sin(ts / 700 + i);
            const my = (a.y + b.y) / 2 + h * 0.07 * Math.cos(ts / 850 + i);

            bctx.beginPath();
            bctx.moveTo(a.x, a.y);
            bctx.quadraticCurveTo(mx, my, b.x, b.y);
            bctx.stroke();
          }
          bctx.globalAlpha = 1;

          for (let i = 0; i < nodeCount; i++) {
            const n0 = nodes[i];
            const rr = 4 + 6 * coupling;
            const gg = bctx.createRadialGradient(n0.x, n0.y, 0, n0.x, n0.y, rr * 3);
            gg.addColorStop(0, withAlpha(col, 0.35));
            gg.addColorStop(1, "rgba(0,0,0,0)");
            bctx.fillStyle = gg;
            bctx.beginPath();
            bctx.arc(n0.x, n0.y, rr * 3, 0, Math.PI * 2);
            bctx.fill();
          }

          if (flash > 0) {
            bctx.globalAlpha = 0.45 * flash;
            bctx.fillStyle = withAlpha(col, 0.25);
            bctx.fillRect(0, 0, w, h);
            bctx.globalAlpha = 1;
          }
        }

        // ===== antigrav (optional visual for NEC bubble) =====
        if (m === "antigrav" || nec > 0.01) {
          const col = th.antigrav ?? "rgba(34,197,94,0.90)";
          const strength = m === "antigrav" ? clamp01(0.35 + nec * 0.65) : clamp01(nec);

          const r0 = Math.min(w, h) * (0.1 + 0.18 * strength);
          const r1 = Math.min(w, h) * (0.32 + 0.22 * strength);

          const g = bctx.createRadialGradient(centerX, centerY, r0, centerX, centerY, r1);
          g.addColorStop(0, withAlpha(col, 0.0));
          g.addColorStop(0.35, withAlpha(col, 0.1 + 0.16 * strength));
          g.addColorStop(0.75, withAlpha(col, 0.04 + 0.08 * strength));
          g.addColorStop(1, "rgba(0,0,0,0)");

          bctx.save();
          bctx.globalCompositeOperation = "screen";
          bctx.fillStyle = g;
          bctx.fillRect(0, 0, w, h);
          bctx.restore();

          if (necHot) {
            bctx.globalAlpha = 0.35;
            bctx.fillStyle = "rgba(239,68,68,0.10)";
            bctx.fillRect(0, 0, w, h);
            bctx.globalAlpha = 1;
          }
        }

        // ===== sync =====
        if (m === "sync") {
          const col = th.sync ?? "rgba(255,255,255,0.85)";
          bctx.save();
          bctx.globalAlpha = 0.55;
          bctx.strokeStyle = col;
          bctx.lineWidth = 2;

          const turns = 3;
          const maxR = Math.min(w, h) * 0.36;
          const t0 = ts / 1000;

          bctx.beginPath();
          for (let i = 0; i <= 220; i++) {
            const tt = i / 220;
            const ang = tt * Math.PI * 2 * turns + t0 * (0.65 + 0.35 * clamp01(coupling));
            const rr = tt * maxR * (0.85 + 0.15 * Math.sin(t0 * 0.9));
            const x = centerX + Math.cos(ang) * rr;
            const y = centerY + Math.sin(ang) * rr;
            if (i === 0) bctx.moveTo(x, y);
            else bctx.lineTo(x, y);
          }
          bctx.stroke();
          bctx.restore();
        }

        // subtle “health” overlay
        const health = clamp01(0.35 + coupling * 0.45 - curl * 0.25);
        bctx.globalAlpha = 0.35;
        bctx.fillStyle = `rgba(34,197,94,${0.05 + 0.08 * health})`;
        bctx.fillRect(0, h * 0.78, w, h * 0.22);
        bctx.globalAlpha = 1;

        // present to screen
        ctx.clearRect(0, 0, w, h);
        ctx.filter = "none";
        ctx.globalCompositeOperation = "source-over";
        ctx.globalAlpha = 1;
        ctx.drawImage(buffer, 0, 0, w, h);

        // bloom pass (cheap)
        if (snap.bloom) {
          ctx.save();
          ctx.globalCompositeOperation = "screen";
          ctx.globalAlpha = clamp01(snap.bloomStrength);
          ctx.filter = `blur(${Math.max(0, snap.bloomBlur)}px)`;
          ctx.drawImage(buffer, 0, 0, w, h);
          ctx.restore();
        }
      } catch (e) {
        if (!warned) {
          warned = true;
          console.error("QFCViewport draw() error (RAF will continue):", e);
        }
      } finally {
        raf = requestAnimationFrame(draw);
      }
    };

    raf = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, []);

  const shell: CSSProperties = {
    height: "100%",
    width: "100%",
    borderRadius: 14,
    overflow: "hidden",
    border: "1px solid rgba(148,163,184,0.35)",
    background:
      "radial-gradient(1200px 600px at 20% 10%, rgba(56,189,248,0.18), transparent 55%)," +
      "radial-gradient(1000px 500px at 80% 20%, rgba(34,197,94,0.10), transparent 55%)," +
      "linear-gradient(180deg, rgba(2,6,23,0.88), rgba(15,23,42,0.78))",
    position: "relative",
  };

  const grid: CSSProperties = {
    position: "absolute",
    inset: 0,
    backgroundImage:
      "linear-gradient(rgba(148,163,184,0.12) 1px, transparent 1px)," +
      "linear-gradient(90deg, rgba(148,163,184,0.12) 1px, transparent 1px)",
    backgroundSize: "52px 52px",
    transform: "perspective(800px) rotateX(65deg) translateY(140px)",
    transformOrigin: "center bottom",
    opacity: 0.35,
    pointerEvents: "none",
  };

  const vignette: CSSProperties = {
    position: "absolute",
    inset: 0,
    background:
      "radial-gradient(closest-side at 50% 40%, transparent 55%, rgba(0,0,0,0.65) 100%)",
    pointerEvents: "none",
  };

  const header: CSSProperties = {
    position: "absolute",
    top: 10,
    left: 12,
    right: 12,
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 10,
    color: "rgba(226,232,240,0.92)",
    zIndex: 5,
  };

  const titleStyle: CSSProperties = {
    fontSize: 12,
    fontWeight: 700,
    letterSpacing: 0.2,
  };

  const subStyle: CSSProperties = {
    marginTop: 2,
    fontSize: 10,
    color: "rgba(226,232,240,0.70)",
  };

  const badge: CSSProperties = {
    padding: "4px 10px",
    borderRadius: 999,
    border: "1px solid rgba(56,189,248,0.40)",
    background: "rgba(56,189,248,0.10)",
    fontSize: 10,
    color: "rgba(226,232,240,0.90)",
    whiteSpace: "nowrap",
  };

  return (
    <div style={shell}>
      <canvas
        ref={canvasRef}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          pointerEvents: "none",
          opacity: 0.95,
        }}
      />

      <div style={grid} />
      <div style={vignette} />

      <div style={header}>
        <div>
          <div style={titleStyle}>{title}</div>
          {subtitle ? <div style={subStyle}>{subtitle}</div> : null}
        </div>
        {rightBadge ? <div style={badge}>{rightBadge}</div> : null}
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 10,
          left: 12,
          fontSize: 10,
          color: "rgba(226,232,240,0.55)",
          zIndex: 5,
        }}
      >
        Tessaris OS viewport (QFC-only)
      </div>
    </div>
  );
}