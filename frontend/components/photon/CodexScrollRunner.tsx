// 📁 frontend/components/CodexScrollRunner.tsx

import { useState } from "react";
import {
  runCodexScroll,
  runPhotonCapsule,
  runPhotonPage,
} from "@/lib/api"; // ✅ corrected import path

export default function CodexScrollRunner() {
  const [mode, setMode] = useState<"codex" | "photon" | "ptn">("codex");
  const [scroll, setScroll] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    try {
      let res: any;

      if (mode === "codex") {
        // CodexLang (scroll-based)
        res = await runCodexScroll(scroll);
      } else if (mode === "photon") {
        // Photon Capsule (.phn)
        try {
          const jsonData = JSON.parse(scroll);
          res = await runPhotonCapsule(jsonData);
        } catch {
          // allow raw capsule path strings
          res = await runPhotonCapsule(scroll);
        }
      } else if (mode === "ptn") {
        // Photon Page (.ptn)
        let jsonData;
        try {
          jsonData = JSON.parse(scroll);
        } catch (err) {
          throw new Error("Invalid JSON format for Photon Page (.ptn)");
        }
        res = await runPhotonPage(jsonData);
      }

      setResult(res);
    } catch (err: any) {
      console.error("Runner Error:", err);
      setResult({
        status: "error",
        message: err.message || "Unknown execution failure",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <select
          className="border rounded p-1"
          value={mode}
          onChange={(e) => setMode(e.target.value as any)}
        >
          <option value="codex">CodexLang (.cxs)</option>
          <option value="photon">Photon Capsule (.phn)</option>
          <option value="ptn">Photon Page (.ptn)</option>
        </select>

        <button
          onClick={run}
          disabled={loading}
          className="px-3 py-1 bg-blue-500 text-white rounded"
        >
          {loading ? "Running..." : "Run"}
        </button>
      </div>

      <textarea
        className="w-full border rounded p-2 h-60 font-mono text-sm"
        placeholder="Enter scroll text, photon capsule JSON, or photon page JSON"
        value={scroll}
        onChange={(e) => setScroll(e.target.value)}
      />

      {result && (
        <pre className="bg-gray-100 rounded p-2 text-xs overflow-x-auto">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}