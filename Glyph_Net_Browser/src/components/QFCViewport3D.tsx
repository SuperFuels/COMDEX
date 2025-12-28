// Glyph_Net_Browser/src/components/QFCViewport.tsx
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";

import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";

// ✅ LIVE TELEMETRY HOOK (auto-bind)
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

  // metrics
  kappa?: number;
  chi?: number;
  sigma?: number;
  alpha?: number;
  curl_rms?: number;
  curv?: number;
  coupling_score?: number;
  max_norm?: number;

  // injected by backend renderer (optional)
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

  // kept for API compatibility
  bloom?: boolean;
  bloomStrength?: number;
  bloomBlur?: number;
};

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const num = (v: any, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);

// alpha helper (rgba/rgb -> rgba with new alpha; hex/named unchanged)
const withAlpha = (c: string, a: number) => {
  const aa = String(Math.max(0, Math.min(1, a)));
  if (!c) return `rgba(255,255,255,${aa})`;
  if (c.startsWith("rgba("))
    return c.replace(/rgba\(([^)]+),\s*[\d.]+\s*\)/, `rgba($1, ${aa})`);
  if (c.startsWith("rgb(")) return c.replace(/rgb\(([^)]+)\)/, `rgba($1, ${aa})`);
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

  const qfcAny: any = (t as any).qfc ?? fusion?.qfc ?? analytics?.qfc ?? {};

  const flags: QFCFlags =
    (qfcAny.flags as QFCFlags) ?? (fusion?.flags as QFCFlags) ?? {};
  const theme: QFCTheme =
    (qfcAny.theme as QFCTheme) ?? (fusion?.theme as QFCTheme) ?? {};
  const mode: QFCMode | undefined =
    (qfcAny.mode as QFCMode) ?? (fusion?.mode as QFCMode) ?? undefined;

  // Primary metrics
  const kappa = num(rqfsState.nu_bias ?? rqfsState.kappa ?? analytics.mean_nu, 0);
  const chi = num(rqfsState.phi_bias ?? rqfsState.chi ?? analytics.mean_phi, 0);
  const sigma = num(rqfsState.amp_bias ?? rqfsState.sigma ?? analytics.mean_amp, 0);

  // ---- ψ̃ (cognitive wave)
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
      : (fusion.fusion_score ?? fusion.fusion ?? fusion.alpha ?? analytics.stability),
    0,
  );

  // ---- κ̃ (resonance field)
  const curl_rms = num(
    fusion["κ̃"] ??
      fusion.kappa_tilde ??
      fusion.curl_rms ??
      fusion.curl ??
      analytics.curl_rms,
    0,
  );

  const curv = num(fusion.curv ?? fusion.curvature ?? analytics.curv ?? analytics.curvature, 0);

  const coupling_score = num(
    fusion.coupling_score ??
      fusion.coupling ??
      analytics.coupling_score ??
      analytics.stability,
    0,
  );

  const max_norm = num(fusion.max_norm ?? analytics.max_norm, 0);

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

function modeColor(mode: QFCMode, theme: QFCTheme): string {
  if (mode === "tunnel") return theme.photon ?? "#fbbf24";
  if (mode === "connect") return theme.connect ?? "#22d3ee";
  if (mode === "matter") return theme.matter ?? "#e2e8f0";
  if (mode === "antigrav") return theme.antigrav ?? "#22c55e";
  if (mode === "sync") return theme.sync ?? "#ffffff";
  return theme.gravity ?? "#38bdf8";
}

