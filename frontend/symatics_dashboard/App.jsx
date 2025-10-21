import React, { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";

export default function App() {
  const [packets, setPackets] = useState([]);
  const [lastGlyph, setLastGlyph] = useState("—");
  const [connected, setConnected] = useState(false);
  const canvasRef = useRef(null);

  // WebSocket connection
  useEffect(() => {
    const ws = new WebSocket("wss://glowing-space-train-r467j79vv5xg2wj4p-8001.app.github.dev/ws/symatics");
    ws.onopen = () => setConnected(true);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setPackets((prev) => [...prev.slice(-50), data]);
      setLastGlyph(data.glyph || "•");
      drawField(data);
    };
    ws.onclose = () => setConnected(false);
    return () => ws.close();
  }, []);

  // Simple harmonic field renderer
  const drawField = (data) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const { width, height } = canvas;
    ctx.fillStyle = "rgba(0,0,0,0.08)";
    ctx.fillRect(0, 0, width, height);

    const x = width / 2 + Math.sin(data.phi) * data.amp * 2;
    const y = height / 2 + Math.cos(data.nu) * data.amp * 2;
    ctx.fillStyle = "#00ffaa";
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, 2 * Math.PI);
    ctx.fill();
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-4">
      <h1 className="text-2xl mb-4 font-bold text-cyan-300">
        Tessaris Symatics Live Dashboard
      </h1>

      <div className="mb-3">
        {connected ? (
          <span className="text-green-400">● Connected</span>
        ) : (
          <span className="text-red-500">● Disconnected</span>
        )}
      </div>

      <motion.div
        className="text-6xl font-mono mb-4"
        animate={{ scale: [1, 1.2, 1] }}
        transition={{ duration: 1.5, repeat: Infinity }}
      >
        {lastGlyph}
      </motion.div>

      <canvas
        ref={canvasRef}
        width={600}
        height={400}
        className="border border-cyan-700 rounded-lg shadow-lg"
      ></canvas>

      <div className="mt-6 text-sm text-gray-400 w-full max-w-xl overflow-y-auto h-32 bg-zinc-900 rounded-lg p-2">
        {packets.map((p, i) => (
          <div key={i} className="flex justify-between text-xs">
            <span>{p.timestamp?.slice(11, 19)}</span>
            <span>{p.glyph}</span>
            <span>ν={p.nu?.toFixed(3)}</span>
            <span>ϕ={p.phi?.toFixed(2)}</span>
            <span>A={p.amp?.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}