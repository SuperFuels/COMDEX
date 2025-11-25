import React, { useState } from "react";
import SciBottomDock from "@/components/sci/SciBottomDock";
import SciFileCabinet, { SciFolder } from "@/components/sci/SciFileCabinet";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

type TranslateResponse = {
  translated: string;
  glyph_count: number;
  chars_before: number;
  chars_after: number;
  compression_ratio: number;
};

type ReverseResponse = {
  status: string;
  photon: string;
  count: number;
  name?: string;
  engine?: string;
};

const SAMPLE_PHOTON = `# Photon test script for SCI IDE
# Expect: container_id, wave, resonance, memory -> glyphs
⊕ container main {
  wave "hello";
  resonance 0.42;
  memory "sticky-notes";
}
`;

export default function SciEditorPanel() {
  // ── file cabinet state ─────────────────────────────────────────────
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

  // ── photon ↔ glyph state ─────────────────────────────────
  const [viewMode, setViewMode] = useState<"code" | "glyph" | "split">("code");
  const [codeText, setCodeText] = useState(SAMPLE_PHOTON);
  const [glyphText, setGlyphText] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const handleCodeToGlyph = async () => {
    if (!codeText.trim()) {
      setGlyphText("");
      setStatus("Nothing to translate.");
      return;
    }
    setIsBusy(true);
    setStatus("Translating code → glyph…");
    try {
      const res = await fetch(`${API_BASE}/photon/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: codeText }),
      });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(`HTTP ${res.status}: ${msg}`);
      }
      const data: TranslateResponse = await res.json();
      setGlyphText(data.translated ?? "");
      setStatus(
        `Compression: ${data.chars_before} → ${data.chars_after} chars (ratio ${(
          data.compression_ratio * 100
        ).toFixed(1)}%)`,
      );
      if (viewMode === "code") setViewMode("split");
    } catch (err: any) {
      console.error(err);
      setStatus(`Code → Glyph failed: ${err.message ?? String(err)}`);
    } finally {
      setIsBusy(false);
    }
  };

  const handleGlyphToCode = async () => {
    if (!glyphText.trim()) {
      setStatus("No glyph text to reverse-translate.");
      return;
    }
    setIsBusy(true);
    setStatus("Translating glyph → code…");
    try {
      const glyph_stream = glyphText
        .split(/\r?\n/)
        .filter((l) => l.trim().length);

      const res = await fetch(`${API_BASE}/photon/translate_reverse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ glyph_stream }),
      });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(`HTTP ${res.status}: ${msg}`);
      }
      const data: ReverseResponse = await res.json();
      setCodeText(data.photon ?? "");
      setStatus(`Glyph → Code: recovered ${data.count} lines.`);
      if (viewMode === "glyph") setViewMode("split");
    } catch (err: any) {
      console.error(err);
      setStatus(`Glyph → Code failed: ${err.message ?? String(err)}`);
    } finally {
      setIsBusy(false);
    }
  };

  const renderCodePane = () => (
    <div className="flex h-full flex-col">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-muted-foreground">
          Code (.ptn)
        </span>
        <button
          className="mt-1 rounded border border-border bg-muted px-3 py-1 text-[11px] font-medium text-foreground hover:bg-muted/70"
          type="button"
        >
          + Save to Atom Vault
        </button>
      </div>
      <textarea
        className="flex-1 min-h-[60vh] resize-none rounded-md border border-border bg-muted p-3 font-mono text-[13px] text-foreground leading-relaxed shadow-inner outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500/40 dark:bg-slate-950 dark:text-slate-100"
        value={codeText}
        onChange={(e) => setCodeText(e.target.value)}
        spellCheck={false}
      />
    </div>
  );

  const renderGlyphPane = () => (
    <div className="flex h-full flex-col">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-muted-foreground">
          Glyph view
        </span>
        <button
          className="mt-1 rounded border border-border bg-muted px-3 py-1 text-[11px] font-medium text-foreground hover:bg-muted/70"
          type="button"
        >
          + Save to Atom Vault
        </button>
      </div>
      <textarea
        className="flex-1 min-h-[60vh] resize-none rounded-md border border-border bg-muted p-3 font-mono text-[13px] text-emerald-700 leading-relaxed shadow-inner outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500/40 dark:bg-slate-950 dark:text-emerald-200"
        value={glyphText}
        onChange={(e) => setGlyphText(e.target.value)}
        spellCheck={false}
      />
    </div>
  );

  return (
    <div className="relative flex min-h-screen flex-col bg-background text-foreground">
      {/* Main IDE content */}
      <div className="flex flex-1 flex-col">
        {/* Top bar */}
        <div className="flex items-center justify-between border-b border-border bg-background/95 px-4 py-2">
          <div>
            <div className="flex items-center gap-2">
              <input
                className="rounded border border-transparent bg-transparent px-1 py-0.5 text-sm font-medium text-foreground hover:border-border focus:border-ring focus:outline-none"
                value={activeFileName}
                onChange={(e) =>
                  handleRenameFile(activeFileId, e.target.value)
                }
              />
              <span className="text-xs uppercase tracking-wide text-muted-foreground">
                / Codex workspace
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              Photon ↔ Glyph translator · offline-capable UX target
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs">
            {/* coherence pill */}
            <span className="rounded-full border border-border bg-muted/60 px-2 py-1 text-[11px] text-foreground/80">
              Φ coherence monitor ·{" "}
              <span className="font-medium text-emerald-600">ready</span>
            </span>
            <span className="rounded-full border border-amber-500/60 bg-amber-500/10 px-2 py-1 text-[11px] text-amber-700">
              Disconnected
            </span>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-2 border-b border-border bg-background px-4 py-2 text-xs">
          <div className="inline-flex overflow-hidden rounded-lg border border-border bg-muted/60">
            <button
              type="button"
              onClick={() => setViewMode("code")}
              className={`px-3 py-1.5 ${
                viewMode === "code"
                  ? "bg-primary text-primary-foreground"
                  : "text-foreground/80 hover:bg-muted"
              }`}
            >
              Code
            </button>
            <button
              type="button"
              onClick={() => setViewMode("glyph")}
              className={`border-l border-border px-3 py-1.5 ${
                viewMode === "glyph"
                  ? "bg-primary text-primary-foreground"
                  : "text-foreground/80 hover:bg-muted"
              }`}
            >
              Glyph
            </button>
            <button
              type="button"
              onClick={() => setViewMode("split")}
              className={`border-l border-border px-3 py-1.5 ${
                viewMode === "split"
                  ? "bg-primary text-primary-foreground"
                  : "text-foreground/80 hover:bg-muted"
              }`}
            >
              Split View
            </button>
          </div>

          <div className="ml-3 inline-flex overflow-hidden rounded-lg border border-border bg-muted/60">
            <button
              type="button"
              onClick={handleCodeToGlyph}
              disabled={isBusy}
              className="px-3 py-1.5 text-[11px] text-sky-700 hover:bg-muted disabled:opacity-50"
            >
              Code → Glyph
            </button>
            <button
              type="button"
              onClick={handleGlyphToCode}
              disabled={isBusy}
              className="border-l border-border px-3 py-1.5 text-[11px] text-emerald-700 hover:bg-muted disabled:opacity-50"
            >
              Glyph → Code
            </button>
          </div>

          <div className="ml-auto text-[11px] text-muted-foreground">
            Paste code and run Code → Glyph to see reduction
          </div>
        </div>

        {/* Main area: sidebar + file cabinet + editors */}
        <div className="px-4 py-3">
          <div className="flex h-[calc(100vh-170px)] gap-4 overflow-hidden">
            {/* Sidebar buttons (4 icons, uniform size) */}
            <div className="flex w-10 shrink-0 flex-col items-center gap-2 border-r border-border pr-3">
              {[
                { label: "Files", glyph: "📁" },
                { label: "Coherence", glyph: "ϕ" },
                { label: "Runtime", glyph: "🧠" },
                { label: "Settings", glyph: "⚙️" },
              ].map((item) => (
                <button
                  key={item.label}
                  type="button"
                  className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-muted text-xs hover:bg-muted/70"
                  title={item.label}
                >
                  <span className="text-[15px] leading-none">
                    {item.glyph}
                  </span>
                </button>
              ))}
            </div>

            {/* File cabinet */}
            <div className="w-64 shrink-0">
              <SciFileCabinet
                folders={folders}
                activeFileId={activeFileId}
                onCreateFolder={handleCreateFolder}
                onCreateFile={handleCreateFile}
                onSelectFile={handleSelectFile}
                onRenameFile={handleRenameFile}
              />
            </div>

            {/* Editors */}
            <div className="flex-1 overflow-hidden">
              <div className="flex h-full gap-4 overflow-hidden">
                {(viewMode === "code" || viewMode === "split") && (
                  <div
                    className={`${
                      viewMode === "split" ? "w-1/2" : "w-full"
                    } h-full flex flex-col`}
                  >
                    {renderCodePane()}
                  </div>
                )}

                {(viewMode === "glyph" || viewMode === "split") && (
                  <div
                    className={`${
                      viewMode === "split" ? "w-1/2" : "w-full"
                    } h-full flex flex-col`}
                  >
                    {renderGlyphPane()}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Status line */}
          <div className="mt-2 text-[11px] text-muted-foreground">
            {isBusy ? "Working…" : status ?? "Idle."}
          </div>
        </div>
      </div>

      {/* Bottom AI/logs dock */}
      <SciBottomDock />
    </div>
  );
}