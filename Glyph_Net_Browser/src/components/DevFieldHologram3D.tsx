// Glyph_Net_Browser/src/components/DevFieldHologram3D.tsx
"use client";

import React, { useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Line as DreiLine } from "@react-three/drei";
import * as THREE from "three";
import type { HoloIR } from "@/lib/types/holo";
import { runHoloSnapshot } from "@/lib/api/holo";

// Drei's <Line> types are noisy in this setup, so wrap as any
const Line = (props: any) => <DreiLine {...props} />;

type GhxNode = { id: string; data: any };
type GhxEdge = {
  id: string;
  source?: string;
  target?: string;
  src?: string;
  dst?: string;
  kind?: string;
};

export type GhxPacket = {
  ghx_version: string;
  origin: string;
  container_id: string;
  nodes: any[];
  edges: any[];
  metadata?: Record<string, any>;
};

export type HologramMode = "field" | "crystal";

export interface DevFieldHologram3DProps {
  packet: GhxPacket | null;
  /** 'world' = card pinned to its grid tile, 'focus' = card pulled to centre */
  focusMode?: "world" | "focus";
  /** Optional callback when the card is clicked */
  onToggleFocus?: () => void;
  /** Visual style / layout for the nodes */
  mode?: HologramMode;
}

/** simple deterministic hash → grid cell for container_id */
function containerSlot(id: string): { gx: number; gz: number } {
  let h = 0;
  for (let i = 0; i < id.length; i++) {
    h = (h * 31 + id.charCodeAt(i)) | 0;
  }
  const gx = ((h >> 1) % 7) - 3; // -3..3
  const gz = ((h >> 4) % 7) - 3;
  return { gx, gz };
}

/** pull ψ–κ–T-ish signature + some normalised scalars out of metadata */
function getPsiSignature(packet: GhxPacket | null) {
  const meta = ((packet && packet.metadata) || {}) as any;
  const sig = meta.psi_kappa_tau_signature || {};
  const nodeCount = meta.node_count ?? (packet?.nodes?.length ?? 0);

  const psi = typeof sig.psi === "number" ? sig.psi : 0;
  const kappa = typeof sig.kappa === "number" ? sig.kappa : 0;
  const tau = typeof sig.tau === "number" ? sig.tau : 0;

  const rank = typeof sig.rank === "number" ? sig.rank : 1;

  let energy: number;
  if (typeof sig.energy === "number") {
    energy = sig.energy;
  } else {
    const sum = psi + kappa + tau;
    energy = sum !== 0 ? sum : nodeCount;
  }

  const entropy =
    typeof sig.entropy === "number" ? sig.entropy : Math.log2(nodeCount + 1);

  const complexity = Math.min(1, nodeCount / 64);
  const energyNorm = Math.min(1, energy / 100.0);
  const entropyNorm = Math.min(1, entropy / 8.0);

  return {
    rank,
    energy,
    entropy,
    complexity,
    energyNorm,
    entropyNorm,
    nodeCount,
  };
}

/** holographic floor grid (slightly brighter blue lines) */
function HoloFloor() {
  const gridSize = 120;
  const divisions = 60;
  return (
    <gridHelper
      args={[
        gridSize,
        divisions,
        new THREE.Color("#1e293b"),
        new THREE.Color("#1d4ed8"),
      ]}
      position={[0, 0, 0]}
    />
  );
}

