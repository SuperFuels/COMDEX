// Glyph_Net_Browser/src/components/PhotonEditor.tsx

import { useState } from "react";

type PhotonEditorProps = {
  docId?: string;
};

/**
 * Figure out where the SCI / Photon API lives.
 *
 * Priority:
 *  1. VITE_PHOTON_API_BASE env var
 *  2. GitHub Codespaces dev: 5173 → 3001
 *  3. Generic localhost:3001
 */
function detectApiBase(): string {
  const envBase = (import.meta as any).env?.VITE_PHOTON_API_BASE as
    | string
    | undefined;

  if (envBase && envBase.trim()) {
    return envBase.replace(/\/$/, "");
  }

  if (typeof window !== "undefined") {
    const origin = window.location.origin;

    // Codespaces: browser on -5173 → SCI Next app on -3001
    if (origin.includes("-5173.app.github.dev")) {
      return origin.replace("-5173.app.github.dev", "-3001.app.github.dev");
    }

    // Generic local Vite: :5173 → :3001
    if (origin.includes(":5173")) {
      return origin.replace(":5173", ":3001");
    }
  }

  // Fallback: local SCI dev
  return "http://localhost:3001";
}

const API_BASE = detectApiBase();

/** Helper: POST JSON to the Photon API */
async function postJson(path: string, body: any) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `HTTP ${res.status} ${res.statusText}${
        text ? ` — ${text.slice(0, 200)}` : ""
      }`,
    );
  }

  return res.json();
}

export default function PhotonEditor({ docId = "devtools" }: PhotonEditorProps) {
  const [name, setName] = useState(docId);
  const [content, setContent] = useState("");
  const [translated, setTranslated] = useState("");
  const [status, setStatus] = useState<string>(
    'Idle — type some Photon source and hit "Translate".',
  );
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const charCount = content.length;

  // ----------------- actions -----------------

  async function handleTranslate() {
    if (!content.trim()) {
      setTranslated("");
      setStatus("Nothing to translate (input is empty).");
      setError(null);
      return;
    }

    setStatus("Translating…");
    setError(null);

    try {
      // Match the SCI translator panel: /api/photon/translate_block
      const data = await postJson("/api/photon/translate_block", {
        source: content,
      });

      const glyphs = data.translated || data.output || "";
      setTranslated(glyphs);
      setStatus("Translated OK.");
    } catch (err: any) {
      console.error("Translate error:", err);
      setStatus("Translate error.");
      setError(`Translate error: ${err?.message || String(err)}`);
    }
  }

  async function handleRun() {
    if (!translated.trim()) {
      setStatus("Nothing to run — translate first.");
      setError("No translated glyph code — run Translate first.");
      return;
    }

    setStatus("Running…");
    setError(null);
    setRunning(true);

    try {
      const data = await postJson("/api/photon/execute_raw", {
        source: translated,
      });

      setStatus(`Executed ${data.count ?? "?"} line(s).`);
      // If you want, you can stash data.results in state later.
    } catch (err: any) {
      console.error("Run error:", err);
      setStatus("Run error.");
      setError(`Run error: ${err?.message || String(err)}`);
    } finally {
      setRunning(false);
    }
  }

  // ----------------- UI -----------------

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 8,
        height: "100%",
      }}
    >
      {/* Name + length + API base */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          fontSize: 12,
        }}
      >
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Scratchpad name"
          style={{
            padding: "4px 8px",
            borderRadius: 6,
            border: "1px solid #e5e7eb",
            fontSize: 12,
            minWidth: 160,
          }}
        />
        <span style={{ color: "#6b7280" }}>Length: {charCount} characters</span>

        <span style={{ marginLeft: "auto", fontSize: 11, color: "#6b7280" }}>
          API base: <code>{API_BASE}</code>
        </span>
      </div>

      {/* Editor + glyph pane */}
      <div
        style={{
          flex: 1,
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
          alignItems: "stretch",
        }}
      >
        {/* Left: source */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            borderRadius: 12,
            border: "1px solid #e5e7eb",
            background: "#ffffff",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "6px 10px",
              borderBottom: "1px solid #e5e7eb",
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: 0.03,
              textTransform: "uppercase",
              color: "#6b7280",
            }}
          >
            Source
          </div>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            style={{
              flex: 1,
              padding: 10,
              border: "none",
              resize: "none",
              outline: "none",
              fontFamily:
                "JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
              fontSize: 13,
              lineHeight: 1.5,
              background: "#f9fafb",
              color: "#111827",
            }}
            placeholder="Write Photon source or text to translate…"
          />
        </div>

        {/* Right: translated glyphs */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            borderRadius: 12,
            border: "1px solid #e5e7eb",
            background: "#ffffff",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "6px 10px",
              borderBottom: "1px solid #e5e7eb",
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: 0.03,
              textTransform: "uppercase",
              color: "#6b7280",
              display: "flex",
              alignItems: "center",
            }}
          >
            <span>Translated Glyphs</span>

            <div style={{ marginLeft: "auto", display: "inline-flex", gap: 8 }}>
              <button
                type="button"
                onClick={handleTranslate}
                style={{
                  fontSize: 12,
                  padding: "4px 10px",
                  borderRadius: 999,
                  border: "1px solid #d1d5db",
                  background: "#eff6ff",
                  cursor: "pointer",
                }}
              >
                Translate
              </button>
              <button
                type="button"
                onClick={handleRun}
                disabled={running}
                style={{
                  fontSize: 12,
                  padding: "4px 10px",
                  borderRadius: 999,
                  border: "1px solid #bbf7d0",
                  background: running ? "#bbf7d0" : "#dcfce7",
                  cursor: running ? "default" : "pointer",
                }}
              >
                ⚡ {running ? "Running…" : "Run"}
              </button>
            </div>
          </div>

          <textarea
            readOnly
            value={
              translated ||
              'Run "Translate" to see glyph output.'
            }
            style={{
              flex: 1,
              padding: 10,
              border: "none",
              resize: "none",
              outline: "none",
              fontFamily:
                "JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
              fontSize: 13,
              lineHeight: 1.5,
              background: "#f9fafb",
              color: translated ? "#111827" : "#9ca3af",
            }}
          />
        </div>
      </div>

      {/* Status / error line */}
      <div
        style={{
          fontSize: 11,
          padding: "6px 8px",
          borderRadius: 8,
          border: error ? "1px solid #fecaca" : "1px solid #e5e7eb",
          background: error ? "#fef2f2" : "#f9fafb",
          color: error ? "#b91c1c" : "#374151",
          whiteSpace: "pre-wrap",
        }}
      >
        {error ?? status}
      </div>
    </div>
  );
}