// Glyph_Net_Browser/src/components/AionMemoryPanel.tsx

import React, { useEffect, useState } from "react";
import { DevFieldHologram3DScene } from "./DevFieldHologram3D";
import { AionHoloIndexPanel } from "./AionHoloIndexPanel";

type GhxNode = { id: string; data: any };
type GhxEdge = { id: string; source: string; target: string; kind?: string };

type GhxPacket = {
  ghx_version: string;
  origin: string;
  container_id: string;
  nodes: GhxNode[];
  edges: GhxEdge[];
  metadata?: Record<string, any>;
};

type AionHoloSnapshot = {
  holo_id: string;
  container_id: string;
  tick: number;
  revision: number;
  created_at?: string;
  ghx_mode?: string;
  ghx: GhxPacket;
  metadata?: Record<string, any>;
};

type SeedMetrics = { [key: string]: number | undefined };

type AionMemorySeedPayload = {
  label?: string;
  timestamp?: string;
  content?: string;
  source?: string;
  metrics?: SeedMetrics;
  keywords?: string[];
  [key: string]: any;
};

type AionMemorySeed = {
  seed_id: string;
  container_id: string;
  kind: string;
  label: string;
  created_at: string;
  tags: string[];
  payload: AionMemorySeedPayload;
};

type AionRulebookSeedPayload = {
  name?: string;
  description?: string;
  domains?: string[];
  metrics?: SeedMetrics;
  [key: string]: any;
};

type AionRulebookSeed = {
  seed_id: string;
  container_id: string;
  rulebook_id: string;
  created_at: string;
  updated_at: string;
  usage_count: number;
  tags: string[];
  payload: AionRulebookSeedPayload;
};

type CombinedSeedsResponse = {
  memory: AionMemorySeed[];
  rulebooks: AionRulebookSeed[];
};

