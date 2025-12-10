import React, { useMemo, useState } from "react";
import { importHoloSnapshot } from "../lib/api/holo";

type ProgramFrameRole = "input" | "mul" | "add" | "sub" | "output";

type ProgramFrame = {
  id: string;
  role: ProgramFrameRole | string;
  label: string;
  order: number;
  config?: Record<string, any>;
};

type Holo = {
  holo_id?: string;
  container_id?: string;
  name?: string;
  timefold?: { tick?: number };
  version?: { revision?: number; [k: string]: any };
  extra?: { program_frames?: ProgramFrame[]; [k: string]: any };
  ghx?: {
    nodes?: Array<{ id: string; label?: string; kind?: string }>;
    edges?: Array<{ id?: string; source: string; target: string; kind?: string }>;
    [k: string]: any;
  };
  [k: string]: any;
};

type RunResult = {
  status?: string;
  message?: string | null;
  container_id?: string;
  holo_id?: string | null;
  tick?: number | null;
  beams?: any[];
  metrics?: Record<string, any>;
  output?: any;
};

type Props = {
  value: Holo;
  onChange?: (next: Holo) => void;
  apiBase?: string; // default "/api"
};

export const HoloProgramEditor: React.FC<Props> = ({
  value,
  onChange,
  apiBase = "/api",
}) => {
  const [localHolo, setLocalHolo] = useState<Holo>(() => value || {});
  const [selectedFrameId, setSelectedFrameId] = useState<string | null>(null);
  const [inputX, setInputX] = useState<string>("10");
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // --- helpers ---------------------------------------------------

  const frames: ProgramFrame[] = useMemo(
    () => localHolo.extra?.program_frames || [],
    [localHolo]
  );

  const edges = useMemo(
    () => localHolo.ghx?.edges || [],
    [localHolo]
  );

  const updateHolo = (fn: (prev: Holo) => Holo) => {
    setLocalHolo((prev) => {
      const next = fn(prev);
      onChange?.(next);
      return next;
    });
  };

  const ensureGhxNodesFromFrames = (frames: ProgramFrame[]) => {
    const existingNodes = localHolo.ghx?.nodes || [];
    const existingIds = new Set(existingNodes.map((n) => n.id));
    const newNodes = [...existingNodes];

    frames.forEach((f) => {
      if (!existingIds.has(f.id)) {
        newNodes.push({
          id: f.id,
          label: f.label || f.id,
          kind: "frame",
        });
      }
    });

    return newNodes;
  };

  // --- 1) Add frame ---------------------------------------------

  const addFrame = (role: ProgramFrameRole) => {
    const idBase = role === "input" ? "input" :
                   role === "output" ? "output" : role;
    let idx = frames.length;
    let id = `${idBase}_${idx}`;
    const existingIds = new Set(frames.map((f) => f.id));

    while (existingIds.has(id)) {
      idx += 1;
      id = `${idBase}_${idx}`;
    }

    const frame: ProgramFrame = {
      id,
      role,
      label: `${role.toUpperCase()} ${idx}`,
      order: frames.length,
      config:
        role === "mul"
          ? { factor: 2 }
          : role === "add" || role === "sub"
          ? { value: 1 }
          : role === "input"
          ? { from: "x" }
          : role === "output"
          ? { to: "y" }
          : {},
    };

    updateHolo((prev) => {
      const extra = { ...(prev.extra || {}) };
      const program_frames = [...(extra.program_frames || []), frame];
      extra.program_frames = program_frames;

      const ghx = { ...(prev.ghx || {}) };
      ghx.nodes = ensureGhxNodesFromFrames(program_frames);

      return { ...prev, extra, ghx };
    });
    setSelectedFrameId(id);
  };

  // --- 2) Update frame label / config ----------------------------

  const updateFrame = (id: string, patch: Partial<ProgramFrame>) => {
    updateHolo((prev) => {
      const extra = { ...(prev.extra || {}) };
      const program_frames = (extra.program_frames || []).map((f: ProgramFrame) =>
        f.id === id ? { ...f, ...patch, config: { ...(f.config || {}), ...(patch.config || {}) } } : f
      );
      extra.program_frames = program_frames;

      const ghx = { ...(prev.ghx || {}) };
      // keep nodes in sync with labels
      const nodes = ensureGhxNodesFromFrames(program_frames).map((n) =>
        n.id === id ? { ...n, label: patch.label || n.label } : n
      );
      ghx.nodes = nodes;

      return { ...prev, extra, ghx };
    });
  };

  // --- 3) Add edge ----------------------------------------------

  const addEdge = (source: string, target: string) => {
    if (!source || !target || source === target) return;

    updateHolo((prev) => {
      const ghx = { ...(prev.ghx || {}) };
      const edges = [...(ghx.edges || [])];

      // de-dupe
      if (edges.some((e) => e.source === source && e.target === target)) {
        return prev;
      }

      edges.push({
        id: `e_${edges.length}`,
        source,
        target,
        kind: "flow",
      });
      ghx.edges = edges;
      return { ...prev, ghx };
    });
  };

  // --- 4) Load demo calculator program (y = 2x + 3) --------------

  const loadDemoCalculator = () => {
    const demoFrames: ProgramFrame[] = [
      {
        id: "f1",
        role: "input",
        label: "Load x",
        order: 0,
        config: { from: "x" },
      },
      {
        id: "f2",
        role: "mul",
        label: "Multiply by 2",
        order: 1,
        config: { factor: 2 },
      },
      {
        id: "f3",
        role: "add",
        label: "Add 3",
        order: 2,
        config: { value: 3 },
      },
      {
        id: "f4",
        role: "output",
        label: "Write to y",
        order: 3,
        config: { to: "y" },
      },
    ];

    const demoEdges = [
      { id: "e1", source: "f1", target: "f2", kind: "flow" },
      { id: "e2", source: "f2", target: "f3", kind: "flow" },
      { id: "e3", source: "f3", target: "f4", kind: "flow" },
    ];

    updateHolo((prev) => {
      const next: Holo = {
        ...prev,
        holo_id: prev.holo_id || "demo:holo_calculator",
        container_id: prev.container_id || "demo_container",
        name: prev.name || "Demo Calculator Hologram",
        timefold: { ...(prev.timefold || {}), tick: 0 },
        version: { ...(prev.version || {}), revision: prev.version?.revision || 1 },
        extra: {
          ...(prev.extra || {}),
          program_frames: demoFrames,
        },
        ghx: {
          ...(prev.ghx || {}),
          nodes: ensureGhxNodesFromFrames(demoFrames),
          edges: demoEdges,
        },
      };
      return next;
    });
    setSelectedFrameId("f1");
  };

  // --- 5) Run via /api/holo/run ---------------------------------

  const [isSaving, setIsSaving] = useState(false);

  const resolveActiveContainerId = (): string => {
    if (localHolo.container_id) return localHolo.container_id;
    if (value?.container_id) return value.container_id;

    if (typeof window !== "undefined") {
      try {
        const params = new URLSearchParams(window.location.search);
        const fromQuery =
          params.get("container") || params.get("containerId");
        if (fromQuery) return fromQuery;
      } catch {
        // ignore
      }
    }
    return "dc_aion_core"; // dev fallback
  };

  // --- 5) Run via /api/holo/run ---------------------------------
  const runProgram = async () => {
    setIsRunning(true);
    setError(null);
    setRunResult(null);

    try {
      const res = await fetch(`${apiBase}/holo/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          holo: localHolo,
          input_ctx: { x: Number(inputX) },
          mode: "qqc",
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }

      const data: any = await res.json();
      setRunResult(data);

      if (typeof window !== "undefined") {
        const updatedHolo = data.updated_holo || localHolo || null;
        (window as any).__DEVTOOLS_LAST_HOLO = updatedHolo;

        const containerId =
          data.container_id ||
          updatedHolo?.container_id ||
          localHolo.container_id ||
          value?.container_id ||
          "dc_aion_core";

        window.dispatchEvent(
          new CustomEvent("devtools.holo_run", {
            detail: {
              source: "program_builder",
              container_id: containerId,
              result: data,
            },
          }),
        );

        const ghx = data.ghx;
        if (ghx && Array.isArray(ghx.nodes) && Array.isArray(ghx.edges)) {
          (window as any).__DEVTOOLS_LAST_GHX = ghx;
          window.dispatchEvent(
            new CustomEvent("devtools.ghx", {
              detail: { ghx },
            }),
          );
        }
      }
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setIsRunning(false);
    }
  };

  // --- 6) Save current program as a .holo snapshot ----------------
  const saveProgramAsHolo = async () => {
    if (!frames.length) return;

    setIsSaving(true);
    setError(null);

    try {
      const containerId =
        localHolo.container_id ?? value?.container_id ?? "dc_aion_core";

      // Build a GHX mini-graph from frames + edges so the 3D canvas has something
      const nodes = frames.map((f) => ({
        id: f.id,
        label: f.label,
        type: "holo_node",
        tags: [],
        meta: {},
        data: { from: "holo", role: f.role, config: f.config ?? {} },
      }));

      const edgeList = edges.map((e, idx) => {
        const id = e.id || `e${idx + 1}`;
        return {
          id,
          src: e.source,
          dst: e.target,
          source: e.source,
          target: e.target,
          kind: e.kind || "flow",
          tags: [],
          meta: {},
          data: { from: "holo" },
        };
      });

      const ghxPacket = {
        ghx_version: "1.0",
        origin:
          localHolo.holo_id ||
          `holo:container/${containerId}/t=0/v1`,
        container_id: containerId,
        nodes,
        edges: edgeList,
        metadata: {
          holo_id: localHolo.holo_id,
          kind: "program_hologram",
          timefold: {
            t_label: null,
            tick: (localHolo.timefold as any)?.tick ?? 0,
          },
        },
      };

      const holoToSave: any = {
        ...(localHolo as any),
        container_id: containerId,
        kind: localHolo.kind || "program",
        name: localHolo.name || "demo_calculator",
        ghx: ghxPacket,
        extra: {
          ...(localHolo.extra || {}),
          program_frames: frames,
          program_edges: edges,
        },
      };

      // 🚀 Use shared API helper (POST /api/holo/import)
      const savedHolo = (await importHoloSnapshot(holoToSave)) as any;

      // TS: savedHolo is HoloIR; localHolo state is typed as Holo → cast
      setLocalHolo(savedHolo as any);

      // Seed globals + notify HologramContainerView so Holo Files refreshes
      if (typeof window !== "undefined") {
        (window as any).__DEVTOOLS_LAST_HOLO = savedHolo;
        window.dispatchEvent(
          new CustomEvent("devtools.holo_saved", {
            detail: { holo: savedHolo },
          }),
        );
      }
    } catch (e: any) {
      console.error("Save as .holo failed", e);
      setError(e?.message || String(e));
    } finally {
      setIsSaving(false);
    }
  };
  // --- render ----------------------------------------------------

  const selectedFrame = frames.find((f) => f.id === selectedFrameId) || null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, padding: 12 }}>
      {/* Top row: actions */}
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <strong>Hologram Program Builder</strong>
        <button type="button" onClick={loadDemoCalculator}>
          Load demo: y = 2·x + 3
        </button>

        <span style={{ marginLeft: "auto", fontSize: 12, opacity: 0.7 }}>
          container: {localHolo.container_id || "—"} · holo: {localHolo.holo_id || "—"}
        </span>
      </div>

      {/* Palette + frame list */}
      <div style={{ display: "flex", gap: 16 }}>
        {/* Palette */}
        <div style={{ minWidth: 140 }}>
          <div style={{ marginBottom: 6, fontWeight: 600 }}>Blocks</div>
          {(["input", "mul", "add", "sub", "output"] as ProgramFrameRole[]).map((role) => (
            <button
              key={role}
              type="button"
              onClick={() => addFrame(role)}
              style={{ display: "block", width: "100%", marginBottom: 4 }}
            >
              + {role.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Frames */}
        <div style={{ flex: 1 }}>
          <div style={{ marginBottom: 6, fontWeight: 600 }}>Frames</div>
          {frames.length === 0 && (
            <div style={{ fontSize: 12, opacity: 0.7 }}>No frames yet.</div>
          )}
          {frames.map((f) => (
            <div
              key={f.id}
              onClick={() => setSelectedFrameId(f.id)}
              style={{
                border: f.id === selectedFrameId ? "2px solid #4f46e5" : "1px solid #ddd",
                borderRadius: 6,
                padding: 6,
                marginBottom: 4,
                cursor: "pointer",
                background: "#fafafa",
              }}
            >
              <div style={{ fontSize: 12, opacity: 0.7 }}>{f.id}</div>
              <div style={{ fontWeight: 600 }}>
                {f.label} <span style={{ fontSize: 11, opacity: 0.7 }}>({f.role})</span>
              </div>
            </div>
          ))}
        </div>

        {/* Frame editor */}
        <div style={{ flex: 1 }}>
          <div style={{ marginBottom: 6, fontWeight: 600 }}>Frame details</div>
          {!selectedFrame && (
            <div style={{ fontSize: 12, opacity: 0.7 }}>Select a frame to edit its config.</div>
          )}
          {selectedFrame && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <label style={{ fontSize: 12 }}>
                Label
                <input
                  style={{ width: "100%" }}
                  value={selectedFrame.label}
                  onChange={(e) => updateFrame(selectedFrame.id, { label: e.target.value })}
                />
              </label>

              {selectedFrame.role === "input" && (
                <label style={{ fontSize: 12 }}>
                  From key (e.g. x)
                  <input
                    style={{ width: "100%" }}
                    value={selectedFrame.config?.from || ""}
                    onChange={(e) =>
                      updateFrame(selectedFrame.id, { config: { from: e.target.value } })
                    }
                  />
                </label>
              )}

              {(selectedFrame.role === "mul" ||
                selectedFrame.role === "add" ||
                selectedFrame.role === "sub") && (
                <label style={{ fontSize: 12 }}>
                  {selectedFrame.role === "mul" ? "Factor" : "Value"}
                  <input
                    type="number"
                    style={{ width: "100%" }}
                    value={
                      selectedFrame.role === "mul"
                        ? selectedFrame.config?.factor ?? 1
                        : selectedFrame.config?.value ?? 0
                    }
                    onChange={(e) =>
                      updateFrame(selectedFrame.id, {
                        config:
                          selectedFrame.role === "mul"
                            ? { factor: Number(e.target.value) }
                            : { value: Number(e.target.value) },
                      })
                    }
                  />
                </label>
              )}

              {selectedFrame.role === "output" && (
                <label style={{ fontSize: 12 }}>
                  To key (e.g. y)
                  <input
                    style={{ width: "100%" }}
                    value={selectedFrame.config?.to || ""}
                    onChange={(e) =>
                      updateFrame(selectedFrame.id, { config: { to: e.target.value } })
                    }
                  />
                </label>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Edges builder */}
      <div style={{ marginTop: 8 }}>
        <div style={{ marginBottom: 6, fontWeight: 600 }}>Edges (flow)</div>
        <EdgeBuilder frames={frames} edges={edges} onAdd={addEdge} />
      </div>

      {/* Run + Save panel */}
      <div
        style={{
          marginTop: 12,
          padding: 8,
          borderRadius: 6,
          border: "1px solid #ddd",
          background: "#fcfcff",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontWeight: 600 }}>Run program</span>
          <span style={{ fontSize: 12, opacity: 0.7 }}>
            Calls {apiBase}/holo/run → output.program_output
          </span>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginTop: 8,
          }}
        >
          <label style={{ fontSize: 12 }}>
            x =
            <input
              type="number"
              value={inputX}
              onChange={(e) => setInputX(e.target.value)}
              style={{ marginLeft: 4, width: 80 }}
            />
          </label>

          <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
            <button
              type="button"
              onClick={saveProgramAsHolo}
              disabled={isSaving || frames.length === 0}
              style={{
                padding: "4px 10px",
                borderRadius: 999,
                border: "1px solid #0ea5e9",
                background: isSaving ? "#e5e7eb" : "#e0f2fe",
                color: isSaving ? "#6b7280" : "#0f172a",
                cursor: isSaving ? "default" : "pointer",
                fontSize: 11,
                fontWeight: 500,
                whiteSpace: "nowrap",
              }}
            >
              {isSaving ? "Saving…" : "Save as .holo"}
            </button>

            <button type="button" onClick={runProgram} disabled={isRunning}>
              {isRunning ? "Running…" : "▶ Run .holo"}
            </button>
          </div>
        </div>

        {error && (
          <div style={{ marginTop: 8, color: "red", fontSize: 12 }}>
            Error: {error}
          </div>
        )}

        {runResult && (
          <div style={{ marginTop: 8, fontSize: 12 }}>
            <div>
              <strong>Status:</strong> {runResult.status || "—"}
            </div>
            <div>
              <strong>Output.program_output:</strong>{" "}
              <code>
                {JSON.stringify(
                  runResult.output?.program_output ?? runResult.output ?? {},
                  null,
                  2,
                )}
              </code>
            </div>
            <div style={{ marginTop: 4 }}>
              <strong>Metrics:</strong>
              <pre style={{ fontSize: 11, background: "#f5f5f5", padding: 6 }}>
                {JSON.stringify(runResult.metrics || {}, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Small helper subcomponent – edge adder UI
type EdgeBuilderProps = {
  frames: ProgramFrame[];
  edges: Array<{ id?: string; source: string; target: string; kind?: string }>;
  onAdd: (source: string, target: string) => void;
};

const EdgeBuilder: React.FC<EdgeBuilderProps> = ({ frames, edges, onAdd }) => {
  const [src, setSrc] = useState("");
  const [dst, setDst] = useState("");

  const add = () => {
    if (!src || !dst || src === dst) return;
    onAdd(src, dst);
    setSrc("");
    setDst("");
  };

  return (
    <div>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <select value={src} onChange={(e) => setSrc(e.target.value)}>
          <option value="">from…</option>
          {frames.map((f) => (
            <option key={f.id} value={f.id}>
              {f.id} ({f.role})
            </option>
          ))}
        </select>
        <span>→</span>
        <select value={dst} onChange={(e) => setDst(e.target.value)}>
          <option value="">to…</option>
          {frames.map((f) => (
            <option key={f.id} value={f.id}>
              {f.id} ({f.role})
            </option>
          ))}
        </select>
        <button type="button" onClick={add}>
          Add edge
        </button>
      </div>

      <div style={{ marginTop: 6, fontSize: 12 }}>
        {edges.length === 0 && <span style={{ opacity: 0.7 }}>No edges yet.</span>}
        {edges.length > 0 && (
          <ul style={{ paddingLeft: 16 }}>
            {edges.map((e, i) => (
              <li key={e.id || i}>
                {e.source} → {e.target} ({e.kind || "flow"})
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};