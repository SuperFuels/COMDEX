"use client";

import React, { useEffect, useState } from "react";
import DnaLogViewer from "./DnaLogViewer"; // ⬅️ New import

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/api\/?$/, "");

export default function AIONDashboardClient() {
  const [status, setStatus] = useState<any>(null);
  const [terminalInput, setTerminalInput] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/aion/status`)
      .then((res) => res.json())
      .then(setStatus)
      .catch(console.error);
  }, []);

  const sendPrompt = async () => {
    if (!terminalInput.trim()) return;
    setLoading(true);
    setResponse("Thinking...");
    try {
      const res = await fetch(`${API_BASE}/aion/prompt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: terminalInput }),
      });
      const data = await res.json();
      setResponse(data.response || "No response received.");
    } catch (err) {
      setResponse("❌ Error talking to AION.");
      console.error(err);
    } finally {
      setLoading(false);
      setTerminalInput("");
    }
  };

  return (
    <div className="flex flex-col min-h-screen text-black font-sans">
      {/* Header */}
      <div className="p-4 border-b bg-white">
        <h1 className="text-3xl font-bold">🧠 AION Dashboard</h1>
        <p className="text-sm text-gray-600">Phase: {status?.phase || "Loading..."}</p>
        <p><strong>Unlocked:</strong> {status?.unlocked?.join(", ") || "Loading..."}</p>
        <p><strong>Locked:</strong> {status?.locked?.join(", ") || "Loading..."}</p>
      </div>

      {/* Terminal Interface */}
      <div className="flex flex-1 overflow-hidden">
        <div className="w-1/2 p-4 border-r overflow-y-auto">
          <h2 className="text-xl font-semibold mb-2">Ask AION</h2>
          <textarea
            value={terminalInput}
            onChange={(e) => setTerminalInput(e.target.value)}
            placeholder="e.g., What milestones did I unlock?"
            rows={10}
            className="w-full border p-2 rounded bg-white text-black resize-none"
          />
        </div>
        <div className="w-1/2 p-4 overflow-y-auto">
          <h2 className="text-xl font-semibold mb-2">🧠 AION Says</h2>
          <div className="whitespace-pre-wrap text-gray-800">
            {loading ? <p>⏳ Thinking...</p> : <p>{response || "Awaiting input..."}</p>}
          </div>
        </div>
      </div>

      {/* Command Input */}
      <div className="border-t p-4 flex items-center space-x-2 bg-gray-100">
        <input
          type="text"
          placeholder="Type a command..."
          value={terminalInput}
          onChange={(e) => setTerminalInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendPrompt()}
          className="flex-1 border px-3 py-2 rounded text-black"
        />
        <button
          onClick={sendPrompt}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          Send
        </button>
      </div>

      {/* 🧬 DNA Mutation Log Viewer */}
      <div className="p-4 bg-gray-50 border-t">
        <DnaLogViewer />
      </div>
    </div>
  );
}