"use client";

import React, { useMemo, useState } from "react";
import SciSqsPanel from "@/pages/sci/sci_sqs_panel";
import { QuantumFieldCanvasLoader } from "@/components/Hologram/QuantumFieldCanvasLoader";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? ""; // e.g. https://comdex-api.../api

type ToolId = "editor" | "atomsheet" | "qfc";
type ViewMode = "code" | "glyph";

export default function IDE() {
  const [activeTool, setActiveTool] = useState<ToolId>("editor");

  // sidebar collapse
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // editor layout
  const [viewMode, setViewMode] = useState<ViewMode>("code");
  const [splitView, setSplitView] = useState(false);

  // text buffers
  const [codeBuffer, setCodeBuffer] = useState<string>(
    [
      "# Photon test script for SCI IDE",
      "# Expect: container_id, wave, resonance, memory -> glyphs",
      "",
      "container_id = 'sci_ide_demo'",
      "wave = quantum_wave(source=container_id)",
      "resonance = tune_resonance(wave, target='AionCore')",
      "memory = write_memory(container_id, payload=resonance)",
      "",
      "print('Photon pipeline complete:', container_id, resonance, memory)",
    ].join("\n")
  );
  const [glyphBuffer, setGlyphBuffer] = useState<string>("");

  const [compressionInfo, setCompressionInfo] = useState<{
    charsBefore: number;
    charsAfter: number;
    compressionRatio: number;
  } | null>(null);

  const sidebarWidthClass = sidebarCollapsed ? "w-14" : "w-64";

  // ───────────────── Code → Glyph (real API) ─────────────────
  async function handleCodeToGlyph() {
    if (!codeBuffer.trim()) return;

    // If API base isn’t configured, fall back to dummy compression
    if (!API_BASE) {
      const approxGlyphs = Math.max(1, Math.round(codeBuffer.length / 40));
      const dummy = "⬢".repeat(approxGlyphs);

      setGlyphBuffer(dummy);
      setViewMode("glyph");
      setCompressionInfo({
        charsBefore: codeBuffer.length,
        charsAfter: dummy.length,
        compressionRatio:
          codeBuffer.length > 0
            ? 1 - dummy.length / codeBuffer.length
            : 0,
      });
      console.warn(
        "[SCI IDE] NEXT_PUBLIC_API_URL is not set; using local dummy glyph converter."
      );
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/photon/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: codeBuffer }),
      });

      if (!res.ok) {
        console.error("Code → Glyph translate failed:", await res.text());
        return;
      }

      const data = await res.json();
      const translated: string = data.translated ?? "";
      const charsBefore: number = data.chars_before ?? codeBuffer.length;
      const charsAfter: number = data.chars_after ?? translated.length;
      const compressionRatio: number =
        data.compression_ratio ??
        (charsBefore > 0 ? 1 - charsAfter / charsBefore : 0);

      setGlyphBuffer(translated);
      setViewMode("glyph");
      setCompressionInfo({ charsBefore, charsAfter, compressionRatio });
    } catch (err) {
      console.error("Code → Glyph error:", err);
    }
  }

  // ───────────────── Glyph → Code (for now: just switch back) ─────────────────
  // Later we can wire this to /api/photon/translate_reverse with proper glyph stream.
  function handleGlyphToCode() {
    setViewMode("code");
  }

  const compressionLabel = useMemo(() => {
    if (!compressionInfo) return "Paste code and run Code → Glyph to see reduction";
    const pct = (compressionInfo.compressionRatio * 100).toFixed(1);
    return `${compressionInfo.charsBefore} chars → ${compressionInfo.charsAfter} chars • ${pct}% reduction`;
  }, [compressionInfo]);

  return (
    <div className="flex h-[calc(100vh-64px)] md:h-[calc(100vh-80px)] bg-slate-950 text-slate-100">
      {/* ───────────────── Sidebar ───────────────── */}
      <aside
        className={`${sidebarWidthClass} border-r border-slate-800 flex flex-col bg-slate-950/95`}
      >
        <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800">
          {!sidebarCollapsed && (
            <span className="text-xs font-semibold tracking-wide text-slate-300">
              SCI IDE
            </span>
          )}
          <button
            type="button"
            onClick={() => setSidebarCollapsed((v) => !v)}
            className="text-xs text-slate-400 hover:text-slate-100"
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {sidebarCollapsed ? "»" : "«"}
          </button>
        </div>

        <nav className="flex-1 px-2 py-3 space-y-2">
          <ToolButton
            icon="</>"
            label="Text Editor (.ptn)"
            active={activeTool === "editor"}
            collapsed={sidebarCollapsed}
            onClick={() => setActiveTool("editor")}
          />

          <ToolButton
            icon="🧮"
            label="AtomSheet (4D grid)"
            active={activeTool === "atomsheet"}
            collapsed={sidebarCollapsed}
            onClick={() => setActiveTool("atomsheet")}
          />

          <ToolButton
            icon="🕸"
            label="Quantum Field Canvas"
            active={activeTool === "qfc"}
            collapsed={sidebarCollapsed}
            onClick={() => setActiveTool("qfc")}
          />
        </nav>
      </aside>

      {/* ───────────────── Main Column ───────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-950/90">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-semibold text-slate-100">
              {activeTool === "editor"
                ? "Untitled.ptn"
                : activeTool === "atomsheet"
                ? "AtomSheet Viewer"
                : "Quantum Field Canvas"}
            </span>
            <span className="text-xs text-slate-500">/ Codex workspace</span>
          </div>

          {activeTool === "editor" && (
            <div className="flex items-center gap-2 text-xs">
              <button
                type="button"
                onClick={() => setViewMode("code")}
                className={`px-2 py-1 rounded ${
                  viewMode === "code"
                    ? "bg-emerald-600 text-white"
                    : "bg-slate-800 text-slate-200"
                }`}
              >
                Code
              </button>
              <button
                type="button"
                onClick={() => setViewMode("glyph")}
                className={`px-2 py-1 rounded ${
                  viewMode === "glyph"
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-800 text-slate-200"
                }`}
              >
                Glyph
              </button>
              <button
                type="button"
                onClick={() => setSplitView((v) => !v)}
                className="px-2 py-1 rounded bg-slate-800 text-slate-100"
              >
                {splitView ? "Single View" : "Split View"}
              </button>
              <button
                type="button"
                onClick={handleCodeToGlyph}
                className="px-2 py-1 rounded bg-purple-600 hover:bg-purple-500 text-white"
              >
                Code → Glyph
              </button>
              <button
                type="button"
                onClick={handleGlyphToCode}
                className="px-2 py-1 rounded bg-purple-600 hover:bg-purple-500 text-white"
              >
                Glyph → Code
              </button>

              <div className="ml-3 text-[11px] text-slate-300 font-mono">
                {compressionLabel}
              </div>
            </div>
          )}
        </header>

        {/* Main content */}
        <div className="flex-1 flex overflow-hidden">
          {activeTool === "editor" && (
            <EditorPane
              viewMode={viewMode}
              splitView={splitView}
              codeBuffer={codeBuffer}
              glyphBuffer={glyphBuffer}
              setCodeBuffer={setCodeBuffer}
              setGlyphBuffer={setGlyphBuffer}
            />
          )}

          {activeTool === "atomsheet" && (
            <div className="flex-1 overflow-auto bg-slate-950">
              <SciSqsPanel />
            </div>
          )}

          {activeTool === "qfc" && (
            <div className="flex-1 bg-black">
              <QuantumFieldCanvasLoader containerId="default.dc.json" />
            </div>
          )}
        </div>

        {/* Bottom status bar */}
        <footer className="h-10 md:h-12 border-t border-slate-800 bg-slate-950/95 flex items-center justify-between px-4 text-xs text-slate-300">
          <div>Φ coherence monitor (placeholder) · ready</div>
          <div className="text-slate-500">
            SCI IDE · local workspace · offline-capable UX target
          </div>
        </footer>
      </div>
    </div>
  );
}