function QFCParticles({ frame, mode, theme }: { frame: QFCFrame | null; mode: QFCMode; theme: QFCTheme }) {
  const pts = useRef<THREE.Points>(null);

  const geom = useMemo(() => {
    const COUNT = 2200;
    const g = new THREE.BufferGeometry();
    const pos = new Float32Array(COUNT * 3);
    const jitter = new Float32Array(COUNT * 1);

    for (let i = 0; i < COUNT; i++) {
      pos[i * 3 + 0] = (Math.random() - 0.5) * 44;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 14 + 2;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 44;
      jitter[i] = Math.random();
    }

    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("jitter", new THREE.BufferAttribute(jitter, 1));
    return g;
  }, []);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();

    const k = clamp01(num(frame?.kappa, 0.2));
    const a = clamp01(num(frame?.alpha, 0.2));
    const s = clamp01(num(frame?.sigma, 0.4));

    if (pts.current) {
      pts.current.rotation.y = t * (0.04 + 0.10 * a);
      pts.current.rotation.x = 0.02 * Math.sin(t * (0.55 + k));
      pts.current.position.y = 0.15 * Math.sin(t * (0.7 + s));
    }
  });

  const col = modeColor(mode, theme);

  return (
    <points ref={pts} geometry={geom}>
      <pointsMaterial
        size={0.065}
        color={col}
        transparent
        opacity={0.55}
        depthWrite={false}
      />
    </points>
  );
}

/** Small “field line” that reacts to current metrics (gives motion + structure). */
function QFCFieldLine({
  frame,
  mode,
  theme,
}: {
  frame: QFCFrame | null;
  mode: QFCMode;
  theme: QFCTheme;
}) {
  const geomRef = useRef<THREE.BufferGeometry | null>(null);

  const { positions, count } = useMemo(() => {
    const COUNT = 260;
    const arr = new Float32Array(COUNT * 3);
    return { positions: arr, count: COUNT };
  }, []);

  const color = useMemo(() => modeColor(mode, theme), [mode, theme]);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();

    const sigma = clamp01(num(frame?.sigma, 0.55));
    const alpha = clamp01(num(frame?.alpha, 0.12));
    const curl = clamp01(num(frame?.curl_rms, 0.03) * 10);
    const coupling = clamp01(num(frame?.coupling_score, 0.55));

    const amp = 0.35 + 0.85 * sigma;
    const freq = 0.55 + 1.25 * sigma;
    const wobble = 0.25 + 0.75 * coupling;
    const lift = 0.25 + 0.25 * alpha;
    const zRoll = 0.25 + 0.65 * curl;

    for (let i = 0; i < count; i++) {
      const u = i / (count - 1);
      const x = -12 + 24 * u;

      const y =
        lift +
        Math.sin((x * 0.45) * freq + t * (1.3 + wobble)) * (0.55 * amp) +
        Math.sin((x * 0.18) * freq - t * 0.9) * (0.25 * amp);

      const z =
        Math.cos((x * 0.22) * freq + t * (0.8 + zRoll)) * (0.35 + 0.35 * alpha);

      positions[i * 3 + 0] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;
    }

    const g = geomRef.current;
    if (g) {
      const attr = g.getAttribute("position") as THREE.BufferAttribute;
      attr.needsUpdate = true;
      g.computeBoundingSphere();
    }
  });

  return (
    <line>
      <bufferGeometry ref={geomRef}>
        <bufferAttribute attach="attributes-position" array={positions} count={count} itemSize={3} />
      </bufferGeometry>
      <lineBasicMaterial
        color={new THREE.Color(withAlpha(color, 0.95))}
        transparent
        opacity={0.95}
      />
    </line>
  );
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
    if (!fr) return;

    setLiveFrame(fr);
  }, [telemetry, frame, frames]);

  const effectiveFrame = frame ?? liveFrame ?? null;
  const effectiveMode: QFCMode = (effectiveFrame?.mode as QFCMode) ?? mode;
  const effectiveTheme: QFCTheme = (effectiveFrame?.theme as QFCTheme) ?? (theme ?? {});

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

        {/* ✅ PARTICLES (this is what makes it stop looking “empty”) */}
        <QFCParticles frame={effectiveFrame} mode={effectiveMode} theme={effectiveTheme} />

        {/* ✅ FIELD LINE */}
        <group position={[0, 0, 0]}>
          <QFCFieldLine frame={effectiveFrame} mode={effectiveMode} theme={effectiveTheme} />
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
          pointerEvents: "none",
        }}
      >
        Tessaris OS viewport (QFC-only)
      </div>
    </div>
  );
}