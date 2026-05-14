import * as React from "react";
import { useRouter } from "next/router";

// If you have shadcn/ui installed, uncomment these and replace the plain buttons/inputs below
// import { Button } from "@/components/ui/button";
// import { Input } from "@/components/ui/input";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────
interface GlyphCell {
  id: string;
  logic: string;
  position: number[]; // [x,y,z,t]
  emotion?: string;
  prediction?: string;
  sqi_score?: number;
  validated?: boolean;
  result?: string;
  wave_beams?: any[];
  meta?: Record<string, any>;
  codexlang_render?: string; // client-side prettified logic (optional)
}

type Direction = "forward" | "reverse";

export default function SciSqsPanel(props: {
  wsUrl?: string;
  containerId?: string;
  file?: string; // optional initial file (.atom or .sqs.json)
  authToken?: string; // optional bearer (defaults to env or none)
}) {
  const router = useRouter();

  // ───────────────────────────────────────────────────────────────────────────
  // State
  // ───────────────────────────────────────────────────────────────────────────
  const [sheetFile, setSheetFile] = React.useState<string>(
    normalizeAtomPath(
      (typeof props.file === "string" && props.file) ||
        (typeof router.query.file === "string"
          ? (router.query.file as string)
          : "backend/data/sheets/example_sheet.atom")
    )
  );
  const [cells, setCells] = React.useState<GlyphCell[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [rawMode, setRawMode] = React.useState(false);
  const [traceMode, setTraceMode] = React.useState<Direction>("forward");
  const [lightconeTrace, setLightconeTrace] = React.useState<any[]>([]);

  // derive container id
  const containerId = React.useMemo(
    () => props.containerId || sheetFile,
    [props.containerId, sheetFile]
  );

  const AUTH_TOKEN = React.useMemo(() => {
    return (
      props.authToken ||
      (typeof process !== "undefined"
        ? process.env.NEXT_PUBLIC_AUTH_TOKEN
        : undefined) ||
      ""
    );
  }, [props.authToken]);

  // ───────────────────────────────────────────────────────────────────────────
  // Effects
  // ───────────────────────────────────────────────────────────────────────────

  // NOTE: removed URL-rewrite effect so /sci doesn't force ?file=...
  // (we still *read* router.query.file if present)

  React.useEffect(() => {
    if (typeof router.query.file === "string") {
      setSheetFile(normalizeAtomPath(router.query.file as string));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router.query.file]);

  React.useEffect(() => {
    fetchSheet();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sheetFile, containerId]);

  // Optional WS live HUD (no-op if not configured)
  React.useEffect(() => {
    if (typeof window === "undefined") return;
    if (!props.wsUrl) return;

    const url = `${props.wsUrl}${
      props.wsUrl.includes("?") ? "&" : "?"
    }container_id=${encodeURIComponent(containerId)}`;

    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(url);
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg?.type === "qpu_beam_timeline" && Array.isArray(msg.timeline)) {
            setLightconeTrace(msg.timeline);
          }
        } catch {
          // ignore malformed events
        }
      };
    } catch {
      /* silent */
    }
    return () => {
      try {
        ws?.close();
      } catch {
        /* noop */
      }
    };
  }, [props.wsUrl, containerId]);

  // ───────────────────────────────────────────────────────────────────────────
  // Data fetchers
  // ───────────────────────────────────────────────────────────────────────────
  async function fetchSheet() {
    setLoading(true);
    setError(null);
    try {
      const url = `/api/atomsheet?file=${encodeURIComponent(
        sheetFile
      )}&container_id=${encodeURIComponent(containerId)}`;
      const res = await fetch(url, {
        headers: AUTH_TOKEN ? { Authorization: `Bearer ${AUTH_TOKEN}` } : {},
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = await res.json();
      const incoming: GlyphCell[] = (data.cells || []).map((c: GlyphCell) => ({
        ...c,
        codexlang_render: prettifyLogic(c.logic),
      }));
      setCells(incoming);
    } catch (e: any) {
      setError(e?.message || String(e));
      setCells([]);
    } finally {
      setLoading(false);
    }
  }

  async function fetchLightCone(entryId: string, dir: Direction) {
    try {
      const url =
        `/api/lightcone` +
        `?file=${encodeURIComponent(sheetFile)}` +
        `&entry_id=${encodeURIComponent(entryId)}` +
        `&direction=${encodeURIComponent(dir)}` +
        (containerId
          ? `&container_id=${encodeURIComponent(containerId)}`
          : "");
      const res = await fetch(url, {
        headers: AUTH_TOKEN ? { Authorization: `Bearer ${AUTH_TOKEN}` } : {},
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = await res.json();
      // API returns {trace:[...]} for single
      setLightconeTrace(data.trace || []);
    } catch (e) {
      // degrade gracefully
      setLightconeTrace([]);
    }
  }

  // ───────────────────────────────────────────────────────────────────────────
  // Helpers
  // ───────────────────────────────────────────────────────────────────────────
  function normalizeAtomPath(v: string): string {
    if (!v) return "example_sheet.atom";
    if (/\.sqs\.json$/i.test(v)) return v.replace(/\.sqs\.json$/i, ".atom");
    return /\.[A-Za-z0-9]+$/.test(v) ? v : `${v}.atom`;
  }

  function prettifyLogic(logic: string): string {
    // super light prettifier; replace with CodexLang renderer if you have it client-side
    return `⟦${logic}⟧`;
  }

  const dims = React.useMemo(() => {
    const maxX = Math.max(0, ...cells.map((c) => c.position?.[0] ?? 0));
    const maxY = Math.max(0, ...cells.map((c) => c.position?.[1] ?? 0));
    const maxZ = Math.max(0, ...cells.map((c) => c.position?.[2] ?? 0));
    const maxT = Math.max(0, ...cells.map((c) => c.position?.[3] ?? 0));
    return { maxX, maxY, maxZ, maxT };
  }, [cells]);

  // Build sparse 4D grid → [t][z][y][x]
  const grid = React.useMemo(() => {
    const { maxX, maxY, maxZ, maxT } = dims;
    const G: (GlyphCell | null)[][][][] = Array.from(
      { length: maxT + 1 },
      () =>
        Array.from({ length: maxZ + 1 }, () =>
          Array.from({ length: maxY + 1 }, () =>
            Array.from({ length: maxX + 1 }, () => null)
          )
        )
    );
    for (const c of cells) {
      const [x, y, z, t] = c.position || [0, 0, 0, 0];
      G[t][z][y][x] = c;
    }
    return G;
  }, [cells, dims]);

  // ───────────────────────────────────────────────────────────────────────────
  // Render
  // ───────────────────────────────────────────────────────────────────────────
  return (
    <div className="p-6 text-zinc-100">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-5">
        <div>
          <div className="text-2xl font-bold">🧮 SQS Panel</div>
          <div className="text-xs text-zinc-400">
            container: {containerId || "—"}
          </div>
        </div>
        <div className="flex gap-2 flex-wrap items-center">
          <input
            value={sheetFile}
            onChange={(e) => setSheetFile(normalizeAtomPath(e.target.value))}
            placeholder="path/to/sheet.atom"
            className="px-3 py-2 text-sm rounded border border-white/10 bg-white/5 focus:outline-none focus:ring-1 focus:ring-white/30"
            style={{ minWidth: 280 }}
          />
          <button
            className="px-3 py-2 text-sm rounded bg-white/10 hover:bg-white/20 border border-white/10"
            onClick={fetchSheet}
            disabled={loading}
            title="Reload"
          >
            {loading ? "Loading…" : "Reload"}
          </button>
          <button
            className="px-3 py-2 text-sm rounded bg-white/10 hover:bg-white/20 border border-white/10"
            onClick={() => setRawMode((v) => !v)}
            title="Toggle render/raw"
          >
            {rawMode ? "Show Rendered" : "Show Raw"}
          </button>
          <button
            className="px-3 py-2 text-sm rounded bg-white/10 hover:bg-white/20 border border-white/10"
            onClick={() =>
              setTraceMode((m) => (m === "forward" ? "reverse" : "forward"))
            }
            title="Toggle LightCone direction"
          >
            {traceMode === "forward" ? "→ Forward" : "← Reverse"}
          </button>
        </div>
      </div>

      {/* Errors */}
      {error && (
        <div className="mb-4 text-sm text-red-300 bg-red-500/10 border border-red-500/20 rounded p-3">
          {error}
        </div>
      )}

      {/* LightCone trace (if present) */}
      {lightconeTrace && lightconeTrace.length > 0 && (
        <div className="mb-5">
          <div className="text-sm font-semibold mb-2">
            🌌 LightCone Trace ({traceMode})
          </div>
          <div className="text-xs bg-white/5 border border-white/10 rounded p-3 max-h-48 overflow-auto">
            <pre className="whitespace-pre-wrap leading-relaxed">
              {JSON.stringify(lightconeTrace, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Grid */}
      {cells.length === 0 ? (
        <div className="text-sm text-zinc-400">No cells to display.</div>
      ) : (
        grid.map((zLayers, t) => (
          <div key={`t-${t}`} className="mb-6">
            <div className="text-lg font-semibold mb-2">Time Layer {t}</div>
            {zLayers.map((rows, z) => (
              <div key={`t-${t}-z-${z}`} className="mb-3">
                <div className="text-sm font-medium mb-1">Z Level {z}</div>
                <div
                  className="grid gap-2"
                  style={{
                    gridTemplateColumns: `repeat(${
                      dims.maxX + 1
                    }, minmax(140px, 1fr))`,
                  }}
                >
                  {rows.map((row, y) =>
                    row?.map((cell, x) => (
                      <div
                        key={`cell-${t}-${z}-${y}-${x}`}
                        className="h-28 p-2 border border-white/10 rounded bg-white/[0.04] hover:bg-white/[0.07] transition-colors"
                        onMouseEnter={() =>
                          cell?.id && fetchLightCone(cell.id, traceMode)
                        }
                        onMouseLeave={() => setLightconeTrace([])}
                        title={
                          cell
                            ? `ID: ${cell.id}\nPos: [${cell.position?.join(
                                ", "
                              )}]`
                            : "Empty"
                        }
                      >
                        {cell ? (
                          <div className="h-full flex flex-col">
                            <div className="text-[11px] font-mono break-words line-clamp-3">
                              {rawMode
                                ? cell.logic
                                : cell.codexlang_render ||
                                  prettifyLogic(cell.logic)}
                            </div>
                            <div className="mt-auto flex items-center justify-between text-[10px] pt-1">
                              <span className="opacity-80">{badge(cell)}</span>
                              <div className="flex items-center gap-2">
                                {typeof cell.sqi_score === "number" && (
                                  <span
                                    className="px-1 rounded bg-white/10 border border-white/10"
                                    title="SQI score"
                                  >
                                    SQI {round1(cell.sqi_score)}
                                  </span>
                                )}
                                {/* Nested expand (A5) */}
                                {(cell as any)?.meta?.nested?.type ===
                                  "ref" &&
                                  (cell as any)?.meta?.nested?.path && (
                                    <button
                                      className="text-[10px] px-1 py-[2px] rounded border border-white/10 hover:bg-white/10"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        const childPath = (cell as any).meta
                                          .nested.path as string;
                                        router.push(
                                          `/sci/sci_atomsheet_panel?file=${encodeURIComponent(
                                            childPath
                                          )}`
                                        );
                                      }}
                                      title="Open nested AtomSheet"
                                    >
                                      ↘ expand
                                    </button>
                                  )}
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="h-full w-full grid place-items-center text-zinc-500">
                            ·
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            ))}
          </div>
        ))
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// UI helpers
// ─────────────────────────────────────────────────────────────────────────────
function badge(c?: GlyphCell) {
  if (!c) return null;
  const v = c.validated;
  if (v === true) return <span className="text-green-300">✅ valid</span>;
  if (v === false) return <span className="text-red-300">❌ invalid</span>;
  return <span className="text-zinc-300">•</span>;
}

function round1(n?: number) {
  if (typeof n !== "number") return "";
  return Math.round(n * 10) / 10;
}