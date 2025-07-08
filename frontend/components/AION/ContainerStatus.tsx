import React, { useEffect, useState } from "react";

type Container = {
  id: string;
  in_memory: boolean;
  is_current?: boolean;
  title?: string;
  description?: string;
  tags?: string[];
  nav?: Record<string, string>; // nav structure: { north: "id2", south: "id3" }
};

const ContainerStatus = () => {
  const [containers, setContainers] = useState<Container[]>([]);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchContainers = async () => {
    try {
      const res = await fetch("/api/aion/containers");
      const data = await res.json();
      if (Array.isArray(data.containers)) {
        setContainers(data.containers);
      }
    } catch (err) {
      console.error("Failed to fetch containers:", err);
    }
  };

  useEffect(() => {
    let socket: WebSocket | null = null;
    let refreshInterval: NodeJS.Timeout;

    const initWebSocket = () => {
      socket = new WebSocket(`ws://${window.location.host}/ws/containers`);

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (Array.isArray(data.containers)) {
            setContainers(data.containers);
          }
        } catch (err) {
          console.error("Invalid WebSocket message:", err);
        }
      };

      socket.onerror = () => {
        console.warn("WebSocket error — falling back to polling.");
        if (autoRefresh) fetchContainers();
        refreshInterval = setInterval(() => autoRefresh && fetchContainers(), 10000);
      };

      socket.onclose = () => {
        console.warn("WebSocket closed — polling will continue if enabled.");
      };
    };

    initWebSocket();

    return () => {
      socket?.close();
      if (refreshInterval) clearInterval(refreshInterval);
    };
  }, [autoRefresh]);

  const teleportTo = (id: string) => {
    fetch("/api/aion/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: `teleport ${id}` }),
    });
  };

  return (
    <div className="p-4 bg-white rounded-lg shadow w-full max-w-md">
      <div className="flex justify-between items-center mb-2">
        <h2 className="text-lg font-bold">📦 Containers</h2>
        <button
          onClick={() => setAutoRefresh((prev) => !prev)}
          className="text-xs text-blue-600 underline"
        >
          {autoRefresh ? "🔁 Auto" : "⏸️ Manual"}
        </button>
      </div>

      {containers.length === 0 ? (
        <p className="text-sm text-gray-500">No containers loaded.</p>
      ) : (
        <ul className="space-y-3">
          {containers.map((c) => (
            <li
              key={c.id}
              onClick={() => teleportTo(c.id)}
              className={`py-2 px-3 rounded cursor-pointer transition border ${
                c.is_current
                  ? "bg-blue-200 font-semibold border-blue-400"
                  : c.in_memory
                  ? "bg-green-100 border-green-300"
                  : "bg-gray-100 border-gray-300"
              }`}
              title={c.description || ""}
            >
              <div className="flex justify-between items-center">
                <span>
                  {c.in_memory ? "🧠" : "📁"} {c.title || c.id}
                </span>
                {Array.isArray(c.tags) && c.tags.length > 0 && (
                  <span className="text-xs text-gray-500">
                    [{c.tags.join(", ")}]
                  </span>
                )}
              </div>
              {c.description && (
                <div className="text-xs text-gray-600 mt-1">{c.description}</div>
              )}
              {c.nav && (
                <div className="text-xs text-gray-500 mt-1">
                  <p className="font-medium">🗺️ Nav Map:</p>
                  <div className="ml-3 grid grid-cols-2 gap-1 text-xs">
                    {Object.entries(c.nav).map(([dir, dest]) => (
                      <div key={dir}>
                        <span className="text-gray-700">{dir}:</span>{" "}
                        <span className="text-blue-700">{dest}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default ContainerStatus;