// Glyph_Net_Browser/src/components/QFCViewport.tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";

import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";

import { useTessarisTelemetry } from "@/hooks/useTessarisTelemetry";
import type { TessarisTelemetry } from "@/hooks/useTessarisTelemetry";

import QFCDemoGravity from "./qfc/demos/QFCDemoGravity";
import QFCDemoTunnel from "./qfc/demos/QFCDemoTunnel";
import QFCDemoMatter from "./qfc/demos/QFCDemoMatter";
import QFCDemoConnect from "./qfc/demos/QFCDemoConnect";
import QFCDemoWormhole from "./qfc/demos/QFCDemoWormhole";
import QFCDemoGenome from "./qfc/demos/QFCDemoGenome";
import QFCDemoTopology from "./qfc/demos/QFCDemoTopology";

export type QFCMode =
  | "gravity"
  | "tunnel"
  | "matter"
  | "connect"
  | "wormhole"
  | "genome"
  | "antigrav"
  | "sync"
  | "topology";

export const isQfcMode = (m: any): m is QFCMode =>
  m === "gravity" ||
  m === "tunnel" ||
  m === "matter" ||
  m === "connect" ||
  m === "wormhole" ||
  m === "genome" ||
  m === "antigrav" ||
  m === "sync" ||
  m === "topology";

export type QFCTheme = {
  gravity?: string;
  matter?: string;
  photon?: string;
  connect?: string;
  danger?: string;
  genome?: string;
  antigrav?: string;
  sync?: string;
  topology?: string; // optional (only if you want a dedicated tint)
};

export type QFCFlags = {
  nec_violation?: boolean;
  nec_strength?: number;
  jump_flash?: number;

  // P13: Chiral Parity Gate (domain tag)
  chirality?: 1 | -1; // +1 = default domain, -1 = mirror domain
};

export type QFCTopology = {
  epoch: number;
  nodes: Array<{ id: string; w?: number }>;
  edges: Array<{ a: string; b: string; w?: number }>;
  gate?: number;
};

export type QFCFrame = {
  t: number;
  kappa?: number;
  chi?: number;
  sigma?: number;
  alpha?: number;
  curl_rms?: number;
  curv?: number;
  coupling_score?: number;
  max_norm?: number;
  mode?: QFCMode;
  theme?: QFCTheme;
  flags?: QFCFlags;
  topology?: QFCTopology;

  // ✅ Task 2: topology drives behavior (0..1 convenience)
  topo_gate01?: number;
};

export type QFCViewportProps = {
  title?: string;
  subtitle?: string;
  rightBadge?: string;

  // preferred mode/theme from parent (HUD)
  mode?: QFCMode;
  theme?: QFCTheme;

  // if provided, these override telemetry-derived frames
  // null is INTENTIONAL (do not fallback to telemetry)
  frame?: QFCFrame | null;
  frames?: QFCFrame[];

  telemetry?: TessarisTelemetry;
};

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const num = (v: any, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);

