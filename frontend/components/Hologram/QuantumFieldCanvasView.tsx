// File: frontend/components/Hologram/QuantumFieldCanvasView.tsx
"use client";

import * as React from "react";
import * as THREE from "three";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";

import { QWaveBeam } from "@/components/QuantumField/beam_renderer";
import { Node } from "@/components/QuantumField/Node";
import { LinkLine } from "@/components/QuantumField/LinkLine";
import { ReplayBranchSelector } from "@/components/QuantumField/ReplayBranchSelector";
import PluginHUD from "../../plugins/PluginHUD";

type FiberInit = { camera: THREE.Camera };

type ViewProps = {
  qwaveBeams: React.ReactNode;

  isReplaying: boolean;
  replayFrames: any[];
  playbackIndex: number;
  setIsReplaying: React.Dispatch<React.SetStateAction<boolean>>;
  setPlaybackIndex: React.Dispatch<React.SetStateAction<number>>;

  collapseTrails?: { id?: string; path: [number, number, number][]; color?: string }[];
  breakthroughTrails?: { points: [number, number, number][]; type?: string }[];
  deadendTrails?: { points: [number, number, number][]; type?: string }[];
  onDroppedScroll?: (glyph: string, scroll: string) => void;
  getLinkColor?: (link: any) => string;

  availableBranches: string[];
  selectedBranch: string;
  setSelectedBranch: (s: string) => void;
  onRetryFromBranch: () => void;

  cameraRef: React.MutableRefObject<THREE.PerspectiveCamera | null>;
  controlsRef: React.MutableRefObject<any>;

  observerPosition: [number, number, number];
  observerDirection: [number, number, number];

  beamData: any[] | null | undefined;
  setSelectedBeam: React.Dispatch<React.SetStateAction<any | null>>;

  mergedNodes: any[];
  mergedLinks: any[];

  onTeleport?: (id: string) => void;

  showPredictedLayer: boolean;
  predictedMode: boolean;
  predictedOverlay: boolean;
  splitScreen: boolean;

  handleOrbitChange: () => void;

  onTogglePredictedLayer: () => void;
  onToggleSplitScreen: () => void;
  onTogglePredictedMode: () => void;
  onTogglePredictedOverlay: () => void;

  tickFilter?: number;
  showCollapsed: boolean;
  others: any;

  beams?: any[];
  liveNodes?: any[];
  liveLinks?: any[];

  predictedOverlayData?: { nodes: any[]; links: any[] } | null;

  // NEW: holo-run wiring
  canRunHolo?: boolean;
  isRunningHolo?: boolean;
  onRunHolo?: () => void;
  lastRunStatus?: string;
};

