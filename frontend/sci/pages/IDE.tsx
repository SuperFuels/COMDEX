"use client";

import React, { useMemo, useState } from "react";
import SciSqsPanel from "@/pages/sci/sci_sqs_panel";
import { QuantumFieldCanvasLoader } from "@/components/Hologram/QuantumFieldCanvasLoader";
import SciFileCabinet, { SciFolder } from "@/components/sci/SciFileCabinet";
type ToolId = "editor" | "atomsheet" | "qfc";
type ViewMode = "code" | "glyph";
import Image from "next/image";

type CompressionInfo = {
  charsBefore: number;
  charsAfter: number;
  compressionRatio: number;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export default function IDE() {
  const [activeTool, setActiveTool] = useState<ToolId>("editor");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isCabinetOpen, setIsCabinetOpen] = useState(true);

  const onSelectEditor = () => {
    setActiveTool("editor");
    setIsCabinetOpen(true); // 🔓 open the file cabinet whenever Text Editor is selected
  };

  const [viewMode, setViewMode] = useState<ViewMode>("code");
  const [splitView, setSplitView] = useState(false);

  const [codeBuffer, setCodeBuffer] = useState<string>(
    [
      "# Photon test script for SCI IDE",
      "# Expect: container_id, wave, resonance, memory -> glyphs",
      "container_id = 'demo_container'",
      "wave = quantum.wave('alpha')",
      "resonance = entangle(container_id, wave)",
      "memory = store(resonance, mode='long_term')",
    ].join("\n")
  );
  const [glyphBuffer, setGlyphBuffer] = useState<string>("");

  const [compression, setCompression] = useState<CompressionInfo | null>(null);
  const [isTranslating, setIsTranslating] = useState(false);
  const [translateError, setTranslateError] = useState<string | null>(null);

  // Fallback visual compression if backend didn't respond with numbers
  const fallbackCompression = useMemo(() => {
    const codeChars = codeBuffer.length;
    const glyphChars = glyphBuffer.length;
    if (!codeChars || !glyphChars) return null;

    const ratio = 1 - glyphChars / codeChars;
    return {
      charsBefore: codeChars,
      charsAfter: glyphChars,
      compressionRatio: Math.max(0, ratio),
    };
  }, [codeBuffer, glyphBuffer]);

  const effectiveCompression = compression ?? fallbackCompression;

  // ───────── SCI file system state ─────────
  const [folders, setFolders] = useState<SciFolder[]>([
    {
      id: "default",
      name: "Codex workspace",
      files: [{ id: "file-1", name: "Untitled.ptn" }],
    },
  ]);

  const [activeFileId, setActiveFileId] = useState<string>("file-1");
  const [activeFileName, setActiveFileName] = useState<string>("Untitled.ptn");

  const handleCreateFolder = () => {
    const id = `folder-${Date.now()}`;
    setFolders((prev) => [
      ...prev,
      { id, name: "New container", files: [] },
    ]);
  };

  const handleCreateFile = (folderId: string) => {
    const fileId = `file-${Date.now()}`;
    setFolders((prev) =>
      prev.map((f) =>
        f.id === folderId
          ? {
              ...f,
              files: [...f.files, { id: fileId, name: "Untitled.ptn" }],
            }
          : f,
      ),
    );
    setActiveFileId(fileId);
    setActiveFileName("Untitled.ptn");
  };

  const handleSelectFile = (fileId: string) => {
    setActiveFileId(fileId);
    const found = folders.flatMap((f) => f.files).find((f) => f.id === fileId);
    if (found) setActiveFileName(found.name);
  };

  const handleRenameFile = (fileId: string, name: string) => {
    setFolders((prev) =>
      prev.map((folder) => ({
        ...folder,
        files: folder.files.map((file) =>
          file.id === fileId ? { ...file, name } : file,
        ),
      })),
    );
    if (fileId === activeFileId) setActiveFileName(name);
  };

  // ───────────────── Code → Glyph (backend call) ─────────────────
  const handleCodeToGlyph = async () => {
    if (!codeBuffer.trim()) return;
    if (!API_BASE) {
      console.warn("NEXT_PUBLIC_API_URL is not set");
      setTranslateError("API base URL missing (NEXT_PUBLIC_API_URL).");
      return;
    }

    setIsTranslating(true);
    setTranslateError(null);

    try {
      const res = await fetch(`${API_BASE}/photon/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: codeBuffer }),
      });

      if (!res.ok) {
        const msg = await res.text();
        console.error("translate failed", res.status, msg);
        setTranslateError(`HTTP ${res.status}: ${msg.slice(0, 160)}`);
        return;
      }

      const data = await res.json();

      const translated: string = data.translated ?? "";
      setGlyphBuffer(translated);
      setViewMode("glyph");

      setCompression({
        charsBefore: data.chars_before ?? codeBuffer.length,
        charsAfter: data.chars_after ?? translated.length,
        compressionRatio: data.compression_ratio ?? 0,
      });
    } catch (err: any) {
      console.error("convert error", err);
      setTranslateError(String(err?.message ?? err));
    } finally {
      setIsTranslating(false);
    }
  };

  // For now Glyph → Code just flips you back; full reverse endpoint can come later
  const handleGlyphToCode = () => {
    setViewMode("code");
  };

  const sidebarWidthClass = sidebarCollapsed ? "w-14" : "w-64";

  return (
    <div className="flex h-[calc(100vh-56px)] bg-background text-foreground">
      {/* ───────────── Sidebar ───────────── */}
      <aside
        className={`${sidebarWidthClass} flex flex-col border-r border-border bg-background`}
      >
        <div className="flex items-center justify-between border-b border-border px-3 py-2">
          <div className="flex items-center gap-2">
            {!sidebarCollapsed && (
              <Image
                src="/photon_logo.png"      // file in frontend/public/photon_logo.png
                alt="Photon IDE"
                width={120}
                height={28}
                priority
              />
            )}
          </div>

          <button
            type="button"
            onClick={() => setSidebarCollapsed((v) => !v)}
            className="text-xs text-foreground/60 hover:text-foreground"
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
            onClick={onSelectEditor}
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

      {/* ───────────── Main Column ───────────── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-950/90">
          {/* left side: file name + workspace */}
          <div className="flex items-center gap-2 text-sm">
            <input
              className="bg-transparent text-sm font-medium outline-none ring-0 border-none px-1 rounded hover:bg-muted/60"
              value={activeFileName}
              onChange={(e) => setActiveFileName(e.target.value)}
              onBlur={(e) =>
                handleRenameFile(
                  activeFileId,
                  e.target.value.trim() || "Untitled.ptn",
                )
              }
            />
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
                disabled={isTranslating}
                className="px-3 py-1 rounded bg-purple-600 hover:bg-purple-500 disabled:bg-purple-900 text-white"
              >
                {isTranslating ? "Converting…" : "Code → Glyph"}
              </button>
              <button
                type="button"
                onClick={handleGlyphToCode}
                className="px-3 py-1 rounded bg-purple-600 hover:bg-purple-500 text-white"
              >
                Glyph → Code
              </button>

              <div className="ml-3 text-[11px] text-slate-300 font-mono">
                {effectiveCompression ? (
                  <>
                    {effectiveCompression.charsBefore} chars →{" "}
                    {effectiveCompression.charsAfter} glyph-chars ·{" "}
                    <span className="text-emerald-400">
                      {(effectiveCompression.compressionRatio * 100).toFixed(1)}% reduction
                    </span>
                  </>
                ) : (
                  <span className="text-slate-500">
                    Paste code and run Code → Glyph to see reduction
                  </span>
                )}
              </div>
            </div>
          )}
        </header>

        {/* Error banner (if any) */}
        {translateError && activeTool === "editor" && (
          <div className="px-4 py-2 text-xs bg-red-900/60 text-red-100 border-b border-red-700">
            Glyph translation error: {translateError}
          </div>
        )}

        {/* ───────────── Main content ───────────── */}
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

        {/* Bottom status */}
        <footer className="h-10 border-t border-slate-800 bg-slate-950/95 flex items-center justify-between px-4 text-xs text-slate-300">
          <div>Φ coherence monitor (placeholder) · ready</div>
          <div className="text-slate-500">
            SCI IDE · local workspace · offline-capable UX target
          </div>
        </footer>
      </div>
    </div>
  );
}

/* ───────────── Editor panes ───────────── */

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
      <div className="flex flex-1 min-h-[70vh] overflow-hidden">
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
    <div className="flex-1 min-h-[70vh]">
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
    <div className="flex flex-col h-full min-h-[60vh]">
      <div className="px-3 py-1 text-[11px] text-slate-400 border-b border-slate-800">
        {label}
      </div>
      <textarea
        className="flex-1 min-h-[50vh] w-full bg-slate-950 text-slate-100 text-sm font-mono px-3 py-2 outline-none resize-none"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
      />
      <button
        type="button"
        className="px-3 py-1 text-[11px] bg-purple-600 hover:bg-purple-500 text-white text-center"
      >
        + Save to Atom Vault
      </button>
    </div>
  );
}

/* ───────────── Sidebar button ───────────── */

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