/* ───────────────── Editor Pane ───────────────── */

type EditorPaneProps = {
  viewMode: ViewMode;
  splitView: boolean;
  codeBuffer: string;
  glyphBuffer: string;
  setCodeBuffer: (v: string) => void;
  setGlyphBuffer: (v: string) => void;
};

function EditorPane({
  viewMode,
  splitView,
  codeBuffer,
  glyphBuffer,
  setCodeBuffer,
  setGlyphBuffer,
}: EditorPaneProps) {
  if (splitView) {
    return (
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 border-r border-slate-800">
          <EditorTextarea
            label="Code (.ptn)"
            value={codeBuffer}
            onChange={setCodeBuffer}
          />
        </div>
        <div className="flex-1">
          <EditorTextarea
            label="Glyph view"
            value={glyphBuffer}
            onChange={setGlyphBuffer}
          />
        </div>
      </div>
    );
  }

  const showCode = viewMode === "code";

  return (
    <div className="flex-1">
      <EditorTextarea
        label={showCode ? "Code (.ptn)" : "Glyph view"}
        value={showCode ? codeBuffer : glyphBuffer}
        onChange={showCode ? setCodeBuffer : setGlyphBuffer}
      />
    </div>
  );
}

type EditorTextareaProps = {
  label: string;
  value: string;
  onChange: (v: string) => void;
};

function EditorTextarea({ label, value, onChange }: EditorTextareaProps) {
  return (
    <div className="flex flex-col h-full min-h-[70vh]">
      <div className="px-3 py-1 text-[11px] text-slate-400 border-b border-slate-800">
        {label}
      </div>
      <textarea
        className="flex-1 w-full bg-slate-950 text-slate-100 text-sm font-mono px-3 py-2 outline-none resize-none"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
      />
      <div className="border-t border-slate-800">
        <button
          type="button"
          className="mt-1 mb-1 ml-3 px-3 py-1 text-xs bg-purple-600 hover:bg-purple-500 text-white font-medium rounded"
        >
          + Save to Atom Vault
        </button>
      </div>
    </div>
  );
}

/* ───────────────── Sidebar button ───────────────── */

type ToolButtonProps = {
  icon: string;
  label: string;
  active: boolean;
  collapsed: boolean;
  onClick: () => void;
};

function ToolButton({ icon, label, active, collapsed, onClick }: ToolButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full flex items-center ${
        collapsed ? "justify-center" : "justify-start"
      } gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
        active
          ? "bg-slate-800 text-slate-50"
          : "bg-transparent text-slate-300 hover:bg-slate-900/70"
      }`}
    >
      <span className="text-base">{icon}</span>
      {!collapsed && <span className="truncate">{label}</span>}
    </button>
  );
}