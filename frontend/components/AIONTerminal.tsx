// components/AIONTerminal.tsx

import React, { useState } from "react";

export default function AIONTerminal() {
  const [responseLog, setResponseLog] = useState<string[]>([]);
  const [input, setInput] = useState<string>("");
  const [isAsking, setIsAsking] = useState<boolean>(false);

  const handleAsk = async () => {
    if (!input.trim()) return;
    setIsAsking(true);
    try {
      const res = await fetch("/api/aion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: input })
      });
      const data = await res.json();
      setResponseLog(prev => [...prev, `🧠 ${input}`, `🪄 ${data.response || "No reply."}`]);
      setInput("");
    } catch (err) {
      setResponseLog(prev => [...prev, `❌ Error: ${err}`]);
    }
    setIsAsking(false);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Terminal Content */}
      <div className="flex-1 overflow-y-auto text-sm text-gray-700 bg-white border rounded p-3 space-y-2">
        {responseLog.length === 0 ? (
          <p className="text-gray-400">No response yet. Ask AION something...</p>
        ) : (
          responseLog.map((msg, idx) => (
            <pre key={idx} className="whitespace-pre-wrap">{msg}</pre>
          ))
        )}
      </div>
    </div>
  );
}