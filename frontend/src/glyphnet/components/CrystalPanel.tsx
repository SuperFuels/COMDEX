// Glyph_Net_Browser/src/components/CrystalPanel.tsx

import { useEffect, useState } from "react";
import { DevFieldHologram3DScene, GhxPacket } from "./DevFieldHologram3D";
import { GHXVisualizerField } from "./GHXVisualizerField";
import { PhotonStubPanel } from "./PhotonStubPanel";

import type { HoloIR } from "../lib/types/holo";
import { buildPhotonStubFromHolo, buildGhxFromHolo } from "../lib/rehydrate";

// Scope matches data/crystals/user/devtools/...
const CRYSTAL_SCOPE = "user/devtools";

type CrystalIndexItem = {
  motif_id: string;
  uri?: string;
  tick?: number;
  revision?: number;
  created_at?: string;
  pattern_strength?: number;
  SQI?: number;
  usage_count?: number;
  tags?: string[];
  path?: string;
  // Optional – if backend ever returns per-motif holo_id
  holo_id?: string;
};

type CrystalIndexResponse = {
  scope: string;
  count: number;
  items: CrystalIndexItem[];
};

type CrystalMeta = {
  motifId?: string;
  patternStrength?: number;
  sqi?: number;
  usageCount?: number;
  raw?: any;
};

function extractCrystalMeta(holo: HoloIR | null): CrystalMeta | null {
  if (!holo || !(holo as any).metadata) return null;
  const meta: any = (holo as any).metadata ?? {};

  const node =
    meta.crystal ??
    meta.motif ??
    meta.pattern ??
    meta.container ??
    {};

  const motifId =
    node.motif_id ??
    node.id ??
    node.pattern_id ??
    node.name ??
    undefined;

  const patternStrength =
    node.pattern_strength ?? node.strength ?? node.score;

  const usageCount =
    node.usage_count ?? node.usage ?? node.samples;

  const sqi =
    node.sqi ??
    node.SQI ??
    (node.metrics ? node.metrics.SQI : undefined);

  if (
    !motifId &&
    patternStrength == null &&
    sqi == null &&
    usageCount == null
  ) {
    return null;
  }

  return {
    motifId,
    patternStrength:
      typeof patternStrength === "number" ? patternStrength : undefined,
    sqi: typeof sqi === "number" ? sqi : undefined,
    usageCount:
      typeof usageCount === "number" ? usageCount : undefined,
    raw: node,
  };
}

function motifLabelFromPath(path?: string): string {
  if (!path) return "";
  const base = path.split("/").pop() ?? path; // motif-0003__t=3_v1.holo.json
  const left = base.split("__")[0] ?? base;   // motif-0003
  return left.replace(/\.holo\.json$/, "");
}

