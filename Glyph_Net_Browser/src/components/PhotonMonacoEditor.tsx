// Glyph_Net_Browser/src/components/PhotonMonacoEditor.tsx
// Monaco-based Photon text editor for Dev Tools.

import { useEffect, useState } from "react";
import Editor from "@monaco-editor/react";

type PhotonMonacoEditorProps = {
  docId?: string;
};

export default function PhotonMonacoEditor({
  docId = "devtools",
}: PhotonMonacoEditorProps) {
  const storageKey = `photon.devtools.${docId}`;

  const [code, setCode] = useState<string>("");
  const [translated, setTranslated] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [running, setRunning] = useState(false);

  // Load last code from localStorage
  useEffect(() => {
    try {
      const saved =
        typeof window !== "undefined"
          ? window.localStorage.getItem(storageKey)
          : null;
      if (saved) setCode(saved);
    } catch {
      // ignore
    }
  }, [storageKey]);

  // Persist edits
  useEffect(() => {
    try {
      if (typeof window !== "undefined") {
        window.localStorage.setItem(storageKey, code);
      }
    } catch {
      // ignore
    }
  }, [code, storageKey]);

  // --- Photon language + theme for Monaco ---
  function definePhotonLang(monaco: any) {
    monaco.languages.register({ id: "photonlang" });

    monaco.languages.setMonarchTokensProvider("photonlang", {
      keywords: [
        "Wave",
        "Photon",
        "Resonate",
        "Entangle",
        "Measure",
        "Collapse",
      ],
      operators: ["⊕", "↔", "⟲", "μ", "π", "⇒", "∇"],
      tokenizer: {
        root: [
          [/[A-Z][a-zA-Z_]+/, "keyword"],
          [/λ|ν|ω|π/, "number"],
          [/⊕|↔|⟲|μ|π|⇒|∇/, "operator"],
          [/"([^"\\]|\\.)*$/, "string.invalid"],
          [/"([^"\\]|\\.)*"/, "string"],
          [/#.*$/, "comment"],
        ],
      },
    });

    monaco.editor.defineTheme("photonTheme", {
      base: "vs-dark",
      inherit: true,
      rules: [
        { token: "keyword", foreground: "7DD3FC", fontStyle: "bold" },
        { token: "operator", foreground: "A78BFA" },
        { token: "number", foreground: "FCD34D" },
        { token: "string", foreground: "86EFAC" },
        { token: "comment", foreground: "52525B", fontStyle: "italic" },
      ],
      colors: {
        "editor.background": "#020617",
        "editorLineNumber.foreground": "#4b5563",
        "editorLineNumber.activeForeground": "#e5e7eb",
        "editorCursor.foreground": "#38bdf8",
        "editorIndentGuide.activeBackground": "#1e40af",
      },
    });
  }

  // --- API calls ---

  async function translate() {
    if (!code.trim()) {
      setTranslated("");
      setStatus("Write some PhotonLang first.");
      return;
    }

    try {
      setStatus("Translating…");
      const res = await fetch("/api/photon/translate_line", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ line: code }),
      });

      const data = await res.json();
      setTranslated(data.translated || "");
      setStatus("✅ Translated Photon → glyphs");
    } catch (e: any) {
      console.error("translate error", e);
      setStatus(`❌ Translate error: ${e?.message || "unknown error"}`);
    }
  }

  async function run() {
    if (!translated.trim()) {
      setStatus("⚠️ No translated glyph code available. Try Translate first.");
      return;
    }

    setRunning(true);
    setStatus("⚡ Executing via Photon–Symatics Bridge…");

    try {
      const res = await fetch("/api/photon/execute_raw", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: translated }),
      });

      const data = await res.json();
      if (!data.ok) {
        throw new Error(data.detail || data.error || "Execution failed");
      }

      setStatus(`✅ Executed ${data.count} line(s) through bridge`);
      // If you want to surface results, you can log or extend UI here:
      console.log("Photon execute_raw results:", data.results);
    } catch (e: any) {
      console.error("run error", e);
      setStatus(`❌ Bridge error: ${e?.message || "unknown error"}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      {/* Controls */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", gap: 6 }}>
          <button
            type="button"
            onClick={translate}
            style={buttonStyle}
          >
            Translate
          </button>
          <button
            type="button"
            onClick={run}
            disabled={running}
            style={{
              ...buttonStyle,
              background: running ? "#0f172a" : "#0ea5e9",
              opacity: running ? 0.7 : 1,
            }}
          >
            {running ? "Running…" : "Run"}
          </button>
        </div>

        <div
          style={{
            fontSize: 11,
            color: "#9ca3af",
            fontFamily:
              "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas",
          }}
        >
          docId: {docId}
        </div>
      </div>

      {/* Monaco editor */}
      <div style={{ flex: 1, minHeight: 0 }}>
        <Editor
          height="100%"
          defaultLanguage="photonlang"
          value={code}
          theme="photonTheme"
          beforeMount={definePhotonLang}
          onChange={(value) => setCode(value || "")}
          options={{
            fontFamily: "JetBrains Mono, Menlo, Monaco, Consolas, monospace",
            fontSize: 13,
            lineNumbers: "on",
            minimap: { enabled: false },
            smoothScrolling: true,
            automaticLayout: true,
            scrollBeyondLastLine: false,
          }}
        />
      </div>

      {/* Translation output */}
      <div
        style={{
          borderRadius: 8,
          border: "1px solid #1f2937",
          background: "#020617",
          padding: 8,
          fontFamily:
            "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas",
          fontSize: 11,
          color: "#e5e7eb",
          minHeight: 72,
          maxHeight: 160,
          overflow: "auto",
        }}
      >
        {translated ? (
          <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>
            {translated}
          </pre>
        ) : (
          <span style={{ opacity: 0.6 }}>
            Glyph translation will appear here after you click{" "}
            <strong>Translate</strong>.
          </span>
        )}
      </div>

      {/* Status line */}
      {status && (
        <div
          style={{
            fontSize: 11,
            color: status.startsWith("✅")
              ? "#bbf7d0"
              : status.startsWith("❌")
              ? "#fecaca"
              : "#9ca3af",
          }}
        >
          {status}
        </div>
      )}
    </div>
  );
}

const buttonStyle: React.CSSProperties = {
  padding: "4px 12px",
  borderRadius: 999,
  border: "1px solid #0ea5e9",
  background: "#0f172a",
  color: "#e5e7eb",
  fontSize: 12,
  cursor: "pointer",
};