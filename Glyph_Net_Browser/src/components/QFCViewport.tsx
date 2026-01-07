// Glyph_Net_Browser/src/components/QFCViewport.tsx
"use client";

import React, { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";

import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";

import { useTessarisTelemetry } from "@/hooks/useTessarisTelemetry";
import type { TessarisTelemetry } from "@/hooks/useTessarisTelemetry";

// Core demos
import QFCDemoGravity from "./qfc/demos/QFCDemoGravity";
import QFCDemoTunnel from "./qfc/demos/QFCDemoTunnel";
import QFCDemoMatter from "./qfc/demos/QFCDemoMatter";
import QFCDemoConnect from "./qfc/demos/QFCDemoConnect";
import QFCDemoWormhole from "./qfc/demos/QFCDemoWormhole";
import QFCDemoGenome from "./qfc/demos/QFCDemoGenome";
import QFCDemoTopology from "./qfc/demos/QFCDemoTopology";

// Extra demos (your list)
import QFCAxiomStability from "./qfc/demos/QFCAxiomStability";
import QFCBornRuleConvergence from "./qfc/demos/QFCBornRuleConvergence";
import QFCCausalSpacetimeK from "./qfc/demos/QFCCausalSpacetimeK";
import QFCDemoPSeries from "./qfc/demos/QFCDemoP-Series";
import QFCEmergentGeometryM from "./qfc/demos/QFCEmergentGeometryM";
import QFCEmergentTimeH2 from "./qfc/demos/QFCEmergentTimeH2";
import QFCFeedbackControllerN from "./qfc/demos/QFCFeedbackControllerN";
import QFCGeometryEmergence from "./qfc/demos/QFCGeometryEmergence";
import QFCGovernedSelection from "./qfc/demos/QFCGovernedSelection";
import QFCInformationCoherence from "./qfc/demos/QFCInformationCoherence";
import QFCInformationDynamicsI from "./qfc/demos/QFCInformationDynamicsI";
import QFCObserverDashboardO from "./qfc/demos/QFCObserverDashboardO";
import QFCPipelineVerification from "./qfc/demos/QFCPipelineVerification";
import QFCSemanticCurvature from "./qfc/demos/QFCSemanticCurvature";
import QFCTelemetryAuditv3 from "./qfc/demos/QFCTelemetryAuditv3";
import QFCVacuumLandscapeF from "./qfc/demos/QFCVacuumLandscapeF";

// GlyphOS demo
import QFCMultiverseActionDemo from "./qfc/demos/QFC_Demo_GlyphOS";

export type QFCDomain = "phys" | "bio";
export const isQfcDomain = (d: any): d is QFCDomain => d === "phys" || d === "bio";

/**
 * Modes are now authoritative and extensible.
 * Keep these strings stable because URLs + HUDs use them.
 */
export const QFC_MODES = [
  // core
  "gravity",
  "tunnel",
  "matter",
  "connect",
  "wormhole",
  "genome",
  "topology",
  "glyphos",

  // extra demos
  "axiom_stability",
  "born",
  "causal_spacetime_k",
  "p_series",
  "emergent_geometry_m",
  "emergent_time_h2",
  "feedback_controller_n",
  "geometry_emergence",
  "governed_selection",
  "information_coherence",
  "information_dynamics_i",
  "observer_dashboard_o",
  "pipeline_verification",
  "semantic_curvature",
  "telemetry_audit_v3",
  "vacuum_landscape_f",

  // optional legacy aliases
  "antigrav",
  "sync",
] as const;

export type QFCMode = (typeof QFC_MODES)[number];
export const isQfcMode = (m: any): m is QFCMode =>
  typeof m === "string" && (QFC_MODES as readonly string[]).includes(m);

export type QFCTheme = {
  gravity?: string;
  matter?: string;
  photon?: string;
  connect?: string;
  danger?: string;
  genome?: string;
  antigrav?: string;
  sync?: string;
  topology?: string;
  glyphos?: string;
};

export type QFCFlags = {
  nec_violation?: boolean;
  nec_strength?: number;
  jump_flash?: number;
  chirality?: 1 | -1;
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

  topo_gate01?: number;
};

export type QFCViewportProps = {
  title?: string;
  subtitle?: string;
  rightBadge?: string;

  domain?: QFCDomain;
  domainLabel?: string;

  mode?: QFCMode;
  theme?: QFCTheme;

  frame?: QFCFrame | null;
  frames?: QFCFrame[];

  telemetry?: TessarisTelemetry;

  showDataPanel?: boolean;
};

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const num = (v: any, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);

function inferDomainFromHash(): QFCDomain {
  try {
    if (typeof window === "undefined") return "phys";
    const h = window.location.hash || "";
    if (h.startsWith("#/qfc-bio")) return "bio";
    if (h.startsWith("#/qfc-hud")) return "phys";
    return "phys";
  } catch {
    return "phys";
  }
}

function buildQfcFrameFromTelemetry(t: TessarisTelemetry): QFCFrame | null {
  if (!t) return null;

  const analytics: any = (t as any).analytics ?? {};
  const fusion: any = (t as any).fusion ?? {};

  const rqfsAny: any = (t as any).rqfs ?? {};
  const rqfsState: any = rqfsAny?.state ?? rqfsAny ?? {};

  const qfcAny: any = (t as any).qfc ?? fusion?.qfc ?? analytics?.qfc ?? {};

  const flags: QFCFlags =
    (qfcAny.flags as QFCFlags) ?? (fusion?.flags as QFCFlags) ?? {};

  const rawCh: any =
    qfcAny?.flags?.chirality ??
    fusion?.flags?.chirality ??
    analytics?.chirality;

  const chirality: 1 | -1 = rawCh === -1 || rawCh === "-1" ? -1 : 1;
  const flags2: QFCFlags = { ...(flags ?? {}), chirality };

  const theme: QFCTheme =
    (qfcAny.theme as QFCTheme) ?? (fusion?.theme as QFCTheme) ?? {};

  const rawMode: any = qfcAny.mode ?? fusion?.mode ?? undefined;
  const mode: QFCMode | undefined = isQfcMode(rawMode) ? rawMode : undefined;

  // NOTE: keep these telemetry mappings as-is; HUD overrides can pass frame/mode props.
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
    flags: flags2,
    topology,
    topo_gate01,
  };
}

