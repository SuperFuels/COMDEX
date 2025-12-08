// Glyph_Net_Browser/src/components/PhotonEditor.tsx
// Photon ↔ Glyph editor for the Glyph Net browser Dev Tools.

import { useState, useEffect } from "react";
import { compileMotifStub } from "../lib/api/motif";
import type { GhxPacket } from "./DevFieldHologram3D";
import { importHoloSnapshot } from "../lib/api/holo";
import type { HoloIR } from "../lib/types/holo";

type PhotonEditorProps = {
  docId?: string;
};

// ---- Types from SCI editor ----
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

type MotifCompileResponse = {
  kind: string; // "photon_motif"
  ghx: {
    ghx_version: string;
    origin: string;
    container_id: string;
    nodes: any[];
    edges: any[];
    metadata: Record<string, any>;
  };
  holo?: {
    holo_id: string;
    container_id: string;
    tick: number;
    revision: number;
    ghx: any;
    metadata: Record<string, any>;
  } | null;
};

// Simple detector: is this the motif stub language?
function looksLikeMotifStub(source: string): boolean {
  if (!source) return false;
  if (/#\s*holo:holo:crystal::user:devtools:motif=/.test(source)) return true;
  if (/\bmotif\s+"[^"]+"\s*\{/.test(source)) return true;
  return false;
}

// ---- AST + hologram types ----
type AstResult = {
  ast: any;
  kind: "python" | "photon" | "codex" | "nl";
  glyphs?: any[];
  mermaid?: string;
  ghx?: GhxPacket;
};

// Same sample block as SCI editor
const SAMPLE_PHOTON = `# Photon test script for SCI IDE
# Expect: container_id, wave, resonance, memory -> glyphs
⊕ container main {
  wave "hello";
  resonance 0.42;
  memory "sticky-notes";
}
`;

// Helper: POST JSON via the /api/photon proxy (Vite dev + packaged)
async function postJson<T = any>(path: string, body: any): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} — ${text || res.statusText}`);
  }

  return res.json() as Promise<T>;
}

export default function PhotonEditor({ docId = "devtools" }: PhotonEditorProps) {
  const [content, setContent] = useState<string>(SAMPLE_PHOTON);
  const [currentName, setCurrentName] = useState(docId);
  const [translated, setTranslated] = useState<string>("");
  const [status, setStatus] = useState<string>(
    'Idle — type some Photon source and hit "Code → Glyph".',
  );
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  // Code translator language (only what /api/photon/translate supports)
  const [codeLanguage, setCodeLanguage] = useState<"photon" | "python">(
    "photon",
  );

  // AST-related state (can be broader: photon/python/codex/nl)
  const [astLanguage, setAstLanguage] = useState<
    "python" | "photon" | "codex" | "nl"
  >("photon");
  const [astResult, setAstResult] = useState<AstResult | null>(null);
  const [loadingAst, setLoadingAst] = useState(false);
  const [astError, setAstError] = useState<string | null>(null);

  const charCount = content.length;

  // ⬇️ React to “Send to Text Editor” and also hydrate from any buffered stub
  useEffect(() => {
    function applyStub(detail: any) {
      if (!detail) return;
      if (detail.docId && detail.docId !== docId) return;

      if (typeof detail.source === "string") {
        setContent(detail.source);
      }
      if (typeof detail.name === "string") {
        setCurrentName(detail.name);
      }
    }

    // 1) On mount, see if something left a stub for us
    if (typeof window !== "undefined") {
      const pending = (window as any).__DEVTOOLS_LAST_PHOTON_STUB;
      if (pending) {
        applyStub(pending);
        delete (window as any).__DEVTOOLS_LAST_PHOTON_STUB;
      }
    }

    // 2) Listen for live events while we're mounted
    function handlePhotonOpen(ev: Event) {
      const detail = (ev as CustomEvent).detail || {};
      applyStub(detail);
    }

    window.addEventListener("devtools.photon_open", handlePhotonOpen as any);
    return () =>
      window.removeEventListener(
        "devtools.photon_open",
        handlePhotonOpen as any,
      );
  }, [docId]);

  // ---------------- AST: View structure ----------------
  async function handleViewAst() {
    if (!content.trim()) {
      setAstResult(null);
      setAstError("No source to analyze.");
      return;
    }

    setLoadingAst(true);
    setAstError(null);
    try {
      const res = await fetch("/api/ast", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: content, language: astLanguage }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      const data = (await res.json()) as AstResult;
      setAstResult(data);
    } catch (e: any) {
      setAstError(String(e.message || e));
      setAstResult(null);
    } finally {
      setLoadingAst(false);
    }
  }

  // ---------------- AST: View as hologram ----------------
  async function handleViewAstHologram() {
    if (!content.trim()) {
      setAstResult(null);
      setAstError("No source to analyze.");
      return;
    }

    setLoadingAst(true);
    setAstError(null);

    try {
      const res = await fetch("/api/ast/hologram", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: content, language: astLanguage }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${res.status}`);
      }

      const data = (await res.json()) as AstResult; // AstResult has .ghx

      setAstResult(data);

      // 🔊 Broadcast to Dev Field Canvas + queue globally
      if (typeof window !== "undefined" && (data as any).ghx) {
        (window as any).__DEVTOOLS_LAST_GHX = (data as any).ghx;

        window.dispatchEvent(
          new CustomEvent("devtools.ghx", {
            detail: {
              source: "ast-hologram",
              language: data.kind,
              ghx: (data as any).ghx,
            },
          }),
        );

        window.dispatchEvent(
          new CustomEvent("devtools.switch_tab", {
            detail: { tool: "field" },
          }),
        );
      }
    } catch (e: any) {
      console.error("AST → Hologram failed:", e);
      setAstError(String(e.message || e));
      setAstResult(null);
    } finally {
      setLoadingAst(false);
    }
  }

  // ---------------- Motif stub tools ----------------
  async function handleMotifToHologram() {
    if (!content.trim()) {
      setAstError("No motif stub to compile.");
      return;
    }

    setLoadingAst(true);
    setAstError(null);

    try {
      const resp = await compileMotifStub(content, { holo: false });

      // Broadcast GHX to Field Lab
      if (typeof window !== "undefined") {
        (window as any).__DEVTOOLS_LAST_GHX = resp.ghx;
        window.dispatchEvent(
          new CustomEvent("devtools.ghx", {
            detail: {
              source: "motif-compiler",
              language: "photon_motif",
              ghx: resp.ghx,
            },
          }),
        );
        window.dispatchEvent(
          new CustomEvent("devtools.switch_tab", {
            detail: { tool: "field" },
          }),
        );
      }

      setAstResult({
        ast: { motif: resp.ghx.metadata?.motif ?? null },
        kind: "photon",
        glyphs: [],
        mermaid: undefined,
        ghx: resp.ghx,
      });
    } catch (e: any) {
      setAstError(e.message || String(e));
      setAstResult(null);
    } finally {
      setLoadingAst(false);
    }
  }

  async function handleMotifToHolo() {
    if (!content.trim()) return;
    setIsBusy(true);
    setError(null);
    setStatus("Compiling motif stub to .holo…");

    try {
      const resp = await compileMotifStub(content, { holo: true });

      if (!resp.holo) {
        throw new Error("Motif compiler did not return a .holo payload");
      }

      // 1) Persist the new holo snapshot as a crystal
      const saved: HoloIR = await importHoloSnapshot(resp.holo);

      // 2) Optionally broadcast that a new holo exists
      if (typeof window !== "undefined") {
        (window as any).__DEVTOOLS_LAST_HOLO = saved;

        window.dispatchEvent(
          new CustomEvent("devtools.holo_saved", {
            detail: { holo: saved },
          }),
        );

        // Optional: jump user to Crystals tab to show the new entry
        window.dispatchEvent(
          new CustomEvent("devtools.switch_tab", {
            detail: { tool: "crystals" },
          }),
        );
      }

      setStatus(`Saved motif as .holo: ${saved.holo_id}`);
    } catch (err: any) {
      console.error("Motif → .holo failed:", err);
      setError(err?.message ?? "Motif → .holo failed");
      setStatus("Motif → .holo failed");
    } finally {
      setIsBusy(false);
    }
  }

  // ---------------- Code → Glyph (uses enriched Photon translator) ----------------
  async function handleCodeToGlyph() {
    if (!content.trim()) {
      setTranslated("");
      setStatus("Nothing to translate.");
      return;
    }

    setIsBusy(true);
    setError(null);
    setStatus("Translating code → glyph…");

    try {
      const data: TranslateResponse = await postJson("/api/photon/translate", {
        text: content,
        language: codeLanguage, // 👈 use current code language selector
      });

      setTranslated(data.translated ?? "");

      const before = data.chars_before ?? content.length;
      const after = data.chars_after ?? (data.translated?.length ?? 0);
      const reduction = before > 0 ? (1 - after / before) * 100 : 0;

      setStatus(
        `Compression: ${before} → ${after} chars (−${reduction.toFixed(1)}%)`,
      );
    } catch (e: any) {
      console.error("Code → Glyph error:", e);
      setError(e?.message || String(e));
      setStatus("Code → Glyph failed.");
    } finally {
      setIsBusy(false);
    }
  }

  // ---------------- Glyph → Code (round-trip check) ----------------
  async function handleGlyphToCode() {
    if (!translated.trim()) {
      setStatus("No glyph text to reverse-translate.");
      return;
    }

    setIsBusy(true);
    setError(null);
    setStatus("Translating glyph → code…");

    try {
      const glyph_stream = translated
        .split(/\r?\n/)
        .filter((l) => l.trim().length);

      const data: ReverseResponse = await postJson(
        "/api/photon/translate_reverse",
        { glyph_stream },
      );

      setContent(data.photon ?? "");
      setStatus(`Glyph → Code: recovered ${data.count} lines.`);
    } catch (e: any) {
      console.error("Glyph → Code error:", e);
      setError(e?.message || String(e));
      setStatus("Glyph → Code failed.");
    } finally {
      setIsBusy(false);
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
        <span style={{ color: "#6b7280" }}>Length: {charCount} characters</span>
      </div>

      {/* Editor + glyph pane + AST inspector */}
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
          {/* Header row: title + language + buttons */}
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
              justifyContent: "space-between",
              gap: 8,
            }}
          >
            <span>
              Source ({codeLanguage === "python" ? ".py" : ".ptn"})
            </span>

            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {/* Language picker for Code↔Glyph */}
              <label style={{ fontSize: 11 }}>Code lang:</label>
              <select
                value={codeLanguage}
                onChange={(e) =>
                  setCodeLanguage(e.target.value as "photon" | "python")
                }
                style={{ fontSize: 11 }}
              >
                <option value="photon">Photon (.ptn)</option>
                <option value="python">Python</option>
              </select>

              {/* Actions */}
              <button onClick={handleCodeToGlyph} disabled={isBusy}>
                Code → Glyph
              </button>
              <button onClick={handleGlyphToCode} disabled={isBusy}>
                Glyph → Code
              </button>
            </div>
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
            placeholder="Write Photon, Python, CodexLang, or NL to translate / inspect…"
          />
        </div>

        {/* Right: translated glyphs + AST inspector */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 8,
            height: "100%",
          }}
        >
          {/* Translated glyphs card */}
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              background: "#ffffff",
              overflow: "hidden",
              minHeight: 0,
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
                gap: 8,
              }}
            >
              <span>Translated Glyphs</span>

              <div
                style={{
                  marginLeft: "auto",
                  display: "inline-flex",
                  gap: 8,
                }}
              >
                <button
                  type="button"
                  onClick={handleCodeToGlyph}
                  disabled={isBusy}
                  style={{
                    fontSize: 12,
                    padding: "4px 10px",
                    borderRadius: 999,
                    border: "1px solid #d1d5db",
                    background: "#eff6ff",
                    cursor: isBusy ? "default" : "pointer",
                    opacity: isBusy ? 0.7 : 1,
                  }}
                >
                  Code → Glyph
                </button>
                <button
                  type="button"
                  onClick={handleGlyphToCode}
                  disabled={isBusy}
                  style={{
                    fontSize: 12,
                    padding: "4px 10px",
                    borderRadius: 999,
                    border: "1px solid #bbf7d0",
                    background: "#dcfce7",
                    cursor: isBusy ? "default" : "pointer",
                    opacity: isBusy ? 0.7 : 1,
                  }}
                >
                  Glyph → Code
                </button>
              </div>
            </div>

            <textarea
              readOnly
              value={translated || 'Run "Code → Glyph" to see glyph output.'}
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

          {/* AST inspector card */}
          <div
            style={{
              flexBasis: "45%",
              display: "flex",
              flexDirection: "column",
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              padding: 8,
              minHeight: 0,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 8,
                marginBottom: 4,
                fontSize: 11,
              }}
            >
              <span style={{ fontWeight: 600 }}>AST Inspector</span>

              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <select
                  value={astLanguage}
                  onChange={(e) =>
                    setAstLanguage(e.target.value as AstResult["kind"])
                  }
                  style={{ fontSize: 11 }}
                >
                  <option value="photon">Photon (.ptn)</option>
                  <option value="python">Python</option>
                  <option value="codex">CodexLang</option>
                  <option value="nl">Natural language</option>
                </select>

                <button
                  type="button"
                  onClick={handleViewAst}
                  disabled={loadingAst || !content.trim()}
                  style={{
                    fontSize: 11,
                    padding: "4px 10px",
                    borderRadius: 999,
                    border: "1px solid #e5e7eb",
                    background: loadingAst ? "#e5e7eb" : "#0f172a",
                    color: loadingAst ? "#6b7280" : "#e5e7eb",
                    cursor: loadingAst ? "default" : "pointer",
                  }}
                >
                  {loadingAst ? "Building AST…" : "View as AST"}
                </button>

                <button
                  type="button"
                  onClick={handleViewAstHologram}
                  disabled={loadingAst || !content.trim()}
                  style={{
                    fontSize: 11,
                    padding: "4px 10px",
                    borderRadius: 999,
                    border: "1px solid #e5e7eb",
                    background: loadingAst ? "#e5e7eb" : "#0369a1",
                    color: "#e5e7eb",
                    cursor: loadingAst ? "default" : "pointer",
                  }}
                >
                  {loadingAst ? "Building…" : "AST → Hologram"}
                </button>
              </div>
            </div>

            {/* Motif-specific tools (only show when the buffer looks like a motif stub) */}
            {looksLikeMotifStub(content) && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  marginBottom: 4,
                  fontSize: 11,
                }}
              >
                <span style={{ color: "#6b7280", marginRight: 4 }}>Motif tools:</span>

                <button
                  type="button"
                  onClick={handleMotifToHologram}
                  disabled={isBusy || !content.trim()}
                  style={{
                    fontSize: 11,
                    padding: "3px 10px",
                    borderRadius: 999,
                    border: "1px solid #0ea5e9",
                    background: "#e0f2fe",
                    color: "#0f172a",
                    cursor: isBusy ? "default" : "pointer",
                    opacity: isBusy ? 0.7 : 1,
                  }}
                >
                  Motif → Hologram
                </button>

                <button
                  type="button"
                  onClick={handleMotifToHolo}
                  disabled={isBusy || !content.trim()}
                  style={{
                    fontSize: 11,
                    padding: "3px 10px",
                    borderRadius: 999,
                    border: "1px solid #22c55e",
                    background: "#dcfce7",
                    color: "#14532d",
                    cursor: isBusy ? "default" : "pointer",
                    opacity: isBusy ? 0.7 : 1,
                  }}
                >
                  Motif → .holo
                </button>
              </div>
            )}

            {astError && (
              <div
                style={{
                  fontSize: 11,
                  color: "#b91c1c",
                  marginBottom: 4,
                }}
              >
                Error: {astError}
              </div>
            )}

            {!astResult && !astError && (
              <div
                style={{
                  fontSize: 11,
                  color: "#6b7280",
                }}
              >
                Click &ldquo;View as AST&rdquo; (or &ldquo;AST → Hologram&rdquo;)
                to inspect structure.
              </div>
            )}

            {astResult && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 6,
                  fontSize: 11,
                  overflow: "auto",
                }}
              >
                <div style={{ color: "#6b7280" }}>
                  kind: <code>{astResult.kind}</code> · glyphs:{" "}
                  {astResult.glyphs ? astResult.glyphs.length : 0}
                </div>

                {astResult.ghx && (
                  <div style={{ color: "#047857", marginTop: 2 }}>
                    hologram: {astResult.ghx.nodes.length} nodes ·{" "}
                    {astResult.ghx.edges.length} edges · origin:{" "}
                    <code>{astResult.ghx.origin}</code>
                  </div>
                )}

                <details open>
                  <summary
                    style={{ cursor: "pointer", fontWeight: 500 }}
                  >
                    AST JSON
                  </summary>
                  <pre
                    style={{
                      maxHeight: 120,
                      overflow: "auto",
                      background: "#ffffff",
                      borderRadius: 6,
                      padding: 6,
                    }}
                  >
                    {JSON.stringify(astResult.ast, null, 2)}
                  </pre>
                </details>

                <details>
                  <summary
                    style={{ cursor: "pointer", fontWeight: 500 }}
                  >
                    Glyphs
                  </summary>
                  <pre
                    style={{
                      maxHeight: 90,
                      overflow: "auto",
                      background: "#ffffff",
                      borderRadius: 6,
                      padding: 6,
                    }}
                  >
                    {JSON.stringify(astResult.glyphs ?? [], null, 2)}
                  </pre>
                </details>

                <details>
                  <summary
                    style={{ cursor: "pointer", fontWeight: 500 }}
                  >
                    Mermaid (preview text)
                  </summary>
                  <pre
                    style={{
                      maxHeight: 90,
                      overflow: "auto",
                      background: "#ffffff",
                      borderRadius: 6,
                      padding: 6,
                    }}
                  >
                    {astResult.mermaid || "flowchart TD\n  n0[no data]"}
                  </pre>
                </details>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )};