import React, { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

export default function TADD() {
  const [aqci, setAqci] = useState({});
  const [rqfs, setRqfs] = useState({});
  const [log, setLog] = useState([]);

  useEffect(() => {
    // Connect to AQCI bias telemetry
    const aqciSocket = new WebSocket("ws://localhost:8004/ws/control");
    aqciSocket.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "control_update" || msg.type === "hello") {
        setAqci(msg.bias || msg.state || {});
        setLog((l) => [...l.slice(-40), { t: new Date().toISOString(), delta: msg.delta ?? 0, nu: msg.bias?.nu_bias ?? 0 }]);
      }
    };

    // Connect to RQFS feedback telemetry
    const rqfsSocket = new WebSocket("ws://localhost:8006/ws/rqfs_feedback");
    rqfsSocket.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "feedback_update" || msg.type === "hello") {
        setRqfs(msg.state || {});
      }
    };

    return () => {
      aqciSocket.close();
      rqfsSocket.close();
    };
  }, []);

  return (
    <div className="p-6 min-h-screen bg-gradient-to-b from-gray-950 to-gray-900 text-gray-100 font-mono">
      <h1 className="text-3xl mb-4 font-bold text-cyan-400">🧬 Tessaris Adaptive Diagnostics Dashboard</h1>

      <div className="grid grid-cols-2 gap-6 mb-8">
        <div className="bg-gray-800 p-4 rounded-2xl shadow">
          <h2 className="text-xl mb-2 text-blue-300">AQCI Bias</h2>
          <pre className="text-sm">{JSON.stringify(aqci, null, 2)}</pre>
        </div>

        <div className="bg-gray-800 p-4 rounded-2xl shadow">
          <h2 className="text-xl mb-2 text-green-300">RQFS Feedback</h2>
          <pre className="text-sm">{JSON.stringify(rqfs, null, 2)}</pre>
        </div>
      </div>

      <div className="bg-gray-800 p-4 rounded-2xl shadow">
        <h2 className="text-lg mb-2 text-yellow-400">ΔC / ν-bias Timeline</h2>
        <LineChart width={700} height={250} data={log}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="t" hide />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="delta" stroke="#facc15" name="ΔC" dot={false} />
          <Line type="monotone" dataKey="nu" stroke="#06b6d4" name="ν-bias" dot={false} />
        </LineChart>
      </div>
    </div>
  );
}