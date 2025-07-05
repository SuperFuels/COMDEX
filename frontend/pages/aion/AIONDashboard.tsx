"use client";

import React, { useEffect, useRef, useState } from "react";
import useAuthRedirect from "@/hooks/useAuthRedirect";
import AIONTerminal from "@/components/AIONTerminal";

export default function AIONDashboard() {
  useAuthRedirect("admin");

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
  const [status, setStatus] = useState<any>(null);

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

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Endpoint Actions */}
        <div className="w-1/4 p-4 border-r overflow-y-auto bg-gray-50">
          <h2 className="text-lg font-semibold mb-4">📡 Actions</h2>

          <div className="space-y-4">
            <div className="bg-white p-3 rounded shadow border">
              <button
                onClick={fetchStatus}
                className="w-full text-center py-2 bg-blue-100 rounded hover:bg-blue-200"
              >
                🔄 Refresh Status
              </button>
            </div>
            <div className="bg-white p-3 rounded shadow border">
              <p className="font-medium mb-2">Presets</p>
              {["Summarize unlocked skills", "Show goal progress", "Reflect on recent dreams", "List bootloader queue", "What is my current personality profile?"].map(
                (text) => (
                  <button
                    key={text}
                    onClick={() => navigator.clipboard.writeText(text)}
                    className="block w-full text-left text-sm px-3 py-1 mb-1 bg-gray-100 rounded hover:bg-gray-200"
                  >
                    {text}
                  </button>
                )
              )}
            </div>
          </div>
        </div>

        {/* Center: AION Terminal */}
        <div className="w-3/4 flex flex-col relative">
          <div className="flex-1 overflow-y-auto p-6">
            <AIONTerminal />
          </div>
          {/* Fixed terminal input */}
          <div className="border-t p-4 bg-white sticky bottom-0 z-10">
            <AIONTerminal />
          </div>
        </div>
      </div>
    </div>
  );
}