// Glyph_Net_Browser/src/components/PhotonEditor.tsx
import { useState } from "react";

type PhotonEditorProps = {
  docId?: string;
};

// Helper: POST JSON to the Photon API (relative to browser origin)
async function postJson(path: string, body: any) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `HTTP ${res.status} — ${text || res.statusText}`
    );
  }

  return res.json();
}

export default function PhotonEditor({ docId = "devtools" }: PhotonEditorProps) {
  const [content, setContent] = useState("");
  const [currentName, setCurrentName] = useState(docId);
  const [translated, setTranslated] = useState("");
  const [status, setStatus] = useState(
    'Idle — type some Photon source and hit "Translate".'
  );
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const charCount = content.length;

  async function handleTranslate() {
    setStatus("Translating…");
    setError(null);

    try {
      const data = await postJson("/api/photon/translate_block", {
        source: content,
      });
      setTranslated(data.translated || "");
      setStatus("Translated.");
    } catch (err: any) {
      console.error("Translate error:", err);
      setStatus("Translate error.");
      setError(err?.message || String(err));
    }
  }

  async function handleRun() {
    if (!translated.trim()) {
      setStatus("Idle.");
      setError("No translated glyph code — run Translate first.");
      return;
    }

    setRunning(true);
    setStatus("Running…");
    setError(null);

    try {
      const data = await postJson("/api/photon/execute_raw", {
        source: translated,
      });
      setStatus(`Ran ${data.count ?? "?"} line(s).`);
      // Optional: stash data.results somewhere if you want to show it.
    } catch (err: any) {
      console.error("Run error:", err);
      setStatus("Run error.");
      setError(err?.message || String(err));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 8,
        height: "100%",
      }}
    >
      {/* Name + length row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          fontSize: 12,
        }}
      >
        <input
          value={currentName}
          onChange={(e) => setCurrentName(e.target.value)}
          placeholder="Scratchpad name"
          style={{
            padding: "4px 8px",
            borderRadius: 6,
            border: "1px solid #e5e7eb",
            fontSize: 12,
            minWidth: 160,
          }}
        />
        <span style={{ color: "#6b7280" }}>
          Length: {charCount} characters
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
                "JetBrains Mono, ui-monospace, SFMono-Regular, monospace",
              fontSize: 13,
              lineHeight: 1.5,
              background: "transparent",
              color: "#111827",
            }}
            placeholder="Write Photon source or text to translate…"
          />
        </div>

        {/* Right: translated glyphs + buttons */}
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
              translated || 'Run "Translate" to see glyph output.'
            }
            style={{
              flex: 1,
              padding: 10,
              border: "none",
              resize: "none",
              outline: "none",
              fontFamily:
                "JetBrains Mono, ui-monospace, SFMono-Regular, monospace",
              fontSize: 13,
              lineHeight: 1.5,
              background: "transparent",
              color: translated ? "#111827" : "#9ca3af",
            }}
          />
        </div>
      </div>

      {/* Status line */}
      <div
        style={{
          fontSize: 11,
          padding: "6px 8px",
          borderRadius: 8,
          border: error ? "1px solid #fecaca" : "1px solid #e5e7eb",
          background: error ? "#fef2f2" : "#f9fafb",
          color: error ? "#b91c1c" : "#4b5563",
          whiteSpace: "pre-wrap",
        }}
      >
        {error ? `❌ ${error}` : status}
      </div>
    </div>
  );
}