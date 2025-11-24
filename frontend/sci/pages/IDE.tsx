"use client";

import React, { useMemo, useState } from "react";
import SciSqsPanel from "@/pages/sci/sci_sqs_panel";
import { QuantumFieldCanvasLoader } from "@/components/Hologram/QuantumFieldCanvasLoader";

/**
 * Main tools available in the SCI IDE
 */
type ToolId = "editor" | "atomsheet" | "qfc";

/**
 * Which view is shown in the main editor region
 */
type ViewMode = "code" | "glyph";

export default function IDE() {
  const [activeTool, setActiveTool] = useState<ToolId>("editor");

  // sidebar collapse
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // editor layout
  const [viewMode, setViewMode] = useState<ViewMode>("code");
  const [splitView, setSplitView] = useState(false);

  // simple local buffers used for Code ⇄ Glyph demo + compression calc
  const [codeBuffer, setCodeBuffer] = useState<string>(
    "Photon CRDT editor — synced across Codex workspace\n\n" +
      "// Paste any block of code here to see glyph compression estimates."
  );
  const [glyphBuffer, setGlyphBuffer] = useState<string>("");

  // very simple “compression” calc just to visualise impact
  const compression = useMemo(() => {
    const codeChars = codeBuffer.length;
    const glyphChars = glyphBuffer.length;

    if (!codeChars || !glyphChars) {
      return {
        codeChars,
        glyphChars,
        percentReduction: 0,
      };
    }
    const ratio = 1 - glyphChars / codeChars;
    return {
      codeChars,
      glyphChars,
      percentReduction: Math.max(0, Math.round(ratio * 100)),
    };
  }, [codeBuffer, glyphBuffer]);

  // naive toy encoder/decoder just to show the UX
  const handleCodeToGlyph = () => {
    if (!codeBuffer.trim()) return;
    // toy compression: ~ 1 glyph per 40 characters
    const approxGlyphs = Math.max(1, Math.round(codeBuffer.length / 40));
    setGlyphBuffer("⬢".repeat(approxGlyphs));
    setViewMode("glyph");
  };

  const handleGlyphToCode = () => {
    if (!glyphBuffer.trim()) return;
    const decoded =
      `// pseudo-decoded from ${glyphBuffer.length} glyphs\n` + glyphBuffer;
    setCodeBuffer(decoded);
    setViewMode("code");
  };

  const sidebarWidthClass = sidebarCollapsed ? "w-14" : "w-64";

  return (
    <div className="flex h-[calc(100vh-80px)] bg-slate-950 text-slate-100">
      {/* ───────────────────────── Sidebar ───────────────────────── */}
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

      {/* ───────────────────────── Main Column ───────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top “tab” bar + controls */}
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

          {/* Code ⇄ Glyph controls */}
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

              {/* Compression indicator */}
              <div className="ml-3 text-[11px] text-slate-300 font-mono">
                {compression.codeChars > 0 && compression.glyphChars > 0 ? (
                  <>
                    {compression.codeChars} chars → {compression.glyphChars} glyphs ·{" "}
                    <span className="text-emerald-400">
                      {compression.percentReduction}% reduction
                    </span>
                  </>
                ) : (
                  <span className="text-slate-500">Paste code to see compression</span>
                )}
              </div>
            </div>
          )}
        </header>

        {/* ───────────────────────── Main content ───────────────────────── */}
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
              {/* For now we bind QFC to a default container; this can be wired to the
                  currently open AtomSheet or .ptn doc later. */}
              <QuantumFieldCanvasLoader containerId="default.dc.json" />
            </div>
          )}
        </div>

        {/* ───────────────────────── Bottom status strip ───────────────────────── */}
        <footer className="h-16 border-t border-slate-800 bg-slate-950/95 flex items-center justify-between px-4 text-xs text-slate-300">
          <div>
            Φ coherence monitor (placeholder) · ready
          </div>
          <div className="text-slate-500">
            SCI IDE · local workspace · offline-capable UX target
          </div>
        </footer>
      </div>
    </div>
  );
}

/* ───────────────────────── Editor Pane ───────────────────────── */

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
            readOnly={false /* allow manual tweaking for now */}
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
  readOnly?: boolean;
};

function EditorTextarea({ label, value, onChange, readOnly }: EditorTextareaProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-1 text-[11px] text-slate-400 border-b border-slate-800">
        {label}
      </div>
      <textarea
        className="flex-1 w-full bg-slate-950 text-slate-100 text-sm font-mono px-3 py-2 outline-none resize-none"
        value={value}
        readOnly={readOnly}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
      />
      <button
        type="button"
        className="px-3 py-2 text-xs bg-purple-600 hover:bg-purple-500 text-white font-medium text-center"
      >
        + Save to Atom Vault
      </button>
    </div>
  );
}

/* ───────────────────────── Sidebar button ───────────────────────── */

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