function fmt(v: any, digits = 4) {
  const x = Number(v);
  if (!Number.isFinite(x)) return "—";
  return x.toFixed(digits);
}

/**
 * Central registry: mode -> renderer
 * This avoids a giant if/else chain and makes adding scenes trivial.
 */
const DEMO_REGISTRY: Record<QFCMode, React.ComponentType<{ frame: QFCFrame | null }>> = {
  // core
  gravity: QFCDemoGravity,
  tunnel: QFCDemoTunnel,
  matter: QFCDemoMatter,
  connect: QFCDemoConnect,
  wormhole: QFCDemoWormhole,
  genome: QFCDemoGenome,
  topology: QFCDemoTopology,
  glyphos: QFCMultiverseActionDemo,

  // extra demos
  axiom_stability: QFCAxiomStability,
  born: QFCBornRuleConvergence,
  causal_spacetime_k: QFCCausalSpacetimeK,
  p_series: QFCDemoPSeries,
  emergent_geometry_m: QFCEmergentGeometryM,
  emergent_time_h2: QFCEmergentTimeH2,
  feedback_controller_n: QFCFeedbackControllerN,
  geometry_emergence: QFCGeometryEmergence,
  governed_selection: QFCGovernedSelection,
  information_coherence: QFCInformationCoherence,
  information_dynamics_i: QFCInformationDynamicsI,
  observer_dashboard_o: QFCObserverDashboardO,
  pipeline_verification: QFCPipelineVerification,
  semantic_curvature: QFCSemanticCurvature,
  telemetry_audit_v3: QFCTelemetryAuditv3,
  vacuum_landscape_f: QFCVacuumLandscapeF,

  // legacy aliases (map to a sane default)
  antigrav: QFCDemoGravity,
  sync: QFCDemoConnect,
};