/** central standing hologram frame + etched nodes for one GHX packet */
function HologramCard({
  packet,
  focusMode,
  onToggleFocus,
  mode = "field",
}: {
  packet: GhxPacket;
  focusMode: "world" | "focus";
  onToggleFocus?: () => void;
  mode?: HologramMode;
}) {
  const nodes = packet.nodes ?? [];
  const edges = packet.edges ?? [];

  const { gx, gz } = containerSlot(packet.container_id || "default");
  const tileSpacing = 10;

  const psi = getPsiSignature(packet);
  const baseRadius = 1.4 + psi.complexity * 0.8;
  const nodeScale = 0.1 + psi.energyNorm * 0.1;
  const cardGlow = 0.12 + psi.entropyNorm * 0.18;

  const worldPos = new THREE.Vector3(gx * tileSpacing, 2.8, gz * tileSpacing);
  const focusPos = new THREE.Vector3(0, 3, 0);
  const pos = focusMode === "focus" ? focusPos : worldPos;

  const layoutNodes = useMemo(() => nodes.slice(0, 64), [nodes]);

  const nodePositions = useMemo(() => {
    const map = new Map<string, THREE.Vector3>();
    const n = layoutNodes.length;
    if (!n) return map;

    if (mode === "crystal") {
      // simple crystal-ish lattice: nodes in a 3x3x? grid slab
      const cols = 3;
      const rows = Math.ceil(n / cols);
      const spacingX = 0.9;
      const spacingY = 0.7;

      layoutNodes.forEach((node, i) => {
        const cx = i % cols;
        const cy = Math.floor(i / cols);
        const x = (cx - (cols - 1) / 2) * spacingX * 2.0;
        const y = (cy - (rows - 1) / 2) * spacingY * 2.0;
        map.set(node.id, new THREE.Vector3(x, y, 0.04));
      });

      return map;
    }

    // default "field" mode – fan / arc
    const radius = baseRadius;
    const arc = Math.PI * 1.0;
    const start = -arc / 2;

    layoutNodes.forEach((node, i) => {
      const t = n === 1 ? 0 : i / (n - 1);
      const angle = start + arc * t;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius * 0.7;
      map.set(node.id, new THREE.Vector3(x, y, 0.04));
    });

    return map;
  }, [layoutNodes, baseRadius, mode]);

  return (
    <group
      position={pos.toArray()}
      onClick={(e) => {
        e.stopPropagation();
        onToggleFocus && onToggleFocus();
      }}
    >
      {/* frame plane */}
      <mesh position={[0, 0, 0]}>
        <planeGeometry args={[7, 3.6]} />
        <meshBasicMaterial color="#0ea5e9" transparent opacity={cardGlow} />
      </mesh>

      {/* outer border */}
      <mesh position={[0, 0, 0.01]}>
        <planeGeometry args={[7.1, 3.7]} />
        <meshBasicMaterial
          color="#e5f0ff"
          wireframe
          transparent
          opacity={0.95}
        />
      </mesh>

      {/* subtle inner etched grid */}
      <group position={[0, 0, 0.02]}>
        {[...Array(5)].map((_, i) => {
          const x = -3.5 + (7 / 6) * (i + 1);
          const p1 = new THREE.Vector3(x, -1.8, 0);
          const p2 = new THREE.Vector3(x, 1.8, 0);
          return (
            <Line
              key={`v-${i}`}
              points={[p1, p2]}
              color="#64748b"
              transparent
              opacity={0.25}
              lineWidth={1}
            />
          );
        })}
        {[...Array(3)].map((_, i) => {
          const y = -1.8 + (3.6 / 4) * (i + 1);
          const p1 = new THREE.Vector3(-3.5, y, 0);
          const p2 = new THREE.Vector3(3.5, y, 0);
          return (
            <Line
              key={`h-${i}`}
              points={[p1, p2]}
              color="#64748b"
              transparent
              opacity={0.25}
              lineWidth={1}
            />
          );
        })}
      </group>

      {/* edges as faint cyan lines */}
      {edges.map((edge, idx) => {
        const e = edge as any;

        // Tolerate all known GHX edge endpoint shapes:
        const srcId =
          e.source ??
          e.src ??
          e.from ??
          e.src_id ??
          null;
        const dstId =
          e.target ??
          e.dst ??
          e.to ??
          e.dst_id ??
          null;

        if (!srcId || !dstId) return null;

        const a = nodePositions.get(srcId);
        const b = nodePositions.get(dstId);
        if (!a || !b) return null;

        return (
          <Line
            key={e.id ?? `edge-${idx}`}
            points={[a, b]}
            color="#38bdf8"
            transparent
            opacity={0.35}
            lineWidth={1}
          />
        );
      })}

      {/* nodes */}
      {layoutNodes.map((node, idx) => {
        const p = nodePositions.get(node.id);
        if (!p) return null;
        const isRoot = idx === 0;
        const r = nodeScale * (isRoot ? 1.6 : 1.0);

        return (
          <group key={node.id} position={p.toArray()}>
            <mesh>
              <sphereGeometry args={[r, 18, 18]} />
              <meshStandardMaterial
                color={isRoot ? "#fefce8" : "#e0f2fe"}
                emissive={isRoot ? "#facc15" : "#38bdf8"}
                emissiveIntensity={isRoot ? 3 : 2}
                transparent
                opacity={isRoot ? 1 : 0.95}
              />
            </mesh>
          </group>
        );
      })}

      {/* container anchor */}
      <mesh position={[0, -2.2, 0]}>
        <cylinderGeometry args={[0.16, 0.16, 0.24, 24]} />
        <meshStandardMaterial
          color="#38bdf8"
          emissive="#38bdf8"
          emissiveIntensity={3}
        />
      </mesh>
    </group>
  );
}

