"use client";

import { useEffect, useState } from "react";
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
  nec_strength?: number;
  jump_flash?: number;
};

type QFCFrame = {
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
};

type QFCViewportProps = {
  title?: string;
  subtitle?: string;
  rightBadge?: string;

  mode?: QFCMode;
  theme?: QFCTheme;

  frame?: QFCFrame | null;
  frames?: QFCFrame[];

  telemetry?: TessarisTelemetry;
};

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const num = (v: any, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);

function buildQfcFrameFromTelemetry(t: TessarisTelemetry): QFCFrame | null {
  if (!t) return null;

  const analytics: any = t.analytics ?? {};
  const fusion: any = t.fusion ?? {};

  const rqfsAny: any = (t as any).rqfs ?? {};
  const rqfsState: any = rqfsAny?.state ?? rqfsAny ?? {};

  const qfcAny: any = (t as any).qfc ?? fusion?.qfc ?? analytics?.qfc ?? {};

  const flags: QFCFlags = (qfcAny.flags as QFCFlags) ?? (fusion?.flags as QFCFlags) ?? {};
  const theme: QFCTheme = (qfcAny.theme as QFCTheme) ?? (fusion?.theme as QFCTheme) ?? {};
  const mode: QFCMode | undefined = (qfcAny.mode as QFCMode) ?? (fusion?.mode as QFCMode) ?? undefined;

  const kappa = num(rqfsState.nu_bias ?? rqfsState.kappa ?? analytics.mean_nu, 0);
  const chi = num(rqfsState.phi_bias ?? rqfsState.chi ?? analytics.mean_phi, 0);
  const sigma = num(rqfsState.amp_bias ?? rqfsState.sigma ?? analytics.mean_amp, 0);

  const psiRaw = num(
    fusion["ψ̃"] ?? fusion.psi_tilde ?? fusion.cognition_signal ?? fusion.inference_strength ?? fusion.signal,
    NaN,
  );
  const psi01 = Number.isFinite(psiRaw) ? clamp01(0.5 + 0.5 * psiRaw) : NaN;

  const alpha = num(
    Number.isFinite(psi01) ? psi01 : (fusion.fusion_score ?? fusion.fusion ?? fusion.alpha ?? analytics.stability),
    0,
  );

  const curl_rms = num(
    fusion["κ̃"] ?? fusion.kappa_tilde ?? fusion.curl_rms ?? fusion.curl ?? analytics.curl_rms,
    0,
  );

  const curv = num(fusion.curv ?? fusion.curvature ?? analytics.curv ?? analytics.curvature, 0);

  const coupling_score = num(
    fusion.coupling_score ?? fusion.coupling ?? analytics.coupling_score ?? analytics.stability,
    0,
  );

  const max_norm = num(fusion.max_norm ?? analytics.max_norm, 0);

  const ts =
    (typeof analytics.timestamp === "string" && Date.parse(analytics.timestamp)) ||
    (typeof fusion.timestamp === "string" && Date.parse(fusion.timestamp)) ||
    Date.now();

  return { t: ts, kappa, chi, sigma, alpha, curl_rms, curv, coupling_score, max_norm, mode, theme, flags };
}

export default function QFCViewport(props: QFCViewportProps) {
  const {
    title = "Quantum Field Canvas",
    subtitle,
    rightBadge,
    mode = "gravity",
    theme,
    frame,
    frames,
    telemetry: telemetryProp,
  } = props;

  const liveTelemetry = useTessarisTelemetry();
  const telemetry = telemetryProp ?? liveTelemetry;

  const [liveFrame, setLiveFrame] = useState<QFCFrame | null>(null);

  useEffect(() => {
    const hasExternalFrames = frame !== undefined || (Array.isArray(frames) && frames.length > 0);
    if (hasExternalFrames) return;
    if (!telemetry) return;

    const fr = buildQfcFrameFromTelemetry(telemetry);
    if (fr) setLiveFrame(fr);
  }, [telemetry, frame, frames]);

  const effectiveFrame = frame ?? liveFrame ?? null;
  const effectiveMode: QFCMode = (effectiveFrame?.mode as QFCMode) ?? mode;

  const shell: CSSProperties = {
    height: "100%",
    width: "100%",
    minHeight: 320,
    borderRadius: 14,
    overflow: "hidden",
    border: "1px solid rgba(148,163,184,0.35)",
    background:
      "radial-gradient(1200px 600px at 20% 10%, rgba(56,189,248,0.18), transparent 55%)," +
      "radial-gradient(1000px 500px at 80% 20%, rgba(34,197,94,0.10), transparent 55%)," +
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

  return (
    <div style={shell}>
      <Canvas
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
          args={[90, 90, new THREE.Color("#1d4ed8"), new THREE.Color("#0ea5e9")]}
          position={[0, -2.0, 0]}
        />

        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -2.02, 0]}>
          <planeGeometry args={[120, 120]} />
          <meshBasicMaterial color={"#030712"} transparent opacity={0.35} />
        </mesh>

        {effectiveMode === "gravity" ? <QFCDemoGravity frame={effectiveFrame} /> : null}
        {effectiveMode === "tunnel" ? <QFCDemoTunnel frame={effectiveFrame} /> : null}
        {effectiveMode === "matter" ? <QFCDemoMatter frame={effectiveFrame} /> : null}
        {effectiveMode === "connect" ? <QFCDemoConnect frame={effectiveFrame} /> : null}

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
        {rightBadge ? <div style={badge}>{rightBadge}</div> : null}
      </div>
    </div>
  );
}