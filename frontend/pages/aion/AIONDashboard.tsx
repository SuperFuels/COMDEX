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

      {/* Main content with adjustable split */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Side Terminal Section */}
        <div className="w-1/2 flex flex-col border-r p-4 space-y-4 overflow-y-auto">
          <div>
            <h2 className="text-lg font-semibold mb-2">💬 AION:</h2>
            <p className="text-green-700 font-medium">✅ Dream Result:</p>
            <p className="text-sm text-gray-800">Dream complete.</p>
          </div>
          <div>
            <h3 className="font-semibold">🎯 Current Goal</h3>
            <p className="text-sm">Explore the world and collect coins</p>
          </div>
          <div>
            <h3 className="font-semibold">🧬 Identity</h3>
            <p className="text-sm text-gray-500">No identity data.</p>
          </div>
          <div>
            <h3 className="font-semibold">🧠 Awareness</h3>
            <p className="text-sm text-gray-500">No awareness data</p>
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            <button className="bg-purple-600 text-white px-3 py-1 rounded">🟣 Boot Skill</button>
            <button className="bg-yellow-500 text-white px-3 py-1 rounded">💠 Reflect Skill</button>
            <button className="bg-green-600 text-white px-3 py-1 rounded">🌙 Run Dream</button>
            <button className="bg-indigo-600 text-white px-3 py-1 rounded">🎮 Game Dream</button>
          </div>
        </div>

        {/* Right Side Output Terminal */}
        <div className="w-1/2 flex flex-col justify-between">
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

          {/* Fixed Input Bar at Bottom */}
          <div className="p-4 border-t bg-white">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask AION anything..."
              rows={2}
              className="w-full border p-2 rounded mb-2 resize-none bg-white"
            />
            <div className="flex items-center justify-between">
              <button
                onClick={sendPrompt}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                Send
              </button>
              <button onClick={fetchStatus} className="text-sm underline text-gray-600">
                Refresh Status
              </button>
            </div>
            <div className="flex flex-wrap gap-2 mt-3">
              {presetPrompts.map((p) => (
                <button
                  key={p}
                  onClick={() => setInput(p)}
                  className="px-3 py-1 text-sm bg-gray-200 rounded hover:bg-gray-300"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}