/** HoloIR extra.program_frames helper */
function getProgramFrames(holo: HoloIR | null) {
  const extra = (holo as any)?.extra || {};
  const frames = (extra.program_frames as any[]) || [];

  if (Array.isArray(frames) && frames.length >= 4) return frames;

  // Fallback default configuration
  return [
    { id: "frame_main", role: "main", label: "Main" },
    { id: "frame_loop", role: "loop", label: "Loop" },
    { id: "frame_exec", role: "exec", label: "Exec" },
    { id: "frame_output", role: "output", label: "Output" },
  ];
}

// ψ / κ / τ per-frame overlay metrics (fake for now)
type FrameMetric = {
  psi: number;
  kappa: number;
  tau: number;
  coherence: number;
};

function deriveFrameMetricsForFrames(
  frames: any[],
  metrics: any,
): Record<string, FrameMetric> {
  if (!Array.isArray(frames) || frames.length === 0) return {};

  const numBeams = Number(metrics?.num_beams ?? 1) || 1;
  const base = Math.max(1, numBeams);
  const out: Record<string, FrameMetric> = {};

  frames.forEach((f, idx) => {
    const id = f.id || `frame_${idx}`;
    const n = idx + 1;

    const psi = Math.min(
      0.99,
      0.6 + 0.03 * (n % 5) + 0.01 * Math.log10(base),
    );
    const kappa = Math.min(
      0.99,
      0.5 + 0.02 * ((n + 1) % 5) + 0.008 * Math.log10(base + 1),
    );
    const tau = Math.min(
      0.99,
      0.4 + 0.015 * ((n + 2) % 5) + 0.006 * Math.log10(base + 2),
    );
    const coherence = Math.min(
      0.99,
      psi * 0.6 + kappa * 0.3 + tau * 0.1,
    );

    out[id] = {
      psi: Number(psi.toFixed(3)),
      kappa: Number(kappa.toFixed(3)),
      tau: Number(tau.toFixed(3)),
      coherence: Number(coherence.toFixed(3)),
    };
  });

  return out;
}