export default function QFCViewport(props: QFCViewportProps) {
  const {
    title = "Quantum Field Canvas",
    subtitle,
    rightBadge,

    domain: domainProp,
    domainLabel: domainLabelProp,

    mode: modeProp,
    theme: themeProp,

    frame,
    frames,
    telemetry: telemetryProp,

    showDataPanel = true,
  } = props;

  const domain: QFCDomain = useMemo(() => {
    if (isQfcDomain(domainProp)) return domainProp;
    return inferDomainFromHash();
  }, [domainProp]);

  const domainLabel = domainLabelProp ?? (domain === "bio" ? "BIO" : "PHYS");

  const liveTelemetry = useTessarisTelemetry();
  const telemetry = telemetryProp ?? liveTelemetry;

  const [liveFrame, setLiveFrame] = useState<QFCFrame | null>(null);

  useEffect(() => {
    const hasExternalFrames =
      frame !== undefined || (Array.isArray(frames) && frames.length > 0);
    if (hasExternalFrames) return;
    if (!telemetry) return;

    const fr = buildQfcFrameFromTelemetry(telemetry);
    if (fr) setLiveFrame(fr);
  }, [telemetry, frame, frames]);

  const effectiveFrame: QFCFrame | null = frame === undefined ? liveFrame : frame;

  // Parent mode prop wins, then frame.mode, else default
  const effectiveMode: QFCMode =
    (isQfcMode(modeProp) ? modeProp : undefined) ??
    (isQfcMode(effectiveFrame?.mode) ? (effectiveFrame!.mode as QFCMode) : undefined) ??
    "gravity";

  const effectiveTheme: QFCTheme | undefined = themeProp ?? effectiveFrame?.theme;

  const topoGate01 = useMemo(() => {
    const g =
      (effectiveFrame as any)?.topo_gate01 ??
      (effectiveFrame as any)?.topology?.gate ??
      1;
    return clamp01(Number(g));
  }, [effectiveFrame]);

  const demoFrame: QFCFrame | null = useMemo(() => {
    if (!effectiveFrame) return null;
    return {
      ...effectiveFrame,
      mode: effectiveMode,
      theme: effectiveTheme ?? effectiveFrame.theme,
      topo_gate01: topoGate01,
    };
  }, [effectiveFrame, effectiveMode, effectiveTheme, topoGate01]);

  const ch: 1 | -1 = (demoFrame?.flags?.chirality ?? 1) === -1 ? -1 : 1;
  const chLabel = `CH:${ch > 0 ? "+1" : "-1"}`;

  // Hard remount on mode change so the scene swaps cleanly
  const canvasKey = useMemo(() => `qfc:${domain}:${effectiveMode}`, [domain, effectiveMode]);

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
    display: "flex",
    flexDirection: "column",
  };

  const canvasWrap: CSSProperties = {
    position: "relative",
    flex: "1 1 auto",
    minHeight: 240,
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

  const badgeText =
    rightBadge && rightBadge.trim().length
      ? `${rightBadge} · ${domainLabel} · ${chLabel} · gate:${topoGate01.toFixed(2)}`
      : `${domainLabel} · ${chLabel} · gate:${topoGate01.toFixed(2)}`;

  const panel: CSSProperties = {
    flex: "0 0 auto",
    borderTop: "1px solid rgba(148,163,184,0.20)",
    background: "rgba(2,6,23,0.55)",
    padding: "10px 12px",
    display: showDataPanel ? "block" : "none",
  };

  const panelRow: CSSProperties = {
    display: "flex",
    flexWrap: "wrap",
    gap: 10,
    alignItems: "center",
    fontSize: 11,
    color: "rgba(226,232,240,0.86)",
  };

  const chip: CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    padding: "4px 8px",
    borderRadius: 999,
    border: "1px solid rgba(148,163,184,0.22)",
    background: "rgba(15,23,42,0.55)",
    color: "rgba(226,232,240,0.90)",
    fontFamily:
      "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
  };

  const kappa = demoFrame?.kappa ?? undefined;
  const chi = demoFrame?.chi ?? undefined;
  const sigma = demoFrame?.sigma ?? undefined;
  const alpha = demoFrame?.alpha ?? undefined;

  const topoEpoch = demoFrame?.topology?.epoch;
  const topoNodes = demoFrame?.topology?.nodes?.length ?? 0;
  const topoEdges = demoFrame?.topology?.edges?.length ?? 0;

  const updatedAt = telemetry?.updatedAt;
  const staleMs = updatedAt ? Math.max(0, Date.now() - updatedAt) : null;
  const staleLabel =
    staleMs == null ? "telemetry:—" : staleMs < 1500 ? "telemetry:live" : `telemetry:${Math.round(staleMs)}ms`;

  // Pick scene component from registry (always defined)
  const Scene = DEMO_REGISTRY[effectiveMode] ?? QFCDemoGravity;

  return (
    <div style={shell}>
      <div style={canvasWrap}>
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

          {/* ✅ Scene switch (registry-driven) */}
          <group key={`${domain}:${effectiveMode}`}>
            <Scene frame={demoFrame} />
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
          <div style={badge}>{badgeText}</div>
        </div>
      </div>

      <div style={panel}>
        <div style={panelRow}>
          <span style={chip}>{`domain:${domainLabel}`}</span>
          <span style={chip}>{`mode:${effectiveMode}`}</span>
          <span style={chip}>{staleLabel}</span>

          <span style={chip}>{`kappa:${fmt(kappa, 5)}`}</span>
          <span style={chip}>{`chi:${fmt(chi, 5)}`}</span>
          <span style={chip}>{`sigma:${fmt(sigma, 5)}`}</span>
          <span style={chip}>{`alpha:${fmt(alpha, 4)}`}</span>

          <span style={chip}>{`gate:${fmt(topoGate01, 3)}`}</span>
          <span style={chip}>{`epoch:${topoEpoch ?? "—"}`}</span>
          <span style={chip}>{`topo:n=${topoNodes} e=${topoEdges}`}</span>
          <span style={chip}>{chLabel}</span>
        </div>
      </div>
    </div>
  );
}