const QuantumFieldCanvasView: React.FC<ViewProps> = (p) => {
  // ---- TS prop-shim: relax prop checking for link line ----
  const LinkLineAny = LinkLine as unknown as React.FC<any>;

  // ✅ normalize beamData so we never call .map on a non-array
  const safeBeamData: any[] = React.useMemo(() => {
    if (p.beamData && !Array.isArray(p.beamData)) {
      console.warn("QuantumFieldCanvasView: beamData is not an array", p.beamData);
      return [];
    }
    return (p.beamData ?? []) as any[];
  }, [p.beamData]);

  // ───────── helpers ─────────
  function makeRenderReplayFrame(nodes: any[], onTeleport?: (id: string) => void) {
    const find = (id: string) => nodes.find((n: any) => String(n.id) === String(id));
    return (frame: any) => (
      <>
        {(frame?.glyphs ?? []).map((node: any, idx: number) => (
          <Node key={`replay-node-${node?.id ?? idx}`} node={node} onTeleport={onTeleport} />
        ))}
        {(frame?.links ?? []).map((link: any, idx: number) => {
          const s = find(String(link?.source));
          const t = find(String(link?.target));
          if (!s || !t) return null;
          return (
            <LinkLineAny
              key={`replay-link-${idx}`}
              source={s as any}
              target={t as any}
              type={link?.type}
              isDream={Boolean(link?.isDream)}
            />
          );
        })}
      </>
    );
  }

  const getNodeById = React.useCallback(
    (id: string) => p.mergedNodes.find((n: any) => String(n.id) === String(id)),
    [p.mergedNodes]
  );

  const handleDrop: React.DragEventHandler<HTMLDivElement> = (e) => {
    e.preventDefault();
    const glyph =
      e.dataTransfer.getData("application/x-glyph") ||
      e.dataTransfer.getData("text/plain") ||
      "";
    const scroll =
      e.dataTransfer.getData("application/x-scroll") ||
      e.dataTransfer.getData("text/markdown") ||
      e.dataTransfer.getData("text/plain") ||
      "";
    p.onDroppedScroll?.(glyph, scroll);
  };

  const renderReplayFrame = React.useMemo(
    () => makeRenderReplayFrame(p.mergedNodes, p.onTeleport),
    [p.mergedNodes, p.onTeleport]
  );

  /* ───────── 3D scene core ───────── */
  const SceneCore: React.FC = () => (
    <>
      {/* beams (symbolic JSX prebuilt in parent) */}
      {p.qwaveBeams}

      {/* clickable beamData beams */}
      {safeBeamData.map((beam: any, idx: number) => (
        <group key={`bd-${idx}`} onClick={() => p.setSelectedBeam(beam)}>
          <QWaveBeam {...(beam as any)} />
        </group>
      ))}

      {/* links */}
      {(p.mergedLinks ?? []).map((link: any, i: number) => {
        const s = getNodeById((link as any).source);
        const t = getNodeById((link as any).target);
        if (!s || !t) return null;
        return (
          <LinkLineAny
            key={`link-${i}`}
            source={s as any}
            target={t as any}
            type={(link as any).type}
            isDream={Boolean((link as any).isDream)}
          />
        );
      })}

      {/* nodes + simple per-node overlays */}
      {(p.mergedNodes ?? []).map((node: any) => (
        <React.Fragment key={String(node.id)}>
          {(node.source === "dream" || node.isDream) && (
            <mesh position={node.position}>
              <ringGeometry args={[0.6, 0.75, 32]} />
              <meshBasicMaterial color="#d946ef" transparent opacity={0.75} />
            </mesh>
          )}

          <Node node={node} onTeleport={p.onTeleport} />

          {node.locked && (
            <Html position={[node.position[0], node.position[1] + 1.5, node.position[2]]}>
              <div className="text-2xl text-red-500 font-bold drop-shadow">🔒</div>
            </Html>
          )}
        </React.Fragment>
      ))}

      {/* replay overlay for current frame */}
      {p.isReplaying && p.replayFrames[p.playbackIndex]
        ? renderReplayFrame(p.replayFrames[p.playbackIndex])
        : null}
    </>
  );

  return (
    <>
      {/* HUD Controls */}
      <div className="absolute top-4 left-4 z-50 space-y-2">
        <button
          className="text-xs px-3 py-1 h-8 bg-blue-900 hover:bg-blue-800 rounded text-white"
          onClick={p.onTogglePredictedLayer}
        >
          🔮 {p.showPredictedLayer ? "Hide" : "Show"} Predicted Layer
        </button>
        <button
          className="text-xs px-3 py-1 h-8 bg-purple-700 hover:bg-purple-600 rounded text-white"
          onClick={p.onToggleSplitScreen}
        >
          🧠 {p.splitScreen ? "Unsplit View" : "Split Reality / Dream"}
        </button>
        <button
          className="text-xs px-3 py-1 h-8 bg-slate-700 hover:bg-slate-600 rounded text-white"
          onClick={p.onTogglePredictedMode}
        >
          🌓 {p.predictedMode ? "Normal" : "Fade Real Nodes"}
        </button>
        <button
          className="text-xs px-3 py-1 h-8 bg-sky-900 hover:bg-sky-800 rounded text-white"
          onClick={p.onTogglePredictedOverlay}
        >
          🌐 {p.predictedOverlay ? "Hide Overlay" : "Show Overlay"}
        </button>

        {/* NEW: Run .holo control */}
        {p.onRunHolo && (
          <button
            className="text-xs px-3 py-1 h-8 bg-emerald-700 hover:bg-emerald-600 rounded text-white disabled:opacity-50 disabled:cursor-default"
            onClick={p.onRunHolo}
            disabled={!p.canRunHolo || p.isRunningHolo}
          >
            {p.isRunningHolo
              ? "⏳ Running .holo…"
              : p.canRunHolo
              ? "▶ Run .holo"
              : "No .holo bound"}
          </button>
        )}

        {p.lastRunStatus && (
          <div className="text-[10px] text-slate-200 opacity-80">
            Last run: <strong>{p.lastRunStatus}</strong>
          </div>
        )}
      </div>

      {/* Branch selector */}
      <div className="absolute top-4 right-4 z-50 w-64">
        <ReplayBranchSelector
          availableBranches={p.availableBranches}
          selectedBranch={p.selectedBranch}
          onSelect={p.setSelectedBranch}
          onRetry={p.onRetryFromBranch}
        />
      </div>

      {/* Views */}
      <div
        className="h-full w-full relative flex"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        {p.splitScreen ? (
          <div className="w-1/2 h-full border-r border-slate-700">
            <Canvas
              camera={{ position: [0, 0, 10], fov: 50 }}
              onCreated={(state: FiberInit) => {
                p.cameraRef.current = state.camera as THREE.PerspectiveCamera;
              }}
            >
              <ambientLight intensity={0.7} />
              <pointLight position={[10, 10, 10]} />
              <OrbitControls
                ref={p.controlsRef}
                enableZoom
                enablePan
                enableRotate
                target={new THREE.Vector3(...p.observerPosition)}
              />
              <SceneCore />
            </Canvas>
          </div>
        ) : (
          <Canvas
            camera={{ position: [0, 0, 10], fov: 50 }}
            onCreated={(state: FiberInit) => {
              p.cameraRef.current = state.camera as THREE.PerspectiveCamera;
            }}
          >
            <ambientLight intensity={0.7} />
            <pointLight position={[10, 10, 10]} />
            <OrbitControls
              ref={p.controlsRef}
              onChange={p.handleOrbitChange}
              enableZoom
              enablePan
              enableRotate
              target={new THREE.Vector3(...p.observerPosition)}
            />
            <SceneCore />
          </Canvas>
        )}
      </div>

      {/* Replay banner – center top */}
      {p.isReplaying && p.replayFrames[p.playbackIndex] && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 text-xs bg-black/70 text-white p-2 rounded z-50">
          ⏪ Replaying Frame #{p.playbackIndex}
        </div>
      )}

      {/* Basic plugin HUD */}
      <PluginHUD />

      {/* Collapse stats export – bottom-left over canvas */}
      <div
        className="absolute bottom-4 left-4 text-xs text-white bg-black/70 rounded-md p-2 z-50 space-y-2"
        role="region"
        aria-label="collapse-export"
      >
        <div>
          🕓 Tick Filter: <strong>{p.tickFilter ?? "—"}</strong>
        </div>
        <div>
          📉 Collapsed Nodes:{" "}
          <strong>
            {(p.mergedNodes ?? []).reduce(
              (acc: number, n: any) => acc + (n?.collapse_state === "collapsed" ? 1 : 0),
              0
            )}
          </strong>
        </div>
        <button
          type="button"
          className="w-full mt-1 px-3 py-1 bg-indigo-600 hover:bg-indigo-500 rounded text-white"
          onClick={() => {
            const exportData = (p.mergedNodes ?? [])
              .filter((n: any) => (p.showCollapsed ? true : n?.collapse_state !== "collapsed"))
              .map((n: any) => ({
                id: n?.id,
                label: n?.label,
                tick: n?.tick,
                state: n?.collapse_state,
                entropy: n?.entropy,
                goalMatchScore: n?.goalMatchScore,
                rewriteSuccessProb: n?.rewriteSuccessProb,
              }));
            const blob = new Blob([JSON.stringify(exportData, null, 2)], {
              type: "application/json",
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `collapse_timeline_tick${p.tickFilter ?? "all"}.json`;
            a.click();
            URL.revokeObjectURL(url);
          }}
        >
          ⬇️ Export Collapse Timeline
        </button>
      </div>
    </>
  );
};

export default QuantumFieldCanvasView;