export function DevFieldHologram3DScene({
  packet,
  focusMode = "world",
  onToggleFocus,
  mode = "field",
}: DevFieldHologram3DProps) {
  // --- .holo run state -----------------
  const [lastHolo, setLastHolo] = React.useState<HoloIR | null>(null);
  const [isRunningHolo, setIsRunningHolo] = React.useState(false);
  const [lastRunStatus, setLastRunStatus] = React.useState<string | null>(null);
  const [runMetrics, setRunMetrics] = React.useState<any | null>(null);
  const [runBeams, setRunBeams] = React.useState<any[]>([]);
  const [runOutput, setRunOutput] = React.useState<string | null>(null);
  const [scriptText, setScriptText] = React.useState("");
  const [frameMetrics, setFrameMetrics] =
    React.useState<Record<string, FrameMetric>>({});

  // seed from any saved .holo + listen for new ones
  React.useEffect(() => {
    if (typeof window === "undefined") return;

    const pending = (window as any).__DEVTOOLS_LAST_HOLO;
    if (pending) {
      setLastHolo(pending as HoloIR);
    }

    function handleHoloSaved(ev: Event) {
      const detail = (ev as CustomEvent).detail;
      if (!detail?.holo) return;
      const holo = detail.holo as HoloIR;
      setLastHolo(holo);
      (window as any).__DEVTOOLS_LAST_HOLO = holo;
    }

    window.addEventListener("devtools.holo_saved", handleHoloSaved as any);
    return () =>
      window.removeEventListener(
        "devtools.holo_saved",
        handleHoloSaved as any,
      );
  }, []);

  async function handleRunHolo() {
    if (!lastHolo) return;

    try {
      setIsRunningHolo(true);
      setLastRunStatus(null);
      setRunMetrics(null);
      setRunBeams([]);
      setRunOutput(null);

      const resp = await fetch("/api/holo/run_snapshot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          holo: lastHolo,
          input_ctx: {
            source: "devtools.field_lab",
            script: scriptText,
          },
          mode: "qqc",
        }),
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `HTTP ${resp.status}`);
      }

      const result: any = await resp.json();

      // local UI state
      setLastRunStatus(result?.status ?? "ok");
      setRunMetrics(result?.metrics ?? null);
      setRunBeams(result?.beams ?? []);

      const engineOutput = result?.engine_output ?? result?.output;
      if (engineOutput) {
        setRunOutput(JSON.stringify(engineOutput, null, 2));
      } else {
        setRunOutput(null);
      }

      // if backend returns an updated holo snapshot, keep it
      if (result?.updated_holo) {
        const updated = result.updated_holo as HoloIR;
        setLastHolo(updated);
        if (typeof window !== "undefined") {
          (window as any).__DEVTOOLS_LAST_HOLO = updated;
        }
      }

      // 🌐 broadcast to DevTools so the Runs strip + console can update
      if (typeof window !== "undefined") {
        window.dispatchEvent(
          new CustomEvent("devtools.holo_run", {
            detail: { result },
          }),
        );
      }
    } catch (e: any) {
      console.error("DevFieldHologram3D: run .holo failed", e);
      setLastRunStatus("error");
      setRunBeams([]);
      setRunOutput(
        JSON.stringify(
          { error: e instanceof Error ? e.message : String(e) },
          null,
          2,
        ),
      );
    } finally {
      setIsRunningHolo(false);
    }
  }

  // Pull run metadata from updated_holo.extra if present
  const runExtra = (lastHolo as any)?.extra || {};
  const runCount =
    typeof runExtra.run_count === "number" ? runExtra.run_count : null;
  const lastRunAt =
    typeof runExtra.last_run_at === "string" ? runExtra.last_run_at : null;

  // Program frames from holo.extra.program_frames or default
  const frames = getProgramFrames(lastHolo);
  const frameById = new Map(
    frames.map((f: any, i: number) => [f.id, { frame: f, index: i }]),
  );

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: "#020617",
        position: "relative",
      }}
    >
      {/* 3D canvas */}
      <Canvas camera={{ position: [0, 8, 18], fov: 55 }}>
        <color attach="background" args={["#020617"]} />
        <ambientLight intensity={0.55} />
        <directionalLight position={[12, 12, 6]} intensity={1.3} />

        <HoloFloor />

        {/* main GHX card in the centre */}
        {packet && (
          <HologramCard
            packet={packet}
            focusMode={focusMode ?? "world"}
            onToggleFocus={onToggleFocus}
            mode={mode}
          />
        )}

        {/* 4-card “program” rail */}
        {frames.map((frame: any, idx: number) => {
          const spacing = 4.0;
          const startX = -spacing * 1.5; // 4 cards ideal positioning
          const x = startX + idx * spacing;
          const z = -6; // little row in front of/around the main card
          const y = 2.4;

          return (
            <group key={frame.id} position={[x, y, z]}>
              {/* frame plane */}
              <mesh>
                <planeGeometry args={[3.2, 1.8]} />
                <meshBasicMaterial
                  color="#22c55e"
                  transparent
                  opacity={0.12}
                />
              </mesh>
              {/* border */}
              <mesh position={[0, 0, 0.01]}>
                <planeGeometry args={[3.3, 1.9]} />
                <meshBasicMaterial
                  color="#bbf7d0"
                  wireframe
                  transparent
                  opacity={0.7}
                />
              </mesh>
              {/* simple bottom strip (label background) */}
              <mesh position={[0, -1.1, 0.02]}>
                <planeGeometry args={[3.0, 0.4]} />
                <meshBasicMaterial
                  color="#022c22"
                  transparent
                  opacity={0.9}
                />
              </mesh>
            </group>
          );
        })}

        {/* beams connecting frames, based on run_holo_snapshot output */}
        {runBeams.map((beam, idx) => {
          const src = (beam as any).source_frame || (beam as any).source;
          const dst = (beam as any).target_frame || (beam as any).target;

          const srcInfo = src ? frameById.get(src) : null;
          const dstInfo = dst ? frameById.get(dst) : null;

          let a: THREE.Vector3;
          let b: THREE.Vector3;

          if (srcInfo && dstInfo) {
            const spacing = 4.0;
            const startX = -spacing * 1.5;
            const z = -6;
            const y = 2.4;

            const sx = startX + srcInfo.index * spacing;
            const dx = startX + dstInfo.index * spacing;

            a = new THREE.Vector3(sx, y, z + 0.1);
            b = new THREE.Vector3(dx, y, z + 0.1);
          } else {
            // fallback to vertical bar if we can’t map frames
            const count = runBeams.length || 1;
            const span = 18;
            const startX = -span / 2;
            const step = span / Math.max(count - 1, 1);
            const x = count === 1 ? 0 : startX + step * idx;
            a = new THREE.Vector3(x, 0.05, 0);
            b = new THREE.Vector3(x, 4.5, 0);
          }

          return (
            <Line
              key={(beam as any).id ?? `run-beam-${idx}`}
              points={[a, b]}
              color="#a3e635"
              transparent
              opacity={0.95}
              lineWidth={2}
            />
          );
        })}

        <OrbitControls
          enablePan
          enableZoom
          enableRotate
          maxPolarAngle={Math.PI * 0.95}
          minDistance={6}
          maxDistance={60}
        />
      </Canvas>

      {/* ▶ Run .holo HUD in the top-right of the grid */}
      <div
        style={{
          position: "absolute",
          top: 8,
          right: 8,
          display: "flex",
          flexDirection: "column",
          gap: 4,
          fontSize: 11,
          zIndex: 10,
        }}
      >
        <button
          type="button"
          onClick={handleRunHolo}
          disabled={!lastHolo || isRunningHolo}
          style={{
            padding: "4px 10px",
            borderRadius: 999,
            border: "1px solid #bbf7d0",
            background: lastHolo ? "#16a34a" : "#e5e7eb",
            color: lastHolo ? "#ecfdf5" : "#6b7280",
            cursor: !lastHolo || isRunningHolo ? "default" : "pointer",
            opacity: isRunningHolo ? 0.7 : 1,
          }}
        >
          {isRunningHolo
            ? "⏳ Running .holo…"
            : lastHolo
            ? "▶ Run .holo"
            : "No .holo bound"}
        </button>

        {lastRunStatus && (
          <div style={{ color: "#e5e7eb", opacity: 0.9 }}>
            Last run: <strong>{lastRunStatus}</strong>
            {runMetrics?.num_beams != null && (
              <> · beams: {runMetrics.num_beams}</>
            )}
          </div>
        )}

        {runCount != null && (
          <div style={{ color: "#9ca3af", opacity: 0.9 }}>
            Runs: {runCount}
            {lastRunAt && (
              <>
                {" "}
                · last at{" "}
                <span style={{ fontFamily: "monospace" }}>
                  {lastRunAt.split(".")[0].replace("T", " ")}
                </span>
              </>
            )}
          </div>
        )}
      </div>

      {/* "Holo Files" stub – placeholder for file cabinet */}
      <div
        style={{
          position: "absolute",
          top: 8,
          left: 8,
          padding: "6px 8px",
          borderRadius: 8,
          background: "rgba(15,23,42,0.96)",
          border: "1px solid rgba(148,163,184,0.6)",
          fontSize: 11,
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas",
          color: "#e5e7eb",
          zIndex: 10,
          maxWidth: 220,
        }}
      >
        <pre
          style={{
            margin: 0,
            whiteSpace: "pre",
          }}
        >
{`Holo Files
├─ main.holo   (t=12 / v=1)
├─ loop.holo   (t=12 / v=1)
├─ exec.holo   (t=12 / v=1)
└─ output.holo (t=12 / v=1)`}
        </pre>
      </div>

      {/* Terminal bar */}
      <div
        style={{
          position: "absolute",
          left: 12,
          bottom: 12,
          right: 12,
          padding: 8,
          borderRadius: 8,
          background: "rgba(15,23,42,0.96)",
          border: "1px solid rgba(148,163,184,0.6)",
          display: "flex",
          flexDirection: "column",
          gap: 4,
          fontSize: 11,
          fontFamily: "monospace",
          color: "#e5e7eb",
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span>&gt;</span>
          <input
            value={scriptText}
            onChange={(e) => setScriptText(e.target.value)}
            placeholder="run frame_main -> frame_exec -> frame_output"
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              color: "#e5e7eb",
              fontFamily: "inherit",
              fontSize: "inherit",
            }}
          />
          <button
            type="button"
            onClick={handleRunHolo}
            disabled={!lastHolo || isRunningHolo}
            style={{
              padding: "3px 10px",
              borderRadius: 999,
              border: "1px solid #4ade80",
              background: "#22c55e",
              color: "#022c22",
              fontSize: 11,
              cursor: !lastHolo || isRunningHolo ? "default" : "pointer",
              opacity: isRunningHolo ? 0.6 : 1,
            }}
          >
            run
          </button>
        </div>

        {runOutput && (
          <pre
            style={{
              margin: 0,
              marginTop: 4,
              maxHeight: 120,
              overflow: "auto",
              whiteSpace: "pre-wrap",
            }}
          >
            {runOutput}
          </pre>
        )}
      </div>
    </div>
  );
}