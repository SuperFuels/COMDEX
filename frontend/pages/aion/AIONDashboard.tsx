"use client";

import React, { useEffect, useRef, useState } from "react";
import useAuthRedirect from "@/hooks/useAuthRedirect";

export default function AIONDashboard() {
  useAuthRedirect("admin");

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
  const [status, setStatus] = useState<any>(null);
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const outputRef = useRef<HTMLDivElement>(null);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/aion/status`);
      const data = await res.json();
      setStatus(data);
    } catch (err) {
      console.error("Failed to fetch status", err);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  useEffect(() => {
    outputRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [output]);

  const sendPrompt = async () => {
    if (!input.trim()) return;
    setLoading(true);
    setOutput("⏳ Thinking...");
    try {
      const res = await fetch(`${API_BASE}/aion/prompt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: input }),
      });
      const data = await res.json();
      setOutput(data.response || "No response.");
    } catch (err) {
      console.error(err);
      setOutput("❌ Error talking to AION.");
    } finally {
      setLoading(false);
      setInput("");
    }
  };

  const presetPrompts = [
    "Summarize unlocked skills",
    "Show goal progress",
    "Reflect on recent dreams",
    "List bootloader queue",
    "What is my current personality profile?",
  ];

  return (
    <div className="flex flex-col h-screen bg-white text-black">
      {/* Header */}
      <div className="p-4 border-b bg-gray-50">
        <h1 className="text-3xl font-bold">🧠 AION Dashboard</h1>
        <p className="text-sm text-gray-600">Phase: {status?.phase || "Loading..."}</p>
        <div className="mt-2 text-sm">
          <strong>Unlocked Modules:</strong>{" "}
          <span className="text-green-600">{status?.unlocked?.join(", ") || "..."}</span>
          <br />
          <strong>Locked Modules:</strong>{" "}
          <span className="text-red-600">{status?.locked?.join(", ") || "..."}</span>
        </div>
      </div>

      {/* Main content split */}
      <div className="flex flex-1 overflow-hidden divide-x">
        {/* Left: Controls */}
        <div className="w-1/3 p-4 space-y-4 overflow-y-auto">
          <h2 className="text-xl font-semibold mb-2">🛠️ Controls</h2>
          <button className="block w-full p-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={() => fetch('/api/aion/dream')}>Trigger Dream</button>
          <button className="block w-full p-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={() => fetch('/api/aion/boot-skill')}>Boot Next Skill</button>
          <button className="block w-full p-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={() => fetch('/api/aion/skill-reflect')}>Reflect Skills</button>
          <button className="block w-full p-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={() => fetch('/api/aion/run-dream')}>Run Scheduled Dream</button>
        </div>

        {/* Right: Terminal & Output */}
        <div className="flex-1 flex flex-col">
          <div className="flex-1 p-4 overflow-y-auto">
            <h2 className="text-xl font-semibold mb-2">🧠 AION Responds</h2>
            <div className="whitespace-pre-wrap text-gray-800">
              {loading ? "⏳ Thinking..." : output}
              <div ref={outputRef} />
            </div>

            {status?.goals?.length > 0 && (
              <div className="mt-6">
                <h3 className="font-semibold text-lg mb-1">🎯 Goals</h3>
                <ul className="list-disc list-inside text-sm text-gray-700">
                  {status.goals.map((g: any, idx: number) => (
                    <li key={idx}>{g.name} — {g.status}</li>
                  ))}
                </ul>
              </div>
            )}

            {status?.bootSkills?.length > 0 && (
              <div className="mt-6">
                <h3 className="font-semibold text-lg mb-1">🚀 Bootloader Skills</h3>
                <ul className="list-disc list-inside text-sm text-gray-700">
                  {status.bootSkills.map((b: any, idx: number) => (
                    <li key={idx}>{b.name} — {b.status}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Terminal input fixed at bottom */}
          <footer className="w-full bg-black text-white border-t border-gray-800 p-4">
            <h2 className="text-lg font-semibold mb-2">💬 Terminal</h2>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              rows={4}
              placeholder="Ask AION anything..."
              className="w-full border p-2 rounded mb-2 text-black resize-none"
            />
            <div className="flex items-center space-x-2">
              <button
                onClick={sendPrompt}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                Send
              </button>
              <button onClick={fetchStatus} className="text-sm underline text-gray-300">
                Refresh Status
              </button>
              {presetPrompts.map((p) => (
                <button
                  key={p}
                  onClick={() => setInput(p)}
                  className="px-3 py-1 text-xs bg-gray-700 rounded hover:bg-gray-600"
                >
                  {p}
                </button>
              ))}
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}