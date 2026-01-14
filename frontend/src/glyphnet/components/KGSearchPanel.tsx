// src/components/KGSearchPanel.tsx

import React, { useState } from "react";

type Scope = "message" | "visit" | "file";

type KGSearchPanelProps = {
  kg: string;          // "personal" | "work"
  topicWa?: string;    // current conversation (for optional local filtering)
};

type SearchResponse = {
  ok: boolean;
  kg: string;
  q: string;
  messages: Array<{
    id: string;
    thread_id: string | null;
    topic_wa: string | null;
    ts: number;
    text: string | null;
    from?: string | null;
    to?: string | null;
  }>;
  visits: Array<{
    id: string;
    thread_id: string | null;
    topic_wa: string | null;
    ts: number;
    uri: string | null;
    host: string | null;
    title: string | null;
    referrer: string | null;
  }>;
  files: Array<{
    file_id: string;
    name: string | null;
    mime: string | null;
    size: number | null;
    sha256: string | null;
    created_ts: number;
    event_id: string | null;
    thread_id: string | null;
    topic_wa: string | null;
  }>;
};

const scopeLabel: Record<Scope, string> = {
  message: "Messages",
  visit: "Visits",
  file: "Files",
};

export default function KGSearchPanel({ kg, topicWa }: KGSearchPanelProps) {
  const [query, setQuery] = useState("");
  const [scopes, setScopes] = useState<Scope[]>(["message", "visit", "file"]);
  const [localOnly, setLocalOnly] = useState(true); // filter to this thread/topic
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SearchResponse | null>(null);

  const toggleScope = (s: Scope) => {
    setScopes((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    );
  };

  const doSearch = async () => {
    const q = query.trim();
    if (!q) return;

    setLoading(true);
    setError(null);

    try {
      const scopeParam =
        scopes.length === 0 ? "message,visit,file" : scopes.join(",");

      const params = new URLSearchParams({
        kg,
        q,
        scope: scopeParam,
      });

      const res = await fetch(`/api/kg/search?${params.toString()}`);
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`HTTP ${res.status} ${txt}`);
      }
      const json = (await res.json()) as SearchResponse;
      setResult(json);
    } catch (e: any) {
      console.warn("[KGSearchPanel] search error", e);
      setError(e?.message || "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      void doSearch();
    }
  };

  // Optional local filtering by topic/thread
  const matchesLocal = (topic_wa: string | null, thread_id: string | null) => {
    if (!localOnly) return true;
    if (!topicWa) return true;
    const t = (topic_wa || "").toLowerCase();
    const thr = (thread_id || "").toLowerCase();
    const topicNorm = topicWa.toLowerCase();
    return t === topicNorm || thr.endsWith(topicNorm);
  };

  return (
    <div
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: 12,
        padding: 10,
        marginTop: 12,
        background: "#f9fafb",
        fontSize: 12,
      }}
    >
      <div
        style={{
          fontSize: 12,
          fontWeight: 600,
          color: "#0f172a",
          marginBottom: 6,
        }}
      >
        KG Search
      </div>

      <div style={{ display: "flex", gap: 6, marginBottom: 6 }}>
        <input
          type="text"
          placeholder="Search messages, visits, files…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onKeyDown}
          style={{
            flex: 1,
            fontSize: 12,
            padding: "4px 6px",
            borderRadius: 8,
            border: "1px solid #d1d5db",
          }}
        />
        <button
          onClick={doSearch}
          disabled={loading || !query.trim()}
          style={{
            fontSize: 12,
            padding: "4px 10px",
            borderRadius: 999,
            border: "1px solid #0f766e",
            background: loading ? "#a7f3d0" : "#14b8a6",
            color: "#022c22",
            cursor: loading ? "default" : "pointer",
            whiteSpace: "nowrap",
          }}
        >
          {loading ? "Searching…" : "Search"}
        </button>
      </div>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 6,
          marginBottom: 6,
        }}
      >
        {(["message", "visit", "file"] as Scope[]).map((s) => {
          const active = scopes.includes(s);
          return (
            <button
              key={s}
              type="button"
              onClick={() => toggleScope(s)}
              style={{
                fontSize: 11,
                padding: "2px 8px",
                borderRadius: 999,
                border: "1px solid #cbd5f5",
                background: active ? "#e0f2fe" : "#ffffff",
                color: active ? "#1d4ed8" : "#64748b",
                cursor: "pointer",
              }}
            >
              {scopeLabel[s]}
            </button>
          );
        })}

        <label
          style={{
            marginLeft: "auto",
            display: "flex",
            alignItems: "center",
            gap: 4,
            fontSize: 11,
            color: "#64748b",
            cursor: "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={localOnly}
            onChange={(e) => setLocalOnly(e.target.checked)}
            style={{ cursor: "pointer" }}
          />
          This thread only
        </label>
      </div>

      {error && (
        <div
          style={{
            fontSize: 11,
            color: "#b91c1c",
            marginBottom: 4,
          }}
        >
          {error}
        </div>
      )}

      {!result && !loading && (
        <div style={{ fontSize: 11, color: "#9ca3af" }}>
          Type a query and press Enter.
        </div>
      )}

      {result && (
        <div
          style={{
            maxHeight: 260,
            overflowY: "auto",
            paddingRight: 4,
          }}
        >
          {/* Messages */}
          {scopes.includes("message") && result.messages.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: "#0f172a",
                  marginBottom: 2,
                }}
              >
                Messages
              </div>
              {result.messages
                .filter((m) => matchesLocal(m.topic_wa, m.thread_id))
                .map((m) => (
                  <div
                    key={m.id}
                    style={{
                      padding: "4px 6px",
                      borderRadius: 8,
                      background: "#ffffff",
                      border: "1px solid #e5e7eb",
                      marginBottom: 4,
                    }}
                  >
                    <div
                      style={{
                        fontSize: 11,
                        color: "#111827",
                        marginBottom: 2,
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                      title={m.text || undefined}
                    >
                      {m.text || "—"}
                    </div>
                    <div
                      style={{
                        fontSize: 10,
                        color: "#9ca3af",
                      }}
                    >
                      {new Date(m.ts).toLocaleString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}{" "}
                      • {m.topic_wa || "—"}
                    </div>
                  </div>
                ))}
            </div>
          )}

          {/* Visits */}
          {scopes.includes("visit") && result.visits.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: "#0f172a",
                  marginBottom: 2,
                }}
              >
                Visits
              </div>
              {result.visits
                .filter((v) => matchesLocal(v.topic_wa, v.thread_id))
                .map((v) => (
                  <div
                    key={v.id}
                    style={{
                      padding: "4px 6px",
                      borderRadius: 8,
                      background: "#ffffff",
                      border: "1px solid #e5e7eb",
                      marginBottom: 4,
                    }}
                  >
                    <div
                      style={{
                        fontSize: 11,
                        color: "#111827",
                        marginBottom: 1,
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                      title={v.title || v.uri || undefined}
                    >
                      {v.title || v.uri || "—"}
                    </div>
                    <div
                      style={{
                        fontSize: 10,
                        color: "#6b7280",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                      title={v.host || undefined}
                    >
                      {v.host || "—"}
                    </div>
                    <div
                      style={{
                        fontSize: 10,
                        color: "#9ca3af",
                      }}
                    >
                      {new Date(v.ts).toLocaleString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}{" "}
                      • {v.topic_wa || "—"}
                    </div>
                  </div>
                ))}
            </div>
          )}

          {/* Files */}
          {scopes.includes("file") && result.files.length > 0 && (
            <div style={{ marginBottom: 4 }}>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: "#0f172a",
                  marginBottom: 2,
                }}
              >
                Files
              </div>
              {result.files
                .filter((f) => matchesLocal(f.topic_wa, f.thread_id))
                .map((f) => (
                  <div
                    key={f.file_id}
                    style={{
                      padding: "4px 6px",
                      borderRadius: 8,
                      background: "#ffffff",
                      border: "1px solid #e5e7eb",
                      marginBottom: 4,
                    }}
                  >
                    <div
                      style={{
                        fontSize: 11,
                        color: "#111827",
                        marginBottom: 1,
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                      title={f.name || undefined}
                    >
                      📎 {f.name || "(unnamed file)"}
                    </div>
                    <div
                      style={{
                        fontSize: 10,
                        color: "#6b7280",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                      title={f.mime || undefined}
                    >
                      {f.mime || "file"} • {f.size ?? "?"} bytes
                    </div>
                    <div
                      style={{
                        fontSize: 10,
                        color: "#9ca3af",
                      }}
                    >
                      {new Date(f.created_ts).toLocaleString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}{" "}
                      • {f.topic_wa || "—"}
                    </div>
                  </div>
                ))}
            </div>
          )}

          {scopes.includes("message") &&
            scopes.includes("visit") &&
            scopes.includes("file") &&
            result.messages.length === 0 &&
            result.visits.length === 0 &&
            result.files.length === 0 && (
              <div style={{ fontSize: 11, color: "#9ca3af" }}>
                No results for “{result.q}”.
              </div>
            )}
        </div>
      )}
    </div>
  );
}