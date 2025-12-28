// /workspaces/COMDEX/frontend/symatics_dashboard/tadd.jsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

function getHttpBase() {
  // Prefer explicit env override, else same-origin (works for Codespaces + prod)
  const envBase =
    (import.meta?.env && import.meta.env.VITE_API_BASE) ||
    (import.meta?.env && import.meta.env.VITE_FASTAPI_URL) ||
    "";

  if (envBase) return envBase;

  if (typeof window !== "undefined" && window.location?.origin) return window.location.origin;

  return "http://localhost:8080";
}

function toWsBase(httpBase) {
  return httpBase.replace(/^http/i, "ws");
}

export default function TADD() {
  const [aqci, setAqci] = useState({});
  const [rqfs, setRqfs] = useState({});
  const [log, setLog] = useState([]);

  const httpBase = useMemo(() => getHttpBase(), []);
  const wsBase = useMemo(() => toWsBase(httpBase), [httpBase]);

  const aqciUrl = useMemo(() => `${wsBase}/api/ws/control`, [wsBase]);
  const rqfsUrl = useMemo(() => `${wsBase}/api/ws/rqfs_feedback`, [wsBase]);

  const aqciRef = useRef(null);
  const rqfsRef = useRef(null);

  useEffect(() => {
    let stopped = false;
    let aqciRetry = 0;
    let rqfsRetry = 0;

    const connectAqci = () => {
      if (stopped) return;

      const ws = new WebSocket(aqciUrl);
      aqciRef.current = ws;

      ws.onmessage = (e) => {
        let msg;
        try {
          msg = JSON.parse(e.data);
        } catch {
          return;
        }

        if (msg?.type === "proxy_error") {
          // optional: surface proxy errors in the log stream
          setLog((l) => [
            ...l.slice(-40),
            { t: new Date().toISOString(), delta: 0, nu: 0, err: msg.error || "proxy_error" },
          ]);
          return;
        }

        if (msg?.type === "control_update" || msg?.type === "hello") {
          setAqci(msg.bias || msg.state || {});
          setLog((l) => [
            ...l.slice(-80),
            {
              t: new Date().toISOString(),
              delta: msg.delta ?? 0,
              nu: msg.bias?.nu_bias ?? 0,
            },
          ]);
        }
      };

      ws.onclose = () => {
        if (stopped) return;
        const delay = Math.min(8000, 500 + aqciRetry * 400);
        aqciRetry += 1;
        setTimeout(connectAqci, delay);
      };

      ws.onerror = () => {
        try {
          ws.close();
        } catch {}
      };
    };

    const connectRqfs = () => {
      if (stopped) return;

      const ws = new WebSocket(rqfsUrl);
      rqfsRef.current = ws;

      ws.onmessage = (e) => {
        let msg;
        try {
          msg = JSON.parse(e.data);
        } catch {
          return;
        }

        if (msg?.type === "proxy_error") return;

        if (msg?.type === "feedback_update" || msg?.type === "hello") {
          setRqfs(msg.state || {});
        }
      };

      ws.onclose = () => {
        if (stopped) return;
        const delay = Math.min(8000, 500 + rqfsRetry * 400);
        rqfsRetry += 1;
        setTimeout(connectRqfs, delay);
      };

      ws.onerror = () => {
        try {
          ws.close();
        } catch {}
      };
    };

    connectAqci();
    connectRqfs();

    return () => {
      stopped = true;
      try {
        aqciRef.current?.close();
      } catch {}
      try {
        rqfsRef.current?.close();
      } catch {}
    };
  }, [aqciUrl, rqfsUrl]);

  return (
    <div className="p-6 min-h-screen bg-gradient-to-b from-gray-950 to-gray-900 text-gray-100 font-mono">
      <h1 className="text-3xl mb-2 font-bold text-cyan-400">🧬 Tessaris Adaptive Diagnostics Dashboard</h1>
      <div className="text-xs text-gray-400 mb-4">
        WS: <span className="text-gray-300">{aqciUrl}</span> ·{" "}
        <span className="text-gray-300">{rqfsUrl}</span>
      </div>

      <div className="grid grid-cols-2 gap-6 mb-8">
        <div className="bg-gray-800 p-4 rounded-2xl shadow">
          <h2 className="text-xl mb-2 text-blue-300">AQCI Bias</h2>
          <pre className="text-sm whitespace-pre-wrap break-words">{JSON.stringify(aqci, null, 2)}</pre>
        </div>

        <div className="bg-gray-800 p-4 rounded-2xl shadow">
          <h2 className="text-xl mb-2 text-green-300">RQFS Feedback</h2>
          <pre className="text-sm whitespace-pre-wrap break-words">{JSON.stringify(rqfs, null, 2)}</pre>
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