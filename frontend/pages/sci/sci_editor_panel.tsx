// =====================================================
//  🌊 SCI PhotonLang Editor — Enhanced Edition
// =====================================================
"use client";

import React, { useEffect, useRef, useState } from "react";
import Editor, { loader } from "@monaco-editor/react";
import PhotonLensOverlay from "@/components/sci/PhotonLensOverlay";
import SQIEnergyMeter from "@/components/sci/SQIEnergyMeter";
import PhotonTranslatorPanel from "@/components/PhotonTranslatorPanel";

// Dynamically load Monaco from CDN
loader.config({
  paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs" },
});

export default function SciEditorPanel({
  wsUrl,
  containerId,
  userId = "default",
}: {
  wsUrl?: string;
  containerId?: string;
  userId?: string;
}) {
  const [code, setCode] = useState<string>("");
  const [translated, setTranslated] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [autoRun, setAutoRun] = useState(false);
  const [highlightReady, setHighlightReady] = useState(false);
  const runBtnRef = useRef<HTMLButtonElement | null>(null);

  // ========================================
  // 🔁 Load & Persist Editor State
  // ========================================
  useEffect(() => {
    const saved = localStorage.getItem("sci.editor.last");
    if (saved) setCode(saved);
  }, []);

  useEffect(() => {
    localStorage.setItem("sci.editor.last", code);
    if (autoRun && highlightReady) runPhotonExecution("bridge");
    if (code.trim()) translatePhotonLine(code);
  }, [code]);

  // ========================================
  // 🌊 Translation (Human → Glyph)
  // ========================================
  async function translatePhotonLine(line: string) {
    try {
      const res = await fetch("/api/photon/translate_line", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ line }),
      });
      const data = await res.json();
      setTranslated(data.translated || "");
    } catch (e) {
      console.error("Translation failed:", e);
    }
  }

  // ========================================
  // ⚛ Execute Glyph Code via PhotonSymaticsBridge
  // ========================================
  async function runPhotonExecution(mode: "local" | "bridge" = "bridge") {
    if (!translated.trim()) {
      setStatus("⚠️ No translated glyph code available to execute.");
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
      if (!data.ok) throw new Error(data.detail || data.error || "Execution failed");

      setResult(data.results);
      setStatus(`✅ Executed ${data.count} line(s) through bridge`);

      // 🌀 Fire visual overlay event
      window.dispatchEvent(
        new CustomEvent("photon:run", { detail: { source: translated } })
      );
    } catch (e: any) {
      setStatus(`❌ Bridge Error: ${e.message}`);
    } finally {
      setRunning(false);
    }
  }

  // ========================================
  // 🧠 PhotonLang Syntax Highlighting
  // ========================================
  function definePhotonLang(monaco: any) {
    monaco.languages.register({ id: "photonlang" });

    monaco.languages.setMonarchTokensProvider("photonlang", {
      keywords: ["Wave", "Photon", "Resonate", "Entangle", "Measure", "Collapse"],
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
        "editor.background": "#0B0B0F",
        "editorLineNumber.foreground": "#3F3F46",
        "editorLineNumber.activeForeground": "#A1A1AA",
        "editorCursor.foreground": "#38BDF8",
        "editorIndentGuide.activeBackground": "#1E3A8A",
      },
    });

    setHighlightReady(true);
  }

  // ========================================
  // 🧩 Layout
  // ========================================
  return (
    <div className="flex flex-col h-full bg-neutral-950 text-zinc-200">
      {/* Header Bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-800 bg-neutral-900/80">
        <h2 className="text-lg font-semibold">🌊 PhotonLang Editor</h2>
        <div className="flex items-center gap-3">
          <label className="text-xs flex items-center gap-1">
            <input
              type="checkbox"
              checked={autoRun}
              onChange={(e) => setAutoRun(e.target.checked)}
            />
            Auto-run
          </label>
          <button
            ref={runBtnRef}
            onClick={() => runPhotonExecution("bridge")} // ✅ clean TS handler
            disabled={running}
            className={`px-3 py-1 rounded border border-blue-500 text-sm transition ${
              running
                ? "bg-blue-800 animate-pulse"
                : "bg-blue-700 hover:bg-blue-600"
            }`}
          >
            {running ? "Running…" : "► Run"}
          </button>
        </div>
      </div>

      {/* Editor + Overlay */}
      <div className="flex flex-row flex-1 overflow-hidden">
        <div className="flex-1">
          <Editor
            height="100%"
            defaultLanguage="photonlang"
            value={code}
            onChange={(v) => setCode(v || "")}
            beforeMount={definePhotonLang}
            theme="photonTheme"
            options={{
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 13,
              lineNumbers: "on",
              minimap: { enabled: false },
              smoothScrolling: true,
              automaticLayout: true,
              scrollBeyondLastLine: false,
            }}
          />
        </div>

        {/* Right: PhotonLens Visualization */}
        <PhotonLensOverlay containerId={containerId} />
      </div>

      {/* Translator Panel */}
      <div className="border-t border-neutral-800 bg-neutral-900/60 p-2">
        <PhotonTranslatorPanel input={code} translation={translated} />
      </div>

      {/* Status */}
      {status && (
        <div
          className={`px-4 py-2 text-xs border-t ${
            status.startsWith("✅")
              ? "text-green-300 border-green-800 bg-green-900/20"
              : status.startsWith("❌")
              ? "text-red-300 border-red-800 bg-red-900/20"
              : "text-zinc-400 border-neutral-800 bg-neutral-900/60"
          }`}
        >
          {status}
        </div>
      )}

      {/* Results */}
      {result && (
        <pre className="p-3 text-xs bg-neutral-900 border-t border-neutral-800 overflow-x-auto text-zinc-300">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}

      {/* SQI Meter */}
      <SQIEnergyMeter containerId={containerId} />
    </div>
  );
}