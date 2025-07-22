import React, { useState } from "react";
import axios from "axios";
import CodexRegisterViewer from "./CodexRegisterViewer";
import CodexScrollPresets from "./CodexScrollPresets";
import CodexScrollHistory from "./CodexScrollHistory";
import CodexLangEditor from "./CodexLangEditor";
import CodexRegisterDebug from "./CodexRegisterDebug";
import CodexDiffViewer from "./CodexDiffViewer";

interface TraceStep {
  step: number;
  instruction: string;
  before: Record<string, any>;
  after: Record<string, any>;
}

export default function CodexScrollRunner() {
  const [scroll, setScroll] = useState("");
  const [lastScroll, setLastScroll] = useState("");
  const [context, setContext] = useState("{}");
  const [result, setResult] = useState<any>(null);
  const [registers, setRegisters] = useState<Record<string, any>>({});
  const [trace, setTrace] = useState<TraceStep[]>([]);

  const runScroll = async () => {
    try {
      const parsedContext = JSON.parse(context || "{}");
      const res = await axios.post("/api/codex/scroll", {
        scroll,
        context: parsedContext,
      });

      if (res.data.status === "ok") {
        setResult(res.data.result.output);
        setRegisters(res.data.result.registers || {});
        setTrace(res.data.result.trace || []);
      } else {
        setResult(`Error: ${res.data.error}`);
        setRegisters({});
        setTrace([]);
      }
    } catch (err) {
      setResult(`Execution failed: ${err}`);
      setRegisters({});
      setTrace([]);
    }
  };

  const mutateScroll = async () => {
    try {
      const parsedTree = JSON.parse(scroll); // assumes CodexLang JSON tree
      const res = await axios.post("/api/codex/mutate", { tree: parsedTree });

      if (res.data.status === "ok") {
        setLastScroll(scroll); // Save old version before mutation
        const mutatedTree = res.data.mutated;
        setScroll(JSON.stringify(mutatedTree, null, 2));
      } else {
        alert("Mutation error: " + res.data.error);
      }
    } catch (err) {
      alert("Mutation request failed");
    }
  };

  return (
    <div className="space-y-4">
      <CodexScrollPresets onSelectScroll={setScroll} />

      <CodexLangEditor value={scroll} onChange={setScroll} />

      <textarea
        value={context}
        onChange={(e) => setContext(e.target.value)}
        placeholder="Optional context (JSON)"
        className="w-full p-2 bg-gray-900 text-white rounded-md border border-cyan-500"
        rows={4}
      />

      <div className="flex gap-4">
        <button
          onClick={runScroll}
          className="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded-md"
        >
          ▶ Run Scroll
        </button>

        <button
          onClick={mutateScroll}
          className="bg-purple-700 hover:bg-purple-800 text-white px-4 py-2 rounded-md"
        >
          🧬 Mutate Scroll
        </button>
      </div>

      <div className="flex gap-4">
        <button
          onClick={() => {
            const name = prompt("Enter name to save scroll:");
            if (name && scroll) {
              axios.post("/api/codex/save", {
                name,
                tree: JSON.parse(scroll),
              });
            }
          }}
          className="bg-green-700 hover:bg-green-800 text-white px-4 py-2 rounded-md"
        >
          💾 Save Scroll
        </button>

        <button
          onClick={() => {
            const name = prompt("Download scroll name:");
            if (name) {
              window.open(`/api/codex/download/${name}`);
            }
          }}
          className="bg-yellow-600 hover:bg-yellow-700 text-white px-4 py-2 rounded-md"
        >
          📦 Export .codex
        </button>
      </div>

      {result && (
        <div className="bg-gray-800 p-4 rounded-md text-white">
          <h3 className="font-bold text-cyan-400 mb-2">🌀 Output</h3>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}

      <CodexRegisterViewer registers={registers} />

      <CodexRegisterDebug trace={trace} />

      {trace.length > 0 && (
        <div className="bg-gray-900 p-3 text-sm text-white rounded-md">
          <h4 className="font-bold text-cyan-300 mb-2">🔍 Raw Execution Trace</h4>
          <pre className="whitespace-pre-wrap">{JSON.stringify(trace, null, 2)}</pre>
        </div>
      )}

      <CodexScrollHistory />

      {lastScroll && scroll && (
        <CodexDiffViewer original={lastScroll} mutated={scroll} />
      )}
    </div>
  );
}