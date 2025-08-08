// frontend/components/Lean/LeanInjectorPanel.tsx
"use client";
import React, { useState } from "react";

type PreviewMode = "raw" | "normalized";
type ContainerType = "dc" | "hoberman" | "sec" | "exotic" | "symmetry" | "atom";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/+$/, "") ||
  "http://localhost:8080/api"; // dev default

export default function LeanInjectorPanel() {
  const [mode, setMode] = useState<"inject" | "export">("inject");

  // Core inputs
  const [containerPath, setContainerPath] = useState(
    "backend/modules/dimensions/containers/test_container.dc.json"
  );
  const [leanPath, setLeanPath] = useState(
    "backend/modules/lean/examples/test_theorems.lean"
  );
  const [overwrite, setOverwrite] = useState(true);
  const [autoClean, setAutoClean] = useState(true);
  const [dedupe, setDedupe] = useState(true);
  const [validate, setValidate] = useState(false);
  const [preview, setPreview] = useState<PreviewMode>("raw");

  // Export options
  const [containerType, setContainerType] = useState<ContainerType>("dc");
  const [outPath, setOutPath] = useState("");

  // Optional extras (reports/graphs)
  const [summary, setSummary] = useState(true);
  const [pretty, setPretty] = useState(true);
  const [reportKind, setReportKind] = useState<"" | "md" | "json">("");
  const [reportOut, setReportOut] = useState("");
  const [dotOut, setDotOut] = useState("");
  const [ghxOut, setGhxOut] = useState("");
  const [ghxBundle, setGhxBundle] = useState("");

  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    setResult(null);

    try {
      const endpoint =
        mode === "inject"
          ? `${API_BASE}/lean/inject`
          : `${API_BASE}/lean/export`;

      const payload =
        mode === "inject"
          ? {
              container_path: containerPath,
              lean_path: leanPath,
              overwrite,
              auto_clean: autoClean,
              dedupe,
              preview,
              validate,
              summary,
              pretty,
              // optional:
              report: reportKind || undefined,
              report_out: reportOut || undefined,
              dot: dotOut || undefined,
              ghx_out: ghxOut || undefined,
              ghx_bundle: ghxBundle || undefined,
            }
          : {
              lean_path: leanPath,
              container_type: containerType,
              preview,
              pretty,
              summary,
              // optional:
              out_path: outPath || undefined,
              report: reportKind || undefined,
              report_out: reportOut || undefined,
              dot: dotOut || undefined,
            };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include", // keep if you use cookies; remove if not needed
        body: JSON.stringify(payload),
      });

      let data: any;
      const text = await res.text();
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        data = { raw: text }; // backend might return plain text on errors
      }

      if (!res.ok) {
        throw new Error(data?.detail || data?.error || `Request failed (${res.status})`);
      }
      setResult(data);
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="p-4 space-y-4 max-w-3xl">
      <h2 className="text-xl font-semibold">Lean ↔ Glyph Injector</h2>
      <p className="text-xs text-gray-500">API: {API_BASE}</p>

      <div className="flex gap-2">
        <button
          className={`px-3 py-1 rounded ${mode === "inject" ? "bg-black text-white" : "bg-gray-200"}`}
          onClick={() => setMode("inject")}
        >
          Inject into existing container
        </button>
        <button
          className={`px-3 py-1 rounded ${mode === "export" ? "bg-black text-white" : "bg-gray-200"}`}
          onClick={() => setMode("export")}
        >
          Export new container
        </button>
      </div>

      <div className="space-y-2">
        <label className="block text-sm">Lean file</label>
        <input
          className="w-full border rounded px-2 py-1"
          value={leanPath}
          onChange={(e) => setLeanPath(e.target.value)}
          placeholder="backend/modules/lean/examples/test_theorems.lean"
        />
      </div>

      {mode === "inject" ? (
        <>
          <div className="space-y-2">
            <label className="block text-sm">Container JSON path</label>
            <input
              className="w-full border rounded px-2 py-1"
              value={containerPath}
              onChange={(e) => setContainerPath(e.target.value)}
              placeholder="backend/modules/dimensions/containers/test_container.dc.json"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={overwrite} onChange={(e) => setOverwrite(e.target.checked)} />
              Overwrite
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={autoClean} onChange={(e) => setAutoClean(e.target.checked)} />
              Auto-clean
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={dedupe} onChange={(e) => setDedupe(e.target.checked)} />
              Dedupe
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={validate} onChange={(e) => setValidate(e.target.checked)} />
              Validate
            </label>
          </div>
        </>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm">Container type</label>
              <select
                className="w-full border rounded px-2 py-1"
                value={containerType}
                onChange={(e) => setContainerType(e.target.value as ContainerType)}
              >
                <option value="dc">dc</option>
                <option value="hoberman">hoberman</option>
                <option value="sec">sec</option>
                <option value="exotic">exotic</option>
                <option value="symmetry">symmetry</option>
                <option value="atom">atom</option>
              </select>
            </div>
            <div>
              <label className="block text-sm">Output path (optional)</label>
              <input
                className="w-full border rounded px-2 py-1"
                value={outPath}
                onChange={(e) => setOutPath(e.target.value)}
                placeholder="backend/modules/dimensions/containers/out.dc.json"
              />
            </div>
          </div>
        </>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm">Preview mode</label>
          <select
            className="w-full border rounded px-2 py-1"
            value={preview}
            onChange={(e) => setPreview(e.target.value as PreviewMode)}
          >
            <option value="raw">raw</option>
            <option value="normalized">normalized</option>
          </select>
        </div>

        <div className="flex items-center gap-2 mt-6">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={summary} onChange={(e) => setSummary(e.target.checked)} />
            Summary
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={pretty} onChange={(e) => setPretty(e.target.checked)} />
            Pretty
          </label>
        </div>
      </div>

      {/* Optional extras */}
      <details className="border rounded p-3">
        <summary className="cursor-pointer select-none">Advanced (reports / graphs / GHX)</summary>
        <div className="grid grid-cols-2 gap-3 mt-3">
          <div>
            <label className="block text-sm">Report kind</label>
            <select
              className="w-full border rounded px-2 py-1"
              value={reportKind}
              onChange={(e) => setReportKind(e.target.value as "" | "md" | "json")}
            >
              <option value="">(none)</option>
              <option value="md">md</option>
              <option value="json">json</option>
            </select>
          </div>
          <div>
            <label className="block text-sm">Report out</label>
            <input
              className="w-full border rounded px-2 py-1"
              value={reportOut}
              onChange={(e) => setReportOut(e.target.value)}
              placeholder="report.md or report.json"
            />
          </div>

          <div>
            <label className="block text-sm">DOT out</label>
            <input
              className="w-full border rounded px-2 py-1"
              value={dotOut}
              onChange={(e) => setDotOut(e.target.value)}
              placeholder="deps.dot"
            />
          </div>

          {mode === "inject" && (
            <>
              <div>
                <label className="block text-sm">GHX out dir</label>
                <input
                  className="w-full border rounded px-2 py-1"
                  value={ghxOut}
                  onChange={(e) => setGhxOut(e.target.value)}
                  placeholder="out/ghx"
                />
              </div>
              <div>
                <label className="block text-sm">GHX bundle file</label>
                <input
                  className="w-full border rounded px-2 py-1"
                  value={ghxBundle}
                  onChange={(e) => setGhxBundle(e.target.value)}
                  placeholder="out/packets.ghx.json"
                />
              </div>
            </>
          )}
        </div>
      </details>

      <button
        className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50"
        onClick={run}
        disabled={busy}
      >
        {busy ? "Working…" : mode === "inject" ? "Inject" : "Export"}
      </button>

      {error && <div className="text-red-600 text-sm">Error: {error}</div>}

      {result && (
        <pre className="bg-gray-50 border rounded p-3 text-xs overflow-auto">
{JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}