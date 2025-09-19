// File: frontend/components/Hologram/QuantumFieldCanvasView.tsx
import * as React from "react";
import * as THREE from "three";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import { QWaveBeam, BeamProps } from "@/components/QuantumField/beam_renderer";
import PredictedLayerRenderer from "@/components/QuantumField/PredictedLayerRenderer";
import PluginHUD from "../../plugins/PluginHUD";
import EmotionOverlay from "@/components/QuantumField/EmotionOverlay";
import ScrollReplayOverlay from "@/components/QuantumField/ScrollReplayOverlay";
import StrategyOverlay from "@/components/QuantumField/StrategyOverlay";
import ObserverViewport from "@/components/QuantumField/ObserverViewport";
import MemoryScroller from "@/components/QuantumField/MemoryScroller";
import ClusterZoomRenderer from "@/components/QuantumField/cluster_zoom_renderer";
import HoverMutationTrace from "@/components/QuantumField/HoverMutationTrace";
import MultiNodeCollapseTrail from "@/components/QuantumField/MultiNodeCollapseTrail";
import BreakthroughDeadendTrail from "@/components/QuantumField/BreakthroughDeadendTrail";
import HolographicCausalityTrails from "@/components/QuantumField/Replay/holographic_causality_trails";
import BeamLogicOverlay from "@/components/QuantumField/BeamLogicOverlay";
import { QWavePreviewPanel } from "@/components/QuantumField/QWavePreviewPanel";
import EntropyNode from "@/components/QuantumField/styling/EntropyNode";
import HoverAgentLogicView from "@/components/QuantumField/Memory/hover_agent_logic_view";
import { MeshEmotionPulse, HtmlEmotionPulse } from "@/components/QuantumField/EmotionPulseOverlay";
import renderQWaveBeams from "./renderQWaveBeams";
import { Node } from "@/components/QuantumField/Node";
import { LinkLine } from "@/components/QuantumField/LinkLine";
import { ReplayBranchSelector } from "@/components/QuantumField/ReplayBranchSelector";

type FiberInit = { camera: THREE.Camera };

type ViewProps = {
  // props passed from parent
  qwaveBeams: React.ReactNode;

  isReplaying: boolean;
  replayFrames: any[];
  playbackIndex: number;
  setIsReplaying: React.Dispatch<React.SetStateAction<boolean>>;
  setPlaybackIndex: React.Dispatch<React.SetStateAction<number>>;

  // Trails (optional)
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

  beamData: any[] | null;
  setSelectedBeam: React.Dispatch<React.SetStateAction<any | null>>;

  mergedNodes: any[];
  mergedLinks: any[];

  onTeleport?: (id: string) => void;

  showPredictedLayer: boolean;
  predictedMode: boolean;
  predictedOverlay: boolean; // boolean toggle (overlay content passed in parent if any)
  splitScreen: boolean;

  handleOrbitChange: () => void;

  // HUD toggles
  onTogglePredictedLayer: () => void;
  onToggleSplitScreen: () => void;
  onTogglePredictedMode: () => void;
  onTogglePredictedOverlay: () => void;

  // panel bits
  tickFilter?: number;
  showCollapsed: boolean;
  others: any;

  // live scene (from parent main file handoff)
  beams?: any[];
  liveNodes?: any[];
  liveLinks?: any[];

  // optional overlay data (if parent provides it)
  predictedOverlayData?: { nodes: any[]; links: any[] } | null;
};

const QuantumFieldCanvasView: React.FC<ViewProps> = (p) => {
  // ---- TS prop-shim: relax prop checking for downstream UI components ----
  const LinkLineAny                   = LinkLine as unknown as React.FC<any>;
  const PredictedLayerRendererAny     = PredictedLayerRenderer as unknown as React.FC<any>;
  const ClusterZoomRendererAny        = ClusterZoomRenderer as unknown as React.FC<any>;
  const ScrollReplayOverlayAny        = ScrollReplayOverlay as unknown as React.FC<any>;
  const StrategyOverlayAny            = StrategyOverlay as unknown as React.FC<any>;
  const ObserverViewportAny           = ObserverViewport as unknown as React.FC<any>;
  const MemoryScrollerAny             = MemoryScroller as unknown as React.FC<any>;
  const HoverMutationTraceAny         = HoverMutationTrace as unknown as React.FC<any>;
  const MultiNodeCollapseTrailAny     = MultiNodeCollapseTrail as unknown as React.FC<any>;
  const BreakthroughDeadendTrailAny   = BreakthroughDeadendTrail as unknown as React.FC<any>;
  const HolographicCausalityTrailsAny = HolographicCausalityTrails as unknown as React.FC<any>;
  const BeamLogicOverlayAny           = BeamLogicOverlay as unknown as React.FC<any>;
  const QWavePreviewPanelAny          = QWavePreviewPanel as unknown as React.FC<any>;

  // ───────── helpers (keep INSIDE component so `p` is in scope) ─────────
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
      {(p.beamData ?? []).map((beam: any, idx: number) => (
        <group key={`bd-${idx}`} onClick={() => p.setSelectedBeam(beam)}>
          <QWaveBeam {...(beam as any)} />
        </group>
      ))}

      {/* links (use relaxed alias) */}
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

      {/* nodes + per-node overlays */}
      {(p.mergedNodes ?? []).map((node: any) => (
        <React.Fragment key={String(node.id)}>
          {(node.source === "dream" || node.isDream) && (
            <mesh position={node.position}>
              <ringGeometry args={[0.6, 0.75, 32]} />
              <meshBasicMaterial color="#d946ef" transparent opacity={0.75} />
            </mesh>
          )}

          <Node node={node} onTeleport={p.onTeleport} />

          {/* emotion pulses */}
          {node.emotion && (
            <>
              <MeshEmotionPulse node={node as any} />
              <HtmlEmotionPulse node={node as any} />
            </>
          )}

          {/* lock icon */}
          {node.locked && (
            <Html position={[node.position[0], node.position[1] + 1.5, node.position[2]]}>
              <div className="text-2xl text-red-500 font-bold drop-shadow">🔒</div>
            </Html>
          )}

          {/* entropy overlay */}
          {typeof node.entropy === "number" && (
            <EntropyNode position={node.position} entropy={node.entropy} nodeId={node.id} />
          )}

          {/* memory summary hover */}
          {node.memoryTrace && (
            <HoverAgentLogicView
              {...({
                position: [node.position[0], node.position[1] + 1.2, node.position[2]],
                logicSummary: node.memoryTrace.summary,
                containerId: node.memoryTrace.containerId,
              } as any)}
            />
          )}

          {/* spawn action */}
          <Html position={[node.position[0] + 0.8, node.position[1] + 1.2, node.position[2]]}>
            <button
              className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white px-2 py-1 rounded shadow"
              onClick={async () => {
                try {
                  const res = await fetch("/api/spawn_container_from_node", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ nodeId: node.id }),
                  });
                  const data = await res.json();
                  if (data.success && data.newContainerId) {
                    alert(`✅ Container spawned: ${data.newContainerId}`);
                  } else {
                    alert("⚠️ Failed to spawn container.");
                  }
                } catch (err) {
                  alert("🚨 Spawn failed: " + err);
                }
              }}
            >
              ➕ Spawn
            </button>
          </Html>
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
              {p.showPredictedLayer && <PredictedLayerRendererAny nodes={[]} links={[]} />}
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
            {p.showPredictedLayer && <PredictedLayerRendererAny nodes={[]} links={[]} visible />}
            <SceneCore />
          </Canvas>
        )}
      </div>

      {/* Replay banner */}
      {p.isReplaying && p.replayFrames[p.playbackIndex] && (
        <div className="absolute top-4 right-4 text-xs bg-black/70 text-white p-2 rounded z-50">
          ⏪ Replaying Frame #{p.playbackIndex}
        </div>
      )}

      {/* Overlays & HUD (DOM layers) */}
      <PluginHUD />

      {/* Predicted overlay draw-over (if parent gave data) */}
      {p.predictedOverlay && p.predictedOverlayData && (
        <PredictedLayerRendererAny
          nodes={(p.predictedOverlayData.nodes || []) as any}
          links={(p.predictedOverlayData.links || []) as any}
          fadedRealMode={p.predictedMode as any}
          visible
        />
      )}

      {/* Zoom, trails, strategy, viewport, scroller */}
      <ClusterZoomRendererAny
        nodes={p.mergedNodes as any}
        links={p.mergedLinks as any}
        radius={2.5}
        onZoomed={(ids: string[]) => console.log("🔍 Zoomed cluster:", ids)}
      />

      <ScrollReplayOverlayAny
        isReplaying={p.isReplaying}
        frames={p.replayFrames}
        playbackIndex={p.playbackIndex}
        onPlay={() => p.setIsReplaying(true)}
        onPause={() => p.setIsReplaying(false)}
        onSeek={p.setPlaybackIndex}
        visible={p.isReplaying}
      />

      <StrategyOverlayAny
        branches={p.availableBranches}
        selected={p.selectedBranch}
        onSelect={p.setSelectedBranch}
        onRetry={p.onRetryFromBranch}
        visible
      />

      <ObserverViewportAny
        position={p.observerPosition}
        direction={p.observerDirection}
        enabled
      />

      <MemoryScrollerAny
        frames={p.replayFrames}
        onJump={p.setPlaybackIndex}
        active={p.isReplaying}
      />

      <HoverMutationTraceAny beam={undefined as any} />
      <MultiNodeCollapseTrailAny segments={p.collapseTrails as any} visible />
      <BreakthroughDeadendTrailAny segments={p.deadendTrails as any} visible />
      <HolographicCausalityTrailsAny
        segments={[...(p.collapseTrails as any[]), ...(p.breakthroughTrails as any[])]}
        trails={p.collapseTrails as any}
      />

      <BeamLogicOverlayAny beam={undefined as any} />

      {/* QWave preview panel */}
      <div className="absolute right-2 top-2 max-w-sm">
        <QWavePreviewPanelAny
          beams={(p.beams || []) as any}
          onSelect={p.setSelectedBeam as any}
          selectedBeamId={undefined as any}
          beamMetadata={undefined as any}
        />
      </div>
      <div
        className="absolute top-4 right-4 text-xs text-white bg-black/70 rounded-md p-2 z-50 space-y-2"
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
            const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" });
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

      {/* Presence (render your PresenceLayer here if you want cursors) */}
      {/* <PresenceLayer others={p.others} /> */}
    </>
  );
};

export default QuantumFieldCanvasView;