export default function AionMemoryPanel() {
  const [seeds, setSeeds] = useState<CombinedSeedsResponse | null>(null);
  const [loadingSeeds, setLoadingSeeds] = useState(false);
  const [seedError, setSeedError] = useState<string | null>(null);

  const [holo, setHolo] = useState<AionHoloSnapshot | null>(null);
  const [loadingHolo, setLoadingHolo] = useState(false);
  const [holoError, setHoloError] = useState<string | null>(null);

  // which holo is “active” in the right-hand index
  const [activeHoloId, setActiveHoloId] = useState<string | null>(null);

  const [filterQuery, setFilterQuery] = useState("");

  // ──────────────────────────────────────────────
  //  Fetch seeds
  // ──────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false;
    setLoadingSeeds(true);
    setSeedError(null);

    (async () => {
      try {
        const seedsResp = await fetch(
          "/api/holo/aion/seeds/combined?limit_memory=64",
        );
        if (!seedsResp.ok) {
          throw new Error(`HTTP ${seedsResp.status}`);
        }
        const data = (await seedsResp.json()) as CombinedSeedsResponse;
        if (!cancelled) {
          setSeeds(data);
        }
      } catch (err) {
        if (!cancelled) {
          setSeedError(String(err));
        }
      } finally {
        if (!cancelled) {
          setLoadingSeeds(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // ──────────────────────────────────────────────
  //  Fetch live hologram snapshot (initial + refresh)
  // ──────────────────────────────────────────────

  async function fetchLiveSnapshot() {
    setLoadingHolo(true);
    setHoloError(null);

    try {
      const holoResp = await fetch(
        "/api/holo/aion/snapshot?limit_memory=64",
      );
      if (!holoResp.ok) {
        throw new Error(`HTTP ${holoResp.status}`);
      }
      const json = await holoResp.json();
      const next = json.holo as AionHoloSnapshot;
      setHolo(next);
      setActiveHoloId(next.holo_id ?? null);
    } catch (err: any) {
      setHoloError(String(err));
    } finally {
      setLoadingHolo(false);
    }
  }

  // initial load
  useEffect(() => {
    fetchLiveSnapshot();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // load a specific snapshot by id (from right-hand index)
  async function handleSelectSnapshot(holoId: string | null) {
    if (!holoId) return;

    setLoadingHolo(true);
    setHoloError(null);

    try {
      const res = await fetch(
        `/api/holo/aion/snapshot/by-id?holo_id=${encodeURIComponent(holoId)}`,
      );
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const json = await res.json();
      const next = json.holo as AionHoloSnapshot;
      setHolo(next);
      setActiveHoloId(next.holo_id ?? holoId);
    } catch (err: any) {
      setHoloError(String(err));
    } finally {
      setLoadingHolo(false);
    }
  }

  // ──────────────────────────────────────────────
  //  Search / filter helper
  // ──────────────────────────────────────────────

  const matchesSearch = (
    seed: AionMemorySeed | AionRulebookSeed,
    q: string,
  ): boolean => {
    const query = q.trim().toLowerCase();
    if (!query) return true;

    const parts: string[] = [];

    // label
    parts.push((seed as any).label || "");

    // tags
    if (Array.isArray((seed as any).tags)) {
      parts.push((seed as any).tags.join(" "));
    }

    const payload: any = (seed as any).payload ?? {};

    if (typeof payload.label === "string") parts.push(payload.label);
    if (typeof payload.content === "string") parts.push(payload.content);

    if (Array.isArray(payload.keywords)) {
      parts.push(payload.keywords.join(" "));
    }

    const metrics: SeedMetrics = payload.metrics ?? {};
    for (const [k, v] of Object.entries(metrics)) {
      parts.push(k);
      if (typeof v === "number") parts.push(String(v));
    }

    const haystack = parts.join(" ").toLowerCase();
    return haystack.includes(query);
  };

  const memory = seeds?.memory ?? [];
  const rulebooks = seeds?.rulebooks ?? [];

  const filteredMemory = memory.filter((s) => matchesSearch(s, filterQuery));
  const filteredRulebooks = rulebooks.filter((s) =>
    matchesSearch(s, filterQuery),
  );

  const tickLabel =
    holo && typeof holo.tick === "number" ? holo.tick : undefined;
  const revLabel =
    holo && typeof holo.revision === "number" ? holo.revision : undefined;

  return (
    <div
      style={{
        display: "flex",
        height: "100%",
        gap: 12,
        minHeight: 320,
      }}
    >
      {/* Left: 3D hologram */}
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
          <span style={{ fontWeight: 600 }}>AION Memory Constellation</span>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            {holo && (
              <span style={{ opacity: 0.8, display: "flex", gap: 6 }}>
                <code style={{ fontSize: 10 }}>{holo.holo_id}</code>
                <span
                  style={{
                    fontSize: 10,
                    color: "#9ca3af",
                    whiteSpace: "nowrap",
                  }}
                >
                  t={tickLabel ?? "?"} · v={revLabel ?? "?"}
                </span>
              </span>
            )}

            <button
              type="button"
              onClick={() => fetchLiveSnapshot()}
              disabled={loadingHolo}
              style={{
                padding: "3px 8px",
                borderRadius: 999,
                border: "1px solid #e5e7eb",
                background: loadingHolo ? "#111827" : "#020617",
                color: "#e5e7eb",
                cursor: loadingHolo ? "default" : "pointer",
                fontSize: 10,
              }}
            >
              {loadingHolo ? "Refreshing…" : "Refresh"}
            </button>
          </div>
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
              Building live hologram…
            </div>
          ) : holoError ? (
            <div
              style={{
                fontSize: 11,
                color: "#f97316",
                padding: 8,
              }}
            >
              Failed to load AION hologram: {holoError}
            </div>
          ) : holo && holo.ghx ? (
            <DevFieldHologram3DScene
              packet={holo.ghx as any}
              focusMode="focus"
              onToggleFocus={() => {
                /* no-op for now */
              }}
            />
          ) : (
            <div
              style={{
                fontSize: 11,
                color: "#9ca3af",
                padding: 8,
              }}
            >
              No hologram available yet.
            </div>
          )}
        </div>
      </div>

      {/* Right: seed inspector + holo index */}
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
            <div style={{ fontWeight: 600 }}>Holo Seeds</div>
            <div style={{ fontSize: 10, color: "#6b7280" }}>
              memory: {memory.length} · rulebooks: {rulebooks.length}
            </div>
          </div>

          <input
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            placeholder="Filter seeds…"
            style={{
              flexShrink: 0,
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

        {loadingSeeds && (
          <div style={{ fontSize: 11, color: "#6b7280" }}>Loading seeds…</div>
        )}
        {seedError && (
          <div style={{ fontSize: 11, color: "#f97316" }}>
            Failed to load seeds: {seedError}
          </div>
        )}

        {!loadingSeeds && !seedError && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 8,
              overflow: "auto",
              maxHeight: 320,
            }}
          >
            {/* Memory seeds */}
            {filteredMemory.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <div
                  style={{
                    fontSize: 10,
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: 0.04,
                    color: "#6b7280",
                  }}
                >
                  Memory entries ({filteredMemory.length})
                </div>

                {filteredMemory.map((seed: AionMemorySeed) => {
                  const payload = (seed.payload ?? {}) as AionMemorySeedPayload;

                  const content =
                    typeof payload.content === "string" ? payload.content : "";
                  const source =
                    typeof payload.source === "string"
                      ? payload.source
                      : "MemoryEngine";

                  const metrics = (payload.metrics ?? {}) as SeedMetrics;

                  return (
                    <div
                      key={seed.seed_id}
                      style={{
                        borderRadius: 8,
                        border: "1px solid #e5e7eb",
                        padding: 8,
                        fontSize: 11,
                        display: "flex",
                        flexDirection: "column",
                        gap: 4,
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: 8,
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
                            title={seed.label}
                          >
                            {seed.label}
                          </div>
                          <div
                            style={{
                              fontSize: 10,
                              color: "#9ca3af",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                            title={source}
                          >
                            {source}
                          </div>
                        </div>
                        <div
                          style={{
                            fontSize: 10,
                            color: "#9ca3af",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {new Date(seed.created_at).toLocaleString()}
                        </div>
                      </div>

                      {content && (
                        <div
                          style={{
                            fontSize: 10,
                            color: "#4b5563",
                            whiteSpace: "pre-line",
                          }}
                        >
                          {content.slice(0, 200)}
                          {content.length > 200 && "…"}
                        </div>
                      )}

                      {Object.keys(metrics).length > 0 && (
                        <div
                          style={{
                            display: "flex",
                            gap: 8,
                            fontSize: 10,
                            color: "#6b7280",
                            marginTop: 2,
                            flexWrap: "wrap",
                          }}
                        >
                          {typeof metrics["SQI"] === "number" && (
                            <span>SQI={metrics["SQI"]}</span>
                          )}
                          {typeof metrics["rho"] === "number" && (
                            <span>ρ={metrics["rho"]}</span>
                          )}
                          {typeof metrics["I_bar"] === "number" && (
                            <span>Ī={metrics["I_bar"]}</span>
                          )}
                          {typeof metrics["E"] === "number" && (
                            <span>E={metrics["E"]}</span>
                          )}
                        </div>
                      )}

                      {seed.tags && seed.tags.length > 0 && (
                        <div
                          style={{
                            display: "flex",
                            flexWrap: "wrap",
                            gap: 4,
                            marginTop: 2,
                          }}
                        >
                          {seed.tags.map((t) => (
                            <span
                              key={t}
                              style={{
                                borderRadius: 999,
                                border: "1px solid #e5e7eb",
                                padding: "1px 6px",
                                fontSize: 9,
                                color: "#4b5563",
                                background: "#f9fafb",
                              }}
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Rulebook seeds */}
            {filteredRulebooks.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <div
                  style={{
                    fontSize: 10,
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: 0.04,
                    color: "#6b7280",
                  }}
                >
                  Rulebooks ({filteredRulebooks.length})
                </div>

                {filteredRulebooks.map((seed: AionRulebookSeed) => {
                  const meta = (seed.payload ?? {}) as AionRulebookSeedPayload;
                  const metrics = (meta.metrics ?? {}) as SeedMetrics;
                  const domains = (meta.domains ?? []) as string[];

                  return (
                    <div
                      key={seed.seed_id}
                      style={{
                        borderRadius: 8,
                        border: "1px solid #e5e7eb",
                        padding: 8,
                        fontSize: 11,
                        display: "flex",
                        flexDirection: "column",
                        gap: 3,
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
                            title={meta.name || seed.rulebook_id}
                          >
                            {meta.name || seed.rulebook_id}
                          </div>
                          <div
                            style={{
                              fontSize: 10,
                              color: "#9ca3af",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                            title={seed.rulebook_id}
                          >
                            {seed.rulebook_id}
                          </div>
                        </div>

                        <div
                          style={{
                            fontSize: 10,
                            color: "#9ca3af",
                            textAlign: "right",
                            whiteSpace: "nowrap",
                          }}
                        >
                          used {seed.usage_count}×
                        </div>
                      </div>

                      {domains.length > 0 && (
                        <div
                          style={{
                            display: "flex",
                            flexWrap: "wrap",
                            gap: 4,
                            marginTop: 2,
                          }}
                        >
                          {domains.map((d) => (
                            <span
                              key={d}
                              style={{
                                borderRadius: 999,
                                border: "1px solid #e5e7eb",
                                padding: "1px 6px",
                                fontSize: 10,
                                color: "#4b5563",
                                background: "#f9fafb",
                              }}
                            >
                              {d}
                            </span>
                          ))}
                        </div>
                      )}

                      {Object.keys(metrics).length > 0 && (
                        <div
                          style={{
                            display: "flex",
                            gap: 8,
                            fontSize: 10,
                            color: "#6b7280",
                            marginTop: 2,
                            flexWrap: "wrap",
                          }}
                        >
                          {typeof metrics["Φ_coherence"] === "number" && (
                            <span>ρ={metrics["Φ_coherence"]}</span>
                          )}
                          {typeof metrics["Φ_entropy"] === "number" && (
                            <span>Ī={metrics["Φ_entropy"]}</span>
                          )}
                          {typeof metrics["SQI"] === "number" && (
                            <span>SQI={metrics["SQI"]}</span>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {filteredMemory.length === 0 && filteredRulebooks.length === 0 && (
              <div
                style={{
                  fontSize: 11,
                  color: "#9ca3af",
                  paddingTop: 4,
                }}
              >
                No seeds match this filter.
              </div>
            )}
          </div>
        )}

        <div style={{ marginTop: 8 }}>
          <AionHoloIndexPanel
            activeHoloId={activeHoloId}
            onSelectSnapshot={(id) => handleSelectSnapshot(id)}
          />
        </div>
      </div>
    </div>
  );
}