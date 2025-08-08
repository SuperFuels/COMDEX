import React, { useState } from "react";

type PreviewMode = "raw" | "normalized";
type ContainerType = "dc" | "hoberman" | "sec" | "exotic" | "symmetry" | "atom";

function apiBase() {
  // If your FastAPI runs on a different origin/port, set NEXT_PUBLIC_API_BASE
  // e.g. http://localhost:8000
  return process.env.NEXT_PUBLIC_API_BASE || "";
}

export default function LeanInjectorPage() {
  const [mode, setMode] = useState<"inject" | "export">("inject");

  // sensible defaults to match your recent runs
  const [leanPath, setLeanPath] = useState("backend/modules/lean/examples/test_theorems.lean");

  // inject mode
  const [containerPath, setContainerPath] = useState("backend/modules/dimensions/containers/test_container.dc.json");
  const [overwrite, setOverwrite] = useState(true);
  const [autoClean, setAutoClean] = useState(true);
  const [dedupe, setDedupe] = useState(true);
  const [validate, setValidate] = useState(true);

  // export mode
  const [containerType, setContainerType] = useState<ContainerType>("dc");
  const [outPath, setOutPath] = useState("");

  const [preview, setPreview] = useState<PreviewMode>("raw");

  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    setResult(null);

    try {
      const base = apiBase();
      const endpoint = mode === "inject" ? `${base}/lean/inject` : `${base}/lean/export`;
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
            }
          : {
              lean_path: leanPath,
              container_type: containerType,
              preview,
              pretty: true,
              out_path: outPath || null,
            };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Request failed");
      setResult(data);
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">Lean ↔︎ Glyph Injector</h1>

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setMode("inject")}
          className={`px-3 py-1 rounded ${mode === "inject" ? "bg-black text-white" : "bg-gray-200"}`}
        >
          Inject into existing container
        </button>
        <button
          onClick={() => setMode("export")}
          className={`px-3 py-1 rounded ${mode === "export" ? "bg-black text-white" : "bg-gray-200"}`}
        >
          Export new container
        </button>
      </div>

      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium">Lean file</label>
          <input
            className="w-full border rounded px-2 py-1"
            value={leanPath}
            onChange={(e) => setLeanPath(e.target.value)}
            placeholder="backend/modules/lean/examples/test_theorems.lean"
          />
        </div>

        {mode === "inject" ? (
          <>
            <div>
              <label className="block text-sm font-medium">Container JSON path</label>
              <input
                className="w-full border rounded px-2 py-1"
                value={containerPath}
                onChange={(e) => setContainerPath(e.target.value)}
                placeholder="backend/modules/dimensions/containers/test_container.dc.json"
              />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
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
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium">Container type</label>
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
                <label className="block text-sm font-medium">Output path (optional)</label>
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

        <div>
          <label className="block text-sm font-medium">Preview mode</label>
          <select
            className="border rounded px-2 py-1"
            value={preview}
            onChange={(e) => setPreview(e.target.value as PreviewMode)}
          >
            <option value="raw">raw</option>
            <option value="normalized">normalized</option>
          </select>
        </div>

        <button
          onClick={run}
          disabled={busy}
          className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50"
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
    </div>
  );
}