function buildQfcFrameFromTelemetry(t: TessarisTelemetry): QFCFrame | null {
  if (!t) return null;

  const analytics: any = (t as any).analytics ?? {};
  const fusion: any = (t as any).fusion ?? {};

  const rqfsAny: any = (t as any).rqfs ?? {};
  const rqfsState: any = rqfsAny?.state ?? rqfsAny ?? {};

  const qfcAny: any = (t as any).qfc ?? fusion?.qfc ?? analytics?.qfc ?? {};

  const flags: QFCFlags =
    (qfcAny.flags as QFCFlags) ?? (fusion?.flags as QFCFlags) ?? {};

  // P13: normalize chirality (canonical tag)
  const rawCh: any =
    qfcAny?.flags?.chirality ??
    fusion?.flags?.chirality ??
    analytics?.chirality;

  const chirality: 1 | -1 = rawCh === -1 || rawCh === "-1" ? -1 : 1;

  // ensure flags exists and carry chirality
  const flags2: QFCFlags = { ...(flags ?? {}), chirality };

  const theme: QFCTheme =
    (qfcAny.theme as QFCTheme) ?? (fusion?.theme as QFCTheme) ?? {};

  const rawMode: any = qfcAny.mode ?? fusion?.mode ?? undefined;
  const mode: QFCMode | undefined = isQfcMode(rawMode) ? rawMode : undefined;

  const kappa = num(rqfsState.nu_bias ?? rqfsState.kappa ?? analytics.mean_nu, 0);
  const chi = num(rqfsState.phi_bias ?? rqfsState.chi ?? analytics.mean_phi, 0);
  const sigma = num(
    rqfsState.amp_bias ?? rqfsState.sigma ?? analytics.mean_amp,
    0,
  );

  const psiRaw = num(
    fusion["ψ̃"] ??
      fusion.psi_tilde ??
      fusion.cognition_signal ??
      fusion.inference_strength ??
      fusion.signal,
    NaN,
  );
  const psi01 = Number.isFinite(psiRaw) ? clamp01(0.5 + 0.5 * psiRaw) : NaN;

  const alpha = num(
    Number.isFinite(psi01)
      ? psi01
      : fusion.fusion_score ??
          fusion.fusion ??
          fusion.alpha ??
          analytics.stability,
    0,
  );

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
    fusion.coupling_score ??
      fusion.coupling ??
      analytics.coupling_score ??
      analytics.stability,
    0,
  );

  const max_norm = num(fusion.max_norm ?? analytics.max_norm, 0);

  const ts =
    (typeof analytics.timestamp === "string" &&
      Date.parse(analytics.timestamp)) ||
    (typeof fusion.timestamp === "string" && Date.parse(fusion.timestamp)) ||
    Date.now();

  // ✅ prefer stable contract topology from telemetry (no _src inside it)
  const topoStream: any =
    qfcAny?.topology ??
    fusion?.qfc?.topology ??
    analytics?.qfc?.topology ??
    undefined;

  const topology: QFCTopology | undefined =
    topoStream &&
    Array.isArray(topoStream.nodes) &&
    Array.isArray(topoStream.edges)
      ? {
          epoch: Number(topoStream.epoch ?? Math.floor(Date.now() / 2000)),
          nodes: topoStream.nodes,
          edges: topoStream.edges,
          gate:
            topoStream.gate == null
              ? undefined
              : clamp01(Number(topoStream.gate)),
        }
      : undefined;

  // ✅ Telemetry builder has NO access to effectiveFrame.
  // It derives topo_gate01 from telemetry topology only (or 1).
  const topo_gate01 = clamp01(Number(topology?.gate ?? 1));

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
    flags: flags2, // ✅ P13 carried forward
    topology, // ✅ contract topology if present
    topo_gate01, // ✅ derived convenience field (telemetry-only)
  };
}

