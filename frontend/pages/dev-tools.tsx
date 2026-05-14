// Glyph_Net_Browser/src/routes/DevTools.tsx
import { useState } from "react";

export default function DevTools() {
  const [source, setSource] = useState("");
  const [translated, setTranslated] = useState("");
  const [status, setStatus] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);

  async function handleTranslate() {
    if (!source.trim()) {
      setStatus("⚠️ Nothing to translate yet.");
      return;
    }
    try {
      setStatus("🔡 Translating Photon line → glyphs…");
      const res = await fetch("/api/photon/translate_line", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ line: source }),
      });
      const data = await res.json();
      setTranslated(data.translated || "");
      setStatus("✅ Translated");
    } catch (err: any) {
      setStatus(`❌ Translate error: ${err.message || String(err)}`);
    }
  }

  async function handleRun() {
    const code = translated.trim() || source.trim();
    if (!code) {
      setStatus("⚠️ No code to run yet.");
      return;
    }

    setRunning(true);
    setStatus("⚡ Executing via Photon–Symatics bridge…");

    try {
      const res = await fetch("/api/photon/execute_raw", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: code }),
      });
      const data = await res.json();
      if (!data.ok) {
        throw new Error(data.detail || data.error || "Execution failed");
      }
      setResult(data.results);
      setStatus(`✅ Executed ${data.count} line(s) through bridge`);
      // Let overlays / HUDs listen if you add them later
      window.dispatchEvent(
        new CustomEvent("photon:run", { detail: { source: code } })
      );
    } catch (err: any) {
      setStatus(`❌ Bridge error: ${err.message || String(err)}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
        height: "100%",
      }}
    >
      <h1 style={{ fontSize: 18, fontWeight: 600 }}>
        🛠 Dev Tools – Photon Editor
      </h1>

      <textarea
        value={source}
        onChange={(e) => setSource(e.target.value)}
        placeholder="Type PhotonLang / symbolic code here…"
        style={{
          flex: 1,
          minHeight: 160,
          width: "100%",
          resize: "vertical",
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 13,
          padding: 8,
          borderRadius: 8,
          border: "1px solid #e5e7eb",
          background: "#020617",
          color: "#e5e7eb",
        }}
      />

      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={handleTranslate}
          disabled={running}
          style={{
            padding: "6px 10px",
            borderRadius: 8,
            border: "1px solid #0ea5e9",
            background: "#0284c7",
            color: "#e0f2fe",
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          🔡 Translate
        </button>
        <button
          onClick={handleRun}
          disabled={running}
          style={{
            padding: "6px 10px",
            borderRadius: 8,
            border: "1px solid #22c55e",
            background: running ? "#15803d" : "#16a34a",
            color: "#ecfdf5",
            fontSize: 12,
            cursor: running ? "default" : "pointer",
          }}
        >
          {running ? "Running…" : "▶ Run"}
        </button>
      </div>

      {translated && (
        <div
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 11,
            padding: 8,
            borderRadius: 8,
            border: "1px solid #e5e7eb",
            background: "#020617",
            color: "#a5b4fc",
          }}
        >
          <strong>Glyph stream:</strong>
          <pre style={{ marginTop: 4, whiteSpace: "pre-wrap" }}>
            {translated}
          </pre>
        </div>
      )}

      {status && (
        <div
          style={{
            fontSize: 11,
            padding: 8,
            borderRadius: 8,
            border: "1px solid #e5e7eb",
            background: "#f9fafb",
          }}
        >
          {status}
        </div>
      )}

      {result && (
        <pre
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 11,
            padding: 8,
            borderRadius: 8,
            border: "1px solid #e5e7eb",
            background: "#0b1120",
            color: "#e5e7eb",
            overflowX: "auto",
          }}
        >
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}