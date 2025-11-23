// src/components/KGDock.tsx
import React, { useEffect, useState } from "react";
import type { KgId, KgStats, EntanglementView } from "../lib/kg";
import { fetchKgStats, fetchEntanglements, forgetVisits } from "../lib/kg";

// Derive container id from URL: #/container/<id>
function getContainerIdFromLocation(): string {
  if (typeof window === "undefined") return "";
  const hash = window.location.hash || "";
  const m = hash.match(/\/container\/([^/?#]+)/);
  return m?.[1] ?? "";
}

function inferKgFromContainer(containerId: string): KgId {
  if (containerId.includes("_work")) return "work";
  return "personal";
}

type TabId = "stats" | "entanglements" | "forget";

export default function KGDock() {
  const containerId = getContainerIdFromLocation();
  const kg: KgId = inferKgFromContainer(containerId);

  const [tab, setTab] = useState<TabId>("stats");
  const [stats, setStats] = useState<KgStats | null>(null);
  const [ent, setEnt] = useState<EntanglementView | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [loadingEnt, setLoadingEnt] = useState(false);

  // Forget UI state
  const [host, setHost] = useState("");
  const [topicWa, setTopicWa] = useState("");
  const [daysBack, setDaysBack] = useState("7");
  const [forgetResult, setForgetResult] = useState<string | null>(null);
  const [forgetError, setForgetError] = useState<string | null>(null);
  const [forgetBusy, setForgetBusy] = useState(false);

  // Load stats when kg changes
  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        setLoadingStats(true);
        const s = await fetchKgStats("", kg);
        if (!cancelled) setStats(s);
      } catch (e: any) {
        console.warn("[KGDock] stats error", e);
        if (!cancelled) setStats(null);
      } finally {
        if (!cancelled) setLoadingStats(false);
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [kg]);

  // Load entanglements when kg/container changes
  useEffect(() => {
    if (!containerId) {
      setEnt(null);
      return;
    }
    let cancelled = false;
    async function run() {
      try {
        setLoadingEnt(true);
        const v = await fetchEntanglements(kg, containerId, "");
        if (!cancelled) setEnt(v);
      } catch (e: any) {
        console.warn("[KGDock] entanglements error", e);
        if (!cancelled) setEnt(null);
      } finally {
        if (!cancelled) setLoadingEnt(false);
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [kg, containerId]);

  async function onSubmitForget(e: React.FormEvent) {
    e.preventDefault();
    setForgetError(null);
    setForgetResult(null);

    const trimmedHost = host.trim();
    const trimmedTopic = topicWa.trim();
    const nDays = parseInt(daysBack, 10);

    const payload: any = { kg };

    if (trimmedHost) payload.host = trimmedHost;
    if (trimmedTopic) payload.topic_wa = trimmedTopic;

    if (Number.isFinite(nDays) && nDays > 0) {
      const now = Date.now();
      payload.from_ms = now - nDays * 24 * 60 * 60 * 1000;
    }

    // Server will reject if we only pass kg (too broad), so guard here too.
    if (!payload.host && !payload.topic_wa && !payload.from_ms && !payload.to_ms) {
      setForgetError(
        "Please specify at least a host, topic, or time window so the forget request is not too broad."
      );
      return;
    }

    setForgetBusy(true);
    try {
      const res = await forgetVisits("", payload);
      setForgetResult(`Deleted ${res.deleted} visit event(s) in ${kg} KG.`);
    } catch (err: any) {
      const msg = String(err?.message ?? err);
      if (msg.includes("400")) {
        setForgetError(
          "Server rejected this forget request as too broad. Add a host, topic, or time window."
        );
      } else {
        setForgetError(msg);
      }
    } finally {
      setForgetBusy(false);
    }
  }

  const sampleNodes = [
    { id: "n1", label: "Identity: kevin.tp" },
    { id: "n2", label: "Bond: partner.home" },
    { id: "n3", label: "Topic: glyphnet" },
  ];

  return (
    <div style={{ padding: 12 }}>
      <h3 style={{ marginBottom: 8 }}>Knowledge Graph</h3>
      <div style={{ fontSize: 12, marginBottom: 8, color: "#4b5563" }}>
        graph: <strong>{kg}</strong>{" "}
        {containerId && (
          <>
            • container: <code>{containerId}</code>
          </>
        )}
      </div>

      {/* Tab selector */}
      <div style={{ display: "flex", gap: 4, marginBottom: 10 }}>
        <button
          type="button"
          onClick={() => setTab("stats")}
          style={{
            padding: "4px 8px",
            borderRadius: 999,
            border: "1px solid #e5e7eb",
            background: tab === "stats" ? "#111827" : "#ffffff",
            color: tab === "stats" ? "#f9fafb" : "#111827",
            fontSize: 12,
          }}
        >
          Stats
        </button>
        <button
          type="button"
          onClick={() => setTab("entanglements")}
          style={{
            padding: "4px 8px",
            borderRadius: 999,
            border: "1px solid #e5e7eb",
            background: tab === "entanglements" ? "#111827" : "#ffffff",
            color: tab === "entanglements" ? "#f9fafb" : "#111827",
            fontSize: 12,
          }}
        >
          Entanglements
        </button>
        <button
          type="button"
          onClick={() => setTab("forget")}
          style={{
            padding: "4px 8px",
            borderRadius: 999,
            border: "1px solid #e5e7eb",
            background: tab === "forget" ? "#b91c1c" : "#ffffff",
            color: tab === "forget" ? "#fef2f2" : "#991b1b",
            fontSize: 12,
          }}
        >
          Forget visits
        </button>
      </div>

      {/* Main panel */}
      <div
        style={{
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          padding: 10,
          fontSize: 13,
        }}
      >
        {tab === "stats" && (
          <div>
            {loadingStats && <div>Loading stats…</div>}
            {!loadingStats && stats && (
              <>
                <div style={{ marginBottom: 8, fontWeight: 600 }}>Totals</div>
                <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
                  <div>
                    <div style={{ fontSize: 11, color: "#6b7280" }}>
                      Events
                    </div>
                    <div style={{ fontWeight: 600 }}>{stats.events_total}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: "#6b7280" }}>
                      Visits
                    </div>
                    <div style={{ fontWeight: 600 }}>{stats.visits_total}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: "#6b7280" }}>
                      Files
                    </div>
                    <div style={{ fontWeight: 600 }}>{stats.files_total}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: "#6b7280" }}>
                      Attachments
                    </div>
                    <div style={{ fontWeight: 600 }}>
                      {stats.attachments_total}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: "#6b7280" }}>
                      Container refs
                    </div>
                    <div style={{ fontWeight: 600 }}>
                      {stats.container_refs_total}
                    </div>
                  </div>
                </div>

                <hr style={{ margin: "10px 0" }} />

                <div style={{ fontSize: 12, marginBottom: 4 }}>
                  Sample nodes
                </div>
                <div style={{ display: "grid", gap: 6 }}>
                  {sampleNodes.map((n) => (
                    <div
                      key={n.id}
                      style={{
                        padding: "6px 8px",
                        borderRadius: 6,
                        border: "1px solid #e5e7eb",
                      }}
                    >
                      {n.label}
                    </div>
                  ))}
                </div>
              </>
            )}
            {!loadingStats && !stats && (
              <div style={{ color: "#9ca3af" }}>
                Stats not available (no KG activity yet?).
              </div>
            )}
          </div>
        )}

        {tab === "entanglements" && (
          <div>
            {loadingEnt && <div>Loading entanglements…</div>}
            {!loadingEnt && ent && ent.entangled_with.length === 0 && (
              <div style={{ color: "#9ca3af" }}>
                This container is not entangled with any others yet.
              </div>
            )}
            {!loadingEnt && ent && ent.entangled_with.length > 0 && (
              <div style={{ display: "grid", gap: 6 }}>
                {ent.entangled_with.map((cid) => (
                  <div
                    key={cid}
                    style={{
                      padding: "6px 8px",
                      borderRadius: 6,
                      border: "1px solid #e5e7eb",
                      fontFamily: "monospace",
                      fontSize: 12,
                    }}
                  >
                    {cid}
                  </div>
                ))}
              </div>
            )}
            {!loadingEnt && !ent && (
              <div style={{ color: "#9ca3af" }}>
                No entanglement info for this container.
              </div>
            )}
          </div>
        )}

        {tab === "forget" && (
          <form onSubmit={onSubmitForget} style={{ display: "grid", gap: 8 }}>
            <div style={{ fontSize: 12, color: "#6b7280" }}>
              Forget <strong>visit</strong> events in the <strong>{kg}</strong>{" "}
              KG. You must provide at least a host, topic, or time window.
            </div>

            <label style={{ display: "grid", gap: 2, fontSize: 12 }}>
              Host (optional)
              <input
                type="text"
                placeholder="example.com"
                value={host}
                onChange={(e) => setHost(e.target.value)}
                style={{
                  borderRadius: 6,
                  border: "1px solid #e5e7eb",
                  padding: "4px 6px",
                  fontSize: 13,
                }}
              />
            </label>

            <label style={{ display: "grid", gap: 2, fontSize: 12 }}>
              Topic WA (optional)
              <input
                type="text"
                placeholder="ucs://local/dc_kg_personal"
                value={topicWa}
                onChange={(e) => setTopicWa(e.target.value)}
                style={{
                  borderRadius: 6,
                  border: "1px solid #e5e7eb",
                  padding: "4px 6px",
                  fontSize: 13,
                }}
              />
            </label>

            <label style={{ display: "grid", gap: 2, fontSize: 12 }}>
              Only last N days (optional)
              <input
                type="number"
                min={1}
                placeholder="e.g. 7"
                value={daysBack}
                onChange={(e) => setDaysBack(e.target.value)}
                style={{
                  borderRadius: 6,
                  border: "1px solid #e5e7eb",
                  padding: "4px 6px",
                  fontSize: 13,
                  maxWidth: 100,
                }}
              />
            </label>

            {forgetError && (
              <div style={{ fontSize: 12, color: "#b91c1c" }}>{forgetError}</div>
            )}
            {forgetResult && (
              <div style={{ fontSize: 12, color: "#065f46" }}>
                {forgetResult}
              </div>
            )}

            <div>
              <button
                type="submit"
                disabled={forgetBusy}
                style={{
                  padding: "6px 10px",
                  borderRadius: 999,
                  border: "1px solid #b91c1c",
                  background: forgetBusy ? "#fee2e2" : "#ef4444",
                  color: "#fef2f2",
                  fontSize: 12,
                  cursor: forgetBusy ? "default" : "pointer",
                }}
              >
                {forgetBusy ? "Forgetting…" : "Forget visits"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}