export default function CrystalPanel() {
  const [index, setIndex] = useState<CrystalIndexItem[]>([]);
  const [loadingIndex, setLoadingIndex] = useState(false);
  const [indexError, setIndexError] = useState<string | null>(null);

  const [activeEntry, setActiveEntry] = useState<CrystalIndexItem | null>(null);
  const [holo, setHolo] = useState<HoloIR | null>(null);
  const [loadingHolo, setLoadingHolo] = useState(false);
  const [holoError, setHoloError] = useState<string | null>(null);

  const [filter, setFilter] = useState("");
  const [focusMode, setFocusMode] = useState<"world" | "focus">("world");

  const toggleFocus = () =>
    setFocusMode((m) => (m === "world" ? "focus" : "world"));

  // 🔁 Rehydrate: push this crystal's GHX back into the Field Lab
  function handleRehydrateToField() {
    if (!holo) return;
    if (typeof window === "undefined") return;

    const packet = buildGhxFromHolo(holo);

    // 1) remember it globally so DevFieldCanvas / other views can seed from it
    (window as any).__DEVTOOLS_LAST_GHX = packet;

    // 2) broadcast to any listeners (Field tab, DevFieldCanvas, etc.)
    window.dispatchEvent(
      new CustomEvent("devtools.ghx", {
        detail: { ghx: packet },
      }),
    );

    // 3) ask DevTools to switch to the Field Lab tab
    window.dispatchEvent(
      new CustomEvent("devtools.switch_tab", {
        detail: { tool: "field" },
      }),
    );
  }

  // Load crystal index from /api/crystals/motifs
  useEffect(() => {
    let cancelled = false;
    setLoadingIndex(true);
    setIndexError(null);

    (async () => {
      try {
        const res = await fetch(
          `/api/crystals/motifs?scope=${encodeURIComponent(CRYSTAL_SCOPE)}`,
        );
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const json = (await res.json()) as CrystalIndexResponse;
        if (cancelled) return;

        const items = json.items ?? [];
        setIndex(items);
        if (items.length > 0) {
          setActiveEntry(items[0]);
        }
      } catch (err: any) {
        if (!cancelled) {
          setIndexError(err?.message ?? String(err));
        }
      } finally {
        if (!cancelled) {
          setLoadingIndex(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // When activeEntry changes, load that crystal’s holo
  useEffect(() => {
    if (!activeEntry) return;

    let cancelled = false;
    setLoadingHolo(true);
    setHoloError(null);

    (async () => {
      try {
        const res = await fetch(
          `/api/crystals/motifs/${encodeURIComponent(
            activeEntry.motif_id,
          )}?scope=${encodeURIComponent(CRYSTAL_SCOPE)}`,
        );
        if (!res.ok) {
          if (res.status === 404) {
            throw new Error("Crystal not found");
          }
          throw new Error(`HTTP ${res.status}`);
        }
        const json = await res.json();
        const holoObj = (json.holo ?? json) as HoloIR;
        if (!cancelled) {
          setHolo(holoObj);
          setFocusMode("world"); // reset focus when you switch crystals
        }
      } catch (err: any) {
        if (!cancelled) {
          setHoloError(err?.message ?? String(err));
          setHolo(null);
        }
      } finally {
        if (!cancelled) {
          setLoadingHolo(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [activeEntry]);

  const filtered = index.filter((item) => {
    if (!filter.trim()) return true;
    const f = filter.toLowerCase();
    const motifLabel = motifLabelFromPath(item.path);
    const haystack = [
      item.motif_id,
      motifLabel,
      ...(item.tags ?? []),
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(f);
  });

  const crystalMeta = extractCrystalMeta(holo);
  const activeMotifLabel =
    activeEntry && motifLabelFromPath(activeEntry.path || undefined);

  // GHX + Photon derived from the active crystal holo
  const ghxPacket: GhxPacket | null = holo ? buildGhxFromHolo(holo) : null;
  const photonStub = holo ? buildPhotonStubFromHolo(holo) : null;

  const nodeCount = ghxPacket?.nodes?.length ?? 0;
  const edgeCount = ghxPacket?.edges?.length ?? 0;
  const origin = ghxPacket?.origin ?? "—";

  return (
    <div
      style={{
        display: "flex",
        gap: 12,
        height: "100%",
        minHeight: 320,
      }}
    >
      {/* Left: crystal hologram (3D) + metadata + Photon stub */}
      <div
        style={{
          flex: 1.4,
          borderRadius: 12,
          border: "1px solid #020617",
          background: "#020617",
          padding: 8,
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
          gap: 6,
        }}
      >
        <div
          style={{
            fontSize: 11,
            color: "#e5e7eb",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <span style={{ fontWeight: 600 }}>Crystal Hologram</span>
            {activeEntry && (
              <span style={{ opacity: 0.75, marginLeft: 8 }}>
                <code style={{ fontSize: 10 }}>
                  {activeMotifLabel || activeEntry.motif_id}
                </code>
                {typeof activeEntry.tick === "number" &&
                  typeof activeEntry.revision === "number" && (
                    <span style={{ marginLeft: 6, fontSize: 10 }}>
                      t={activeEntry.tick} / v={activeEntry.revision}
                    </span>
                  )}
              </span>
            )}
          </div>

          <button
            type="button"
            onClick={handleRehydrateToField}
            disabled={!holo}
            style={{
              fontSize: 10,
              padding: "3px 8px",
              borderRadius: 999,
              border: "1px solid #22c55e",
              background: holo ? "#16a34a" : "#374151",
              color: "#ecfdf5",
              cursor: holo ? "pointer" : "default",
              opacity: holo ? 1 : 0.5,
              whiteSpace: "nowrap",
            }}
          >
            ↻ Rehydrate to Field
          </button>
        </div>

        <div style={{ flex: 1, minHeight: 260 }}>
          {loadingHolo ? (
            <div
              style={{
                fontSize: 11,
                color: "#9ca3af",
                padding: 8,
              }}
            >
              Loading crystal hologram…
            </div>
          ) : holoError ? (
            <div
              style={{
                fontSize: 11,
                color: "#f97316",
                padding: 8,
              }}
            >
              Failed to load crystal hologram: {holoError}
            </div>
          ) : ghxPacket ? (
            <DevFieldHologram3DScene
              packet={ghxPacket}
              mode="crystal"
              focusMode={focusMode}
              onToggleFocus={toggleFocus}
            />
          ) : (
            <div
              style={{
                fontSize: 11,
                color: "#9ca3af",
                padding: 8,
              }}
            >
              No crystal selected yet.
            </div>
          )}
        </div>

        {crystalMeta && (
          <div
            style={{
              marginTop: 6,
              borderRadius: 8,
              border: "1px solid #1f2937",
              background: "#020617",
              padding: 8,
              fontSize: 11,
              color: "#e5e7eb",
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              Motif metadata
            </div>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 8,
                fontSize: 10,
                color: "#9ca3af",
              }}
            >
              {crystalMeta.motifId && <span>id={crystalMeta.motifId}</span>}
              {typeof crystalMeta.patternStrength === "number" && (
                <span>
                  pattern_strength={crystalMeta.patternStrength.toFixed(3)}
                </span>
              )}
              {typeof crystalMeta.sqi === "number" && (
                <span>SQI={crystalMeta.sqi.toFixed(3)}</span>
              )}
              {typeof crystalMeta.usageCount === "number" && (
                <span>usage={crystalMeta.usageCount}</span>
              )}
            </div>
          </div>
        )}

        {photonStub && (
          <div
            style={{
              marginTop: 6,
              maxHeight: 260,
              overflow: "auto",
            }}
          >
            <PhotonStubPanel code={photonStub} />
          </div>
        )}
      </div>

      {/* Right: crystal list + GHX inspector */}
      <div
        style={{
          width: 360,
          maxWidth: 360,
          borderRadius: 12,
          border: "1px solid #e5e7eb",
          background: "#f9fafb",
          padding: 8,
          fontSize: 11,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          minWidth: 0,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 8,
            alignItems: "baseline",
          }}
        >
          <div>
            <div style={{ fontWeight: 600 }}>Crystals (motifs)</div>
            <div style={{ fontSize: 10, color: "#6b7280" }}>
              {index.length} total
            </div>
          </div>

          <input
            type="text"
            placeholder="Filter motifs…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{
              borderRadius: 999,
              border: "1px solid #d1d5db",
              padding: "4px 8px",
              fontSize: 10,
              outline: "none",
              background: "#ffffff",
              minWidth: 120,
            }}
          />
        </div>

        {loadingIndex && (
          <div style={{ fontSize: 11, color: "#6b7280" }}>
            Loading crystals…
          </div>
        )}

        {indexError && (
          <div style={{ fontSize: 11, color: "#f97316" }}>
            Failed to load crystal index: {indexError}
          </div>
        )}

        {!loadingIndex && !indexError && (
          <>
            <div style={{ fontSize: 10, color: "#9ca3af" }}>
              Click a crystal to load its hologram.
            </div>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 6,
                maxHeight: 220,
                overflow: "auto",
              }}
            >
              {filtered.length === 0 && (
                <div style={{ fontSize: 11, color: "#9ca3af" }}>
                  No crystals match this filter.
                </div>
              )}

              {filtered.map((item) => {
                const isActive =
                  activeEntry && item.motif_id === activeEntry.motif_id;
                const motifLabel = motifLabelFromPath(item.path);

                return (
                  <button
                    key={item.motif_id}
                    type="button"
                    onClick={() => setActiveEntry(item)}
                    style={{
                      borderRadius: 6,
                      border: isActive
                        ? "1px solid #0ea5e9"
                        : "1px solid #e5e7eb",
                      padding: 6,
                      display: "flex",
                      flexDirection: "column",
                      gap: 3,
                      cursor: "pointer",
                      textAlign: "left",
                      background: isActive ? "#e0f2fe" : "#ffffff",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 8,
                        alignItems: "baseline",
                      }}
                    >
                      <div style={{ overflow: "hidden" }}>
                        <div
                          style={{
                            fontWeight: 600,
                            fontSize: 11,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                          title={motifLabel || item.motif_id}
                        >
                          {motifLabel || item.motif_id}
                        </div>
                        <div
                          style={{
                            fontSize: 10,
                            color: "#9ca3af",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                          title={item.path}
                        >
                          {item.path}
                        </div>
                      </div>

                      <div
                        style={{
                          fontSize: 10,
                          color: "#9ca3af",
                          whiteSpace: "nowrap",
                          textAlign: "right",
                        }}
                      >
                        {item.tick != null && item.revision != null && (
                          <span>t={item.tick}/v={item.revision}</span>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </>
        )}

        {/* Holo GHX inspector (right column) */}
        {ghxPacket && (
          <div
            style={{
              marginTop: 8,
              borderRadius: 10,
              border: "1px solid #e5e7eb",
              background: "#ffffff",
              padding: 8,
              display: "flex",
              flexDirection: "column",
              gap: 6,
            }}
          >
            <div>
              <div
                style={{
                  fontWeight: 600,
                  fontSize: 12,
                  marginBottom: 2,
                }}
              >
                Holo GHX view
              </div>
              <div style={{ fontSize: 11, color: "#6b7280" }}>
                origin:{" "}
                <span style={{ fontFamily: "monospace" }}>{origin}</span>
                <br />
                nodes: {nodeCount} • edges: {edgeCount}
              </div>
            </div>

            <div style={{ borderRadius: 8, overflow: "hidden" }}>
              <GHXVisualizerField packet={ghxPacket} layout="crystal" />
            </div>

            <div
              style={{
                borderRadius: 6,
                border: "1px solid #e5e7eb",
                background: "#f9fafb",
                padding: 6,
                maxHeight: 140,
                overflow: "auto",
                fontFamily:
                  'SFMono-Regular, ui-monospace, Menlo, Monaco, Consolas, "Courier New", monospace',
                fontSize: 10,
                whiteSpace: "pre",
              }}
            >
              {JSON.stringify(ghxPacket, null, 2)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}