// components/AIONTerminal.tsx

import React, { useState } from "react";

export default function AIONTerminal() {
  const [input, setInput] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [outputs, setOutputs] = useState<string[]>([]);

  const sendPrompt = async () => {
    if (!input.trim()) return;
    setLoading(true);
    try {
      const res = await fetch("/api/aion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: input }),
      });
      const data = await res.json();
      const reply = data?.response || "No response from AION.";
      setOutputs((prev) => [...prev, `🧠 AION: ${reply}`]);
      setResponse(reply);
    } catch (err) {
      setOutputs((prev) => [...prev, `❌ Error: ${err}`]);
    } finally {
      setLoading(false);
      setInput("");
    }
  };

  return (
    <div className="flex flex-col h-full relative">
      {/* Output */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-2">
        {outputs.map((out, idx) => (
          <div key={idx} className="bg-white shadow border rounded p-4 whitespace-pre-wrap text-sm">
            {out}
          </div>
        ))}
      </div>

      {/* Footer Input */}
      <div className="sticky bottom-0 left-0 bg-white border-t border-gray-300 p-3">
        <div className="flex items-center space-x-2">
          <input
            className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm"
            type="text"
            placeholder="Ask AION anything..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendPrompt()}
          />
          <button
            onClick={sendPrompt}
            disabled={loading}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
          >
            {loading ? "..." : "Ask"}
          </button>
        </div>
      </div>
    </div>
  );
}