export default function QFCViewport(props: QFCViewportProps) {
  const {
    title = "Quantum Field Canvas",
    subtitle,
    rightBadge,

    mode: modeProp,
    theme: themeProp,

    frame,
    frames,
    telemetry: telemetryProp,
  } = props;

  const liveTelemetry = useTessarisTelemetry();
  const telemetry = telemetryProp ?? liveTelemetry;

  const [liveFrame, setLiveFrame] = useState<QFCFrame | null>(null);

  // Only derive liveFrame if parent did NOT provide any frame(s).
  useEffect(() => {
    const hasExternalFrames =
      frame !== undefined || (Array.isArray(frames) && frames.length > 0);
    if (hasExternalFrames) return;
    if (!telemetry) return;

    const fr = buildQfcFrameFromTelemetry(telemetry);
    if (fr) setLiveFrame(fr);
  }, [telemetry, frame, frames]);

  // ✅ if parent passed frame (even null), do NOT fall back to telemetry
  const effectiveFrame: QFCFrame | null = frame === undefined ? liveFrame : frame;

  // ✅ Prefer parent prop mode first, then frame mode (if any), then default
  const effectiveMode: QFCMode =
    (isQfcMode(modeProp) ? modeProp : undefined) ??
    (isQfcMode(effectiveFrame?.mode) ? (effectiveFrame!.mode as QFCMode) : undefined) ??
    "gravity";

  // ✅ Prefer parent theme first, then frame theme (if any)
  const effectiveTheme: QFCTheme | undefined = themeProp ?? effectiveFrame?.theme;

  // ✅ Task 2: derive topoGate01 from whatever frame we’re actually rendering
  // Prefer already-plumbed topo_gate01 on the effectiveFrame (Freeze/DevTools),
  // then fallback to topology.gate, then 1.
  const topoGate01 = useMemo(() => {
    const g =
      (effectiveFrame as any)?.topo_gate01 ??
      (effectiveFrame as any)?.topology?.gate ??
      1;
    return clamp01(Number(g));
  }, [effectiveFrame]);

  // ✅ feed demos a frame that always contains the chosen mode/theme AND topo_gate01
  const demoFrame: QFCFrame | null = useMemo(() => {
    if (!effectiveFrame) return null;
    return {
      ...effectiveFrame,
      mode: effectiveMode,
      theme: effectiveTheme ?? effectiveFrame.theme,
      topo_gate01: topoGate01,
    };
  }, [effectiveFrame, effectiveMode, effectiveTheme, topoGate01]);

  // P13 label (always canonical)
  const ch: 1 | -1 = (demoFrame?.flags?.chirality ?? 1) === -1 ? -1 : 1;
  const chLabel = `CH:${ch > 0 ? "+1" : "-1"}`;

  useEffect(() => {
    console.log(
      "[QFCViewport] modeProp:",
      modeProp,
      "effectiveMode:",
      effectiveMode,
      "chirality:",
      demoFrame?.flags?.chirality,
      "topoGate01:",
      topoGate01,
    );
  }, [modeProp, effectiveMode, demoFrame?.flags?.chirality, topoGate01]);

  // ✅ force full Canvas remount on mode change
  const canvasKey = useMemo(() => `qfc:${effectiveMode}`, [effectiveMode]);

  // Slightly darker purple + green accents (subtle)
  const shell: CSSProperties = {
    height: "100%",
    width: "100%",
    minHeight: 320,
    borderRadius: 14,
    overflow: "hidden",
    border: "1px solid rgba(148,163,184,0.35)",
    background:
      "radial-gradient(1200px 600px at 20% 10%, rgba(99,102,241,0.14), transparent 55%)," +
      "radial-gradient(1000px 500px at 80% 20%, rgba(34,197,94,0.07), transparent 55%)," +
      "linear-gradient(180deg, rgba(2,6,23,0.92), rgba(15,23,42,0.85))",
    position: "relative",
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
    pointerEvents: "none",
  };

  const titleStyle: CSSProperties = { fontSize: 12, fontWeight: 700, letterSpacing: 0.2 };
  const subStyle: CSSProperties = { marginTop: 2, fontSize: 10, color: "rgba(226,232,240,0.70)" };
  const badge: CSSProperties = {
    padding: "4px 10px",
    borderRadius: 999,
    border: "1px solid rgba(56,189,248,0.40)",
    background: "rgba(56,189,248,0.10)",
    fontSize: 10,
    color: "rgba(226,232,240,0.90)",
    whiteSpace: "nowrap",
  };

  const badgeText =
    rightBadge && rightBadge.trim().length
      ? `${rightBadge} · ${chLabel} · gate:${topoGate01.toFixed(2)}`
      : `${chLabel} · gate:${topoGate01.toFixed(2)}`;

  const showBadge = true;

  return (
    <div style={shell}>
      <Canvas
        key={canvasKey}
        style={{ position: "absolute", inset: 0 }}
        camera={{ position: [0, 7, 16], fov: 45, near: 0.1, far: 250 }}
        gl={{ antialias: true, alpha: true }}
      >
        <color attach="background" args={["#050816"]} />
        <fog attach="fog" args={["#050816", 18, 70]} />

        <ambientLight intensity={0.65} />
        <directionalLight position={[8, 14, 10]} intensity={1.0} />
        <directionalLight position={[-8, 6, -10]} intensity={0.35} />

        <gridHelper
          args={[
            90,
            90,
            new THREE.Color("#1d4ed8"),
            new THREE.Color("#0ea5e9"),
          ]}
          position={[0, -2.0, 0]}
        />

        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -2.02, 0]}>
          <planeGeometry args={[120, 120]} />
          <meshBasicMaterial color={"#030712"} transparent opacity={0.35} />
        </mesh>

        <group key={effectiveMode}>
          {effectiveMode === "gravity" ? <QFCDemoGravity frame={demoFrame} /> : null}
          {effectiveMode === "tunnel" ? <QFCDemoTunnel frame={demoFrame} /> : null}
          {effectiveMode === "matter" ? <QFCDemoMatter frame={demoFrame} /> : null}
          {effectiveMode === "connect" ? <QFCDemoConnect frame={demoFrame} /> : null}
          {effectiveMode === "wormhole" ? <QFCDemoWormhole frame={demoFrame} /> : null}
          {effectiveMode === "genome" ? <QFCDemoGenome frame={demoFrame} /> : null}
          {effectiveMode === "topology" ? <QFCDemoTopology frame={demoFrame} /> : null}
        </group>

        <OrbitControls
          makeDefault
          enableDamping
          dampingFactor={0.08}
          rotateSpeed={0.65}
          zoomSpeed={0.9}
          panSpeed={0.7}
          minDistance={6}
          maxDistance={60}
          target={[0, -0.2, 0]}
        />
      </Canvas>

      <div style={header}>
        <div>
          <div style={titleStyle}>{title}</div>
          {subtitle ? <div style={subStyle}>{subtitle}</div> : null}
        </div>

        {showBadge ? <div style={badge}>{badgeText}</div> : null}
      </div>
    </div>
  );
}